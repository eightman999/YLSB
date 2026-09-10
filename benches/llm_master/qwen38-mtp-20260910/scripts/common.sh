#!/usr/bin/env bash
set -u
set -o pipefail

ROOT=/home/eightman/llm_master/benches/qwen38-mtp-20260910
BIN=/home/eightman/dev/tools/llama.cpp/build/bin/llama-server
MODEL=/home/eightman/gguf-nvme/qwen3.8-27b-q4_K_M/qwen3.8-27b-q4_K_M.gguf
PORT=18080
HOST=127.0.0.1
ALIAS=qwen3.8-27b-q4_K_M
NGL=999
PID_FILE="$ROOT/llama-server.pid"
LLAMA_COMMIT=5ea1b124e7dfcdb80d7291be188efc7d0b485d66

kill_server() {
  if [[ -f "$PID_FILE" ]]; then
    local pid; pid=$(cat "$PID_FILE" || true)
    if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
      echo "[KILL] pid $pid"
      kill "$pid" 2>/dev/null || true
      sleep 2
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
  fi
  local p
  p=$(ss -tlnp 2>/dev/null | grep ":${PORT}" | sed -n 's/.*pid=\([0-9]*\).*/\1/p' | head -1 || true)
  if [[ -n "${p:-}" ]]; then
    echo "[KILL] port $PORT pid $p"
    kill "$p" 2>/dev/null || true
    sleep 1
    kill -9 "$p" 2>/dev/null || true
  fi
  pgrep -u eightman -f "llama-server.*${PORT}" | xargs -r kill 2>/dev/null || true
  sleep 1
}

wait_health() {
  local deadline=$((SECONDS + 420))
  while (( SECONDS < deadline )); do
    if curl -fsS --max-time 2 "http://${HOST}:${PORT}/health" >/dev/null 2>&1; then
      return 0
    fi
    if [[ -f "$PID_FILE" ]]; then
      local pid; pid=$(cat "$PID_FILE")
      if ! kill -0 "$pid" 2>/dev/null; then
        echo "[HEALTH] server pid $pid died"
        return 1
      fi
    fi
    sleep 2
  done
  return 1
}

# start_server SPLIT MTP TAG LOG_DIR CTX PARALLEL [TENSOR_SPLIT] [NMAX] [PMIN]
# MTP=ON|OFF ; optional NMAX default 2 ; PMIN empty=omit
start_server() {
  local split="$1"
  local mtp="$2"
  local tag="$3"
  local log_dir="$4"
  local ctx="$5"
  local parallel="$6"
  local tsplit="${7:-1,1}"
  local nmax="${8:-2}"
  local pmin="${9:-}"
  local logfile="$log_dir/server_${tag}.log"

  mkdir -p "$log_dir"
  kill_server
  sleep 1
  nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu --format=csv,noheader | tee -a "$logfile" || true

  local -a args=(
    -m "$MODEL"
    --n-gpu-layers "$NGL"
    --split-mode "$split"
    --parallel "$parallel"
    --ctx-size "$ctx"
    --host "$HOST"
    --port "$PORT"
    --alias "$ALIAS"
    -fa on
    --cache-type-k q4_0
    --cache-type-v q4_0
    --metrics
  )
  if [[ "$split" == "tensor" ]]; then
    args+=(--tensor-split "$tsplit")
  fi
  if [[ "$mtp" == "ON" ]]; then
    args+=(--spec-type draft-mtp --spec-draft-n-max "$nmax")
    if [[ -n "$pmin" ]]; then
      args+=(--spec-draft-p-min "$pmin")
    fi
  fi

  echo "[START] $(date -Is) $tag ctx=$ctx parallel=$parallel tsplit=$tsplit nmax=$nmax pmin=${pmin:-none} -> ${args[*]}" | tee -a "$logfile"
  local t0=$SECONDS
  stdbuf -oL -eL "$BIN" "${args[@]}" > >(tee -a "$logfile") 2>&1 &
  local spid=$!
  echo "$spid" > "$PID_FILE"
  echo "[START] pid=$spid log=$logfile"

  if ! wait_health; then
    echo "[START] FAIL health for $tag load_s=$((SECONDS-t0))"
    tail -80 "$logfile" || true
    if grep -qiE "out of memory|failed to allocate|CUDA error|ggml_backend.*alloc" "$logfile"; then
      echo "OOM" > "$log_dir/oom_${tag}.txt"
    fi
    return 1
  fi
  local load_s=$((SECONDS-t0))
  echo "[START] healthy $tag load_s=$load_s"
  echo "$load_s" > "$log_dir/load_s_${tag}.txt"
  nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader | tee "$log_dir/vram_after_load_${tag}.csv"
  {
    echo "=== FLAG GREP $tag ==="
    grep -iE "set_sampler|backend offload|CPU sampler|draft-mtp|speculative|MTP|load_mtp|spec_type|tensor.split|tensor_split|flash.?attn" "$logfile" || true
  } | tee "$log_dir/flags_${tag}.txt"
  return 0
}

gpu_snap() {
  local out="$1"
  nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu,utilization.memory,temperature.gpu,power.draw --format=csv > "$out"
}

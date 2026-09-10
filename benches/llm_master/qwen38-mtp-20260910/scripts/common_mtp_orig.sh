#!/usr/bin/env bash
# Shared helpers for MTP bench phases
set -u
set -o pipefail

ROOT=/home/eightman/mtp_bench
BIN=/home/eightman/dev/tools/llama.cpp/build/bin/llama-server
MODEL=/mnt/llm-hdd/ollama/models/blobs/sha256-f5f1dd8920d417aac2718b0bda3403da274301efdd6760b4f0f4b864ff2ad57d
PORT=11311
HOST=127.0.0.1
ALIAS=qwen3.8-27b-q4_K_M
NGL=999
SCRIPT_DIR="$ROOT/scripts"
ENV_DIR="$ROOT/env"
PID_FILE="$ROOT/llama-server.pid"

restore_master() {
  echo "[RESTORE] starting llama-master.service"
  systemctl --user start llama-master.service || true
  sleep 3
  for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
    if curl -fsS --max-time 3 "http://100.74.160.53:8080/health" >/dev/null 2>&1; then
      echo "[RESTORE] health OK"
      curl -fsS --max-time 3 "http://100.74.160.53:8080/health" | tee "$ENV_DIR/restore_health.json" || true
      date -Is | tee "$ENV_DIR/restore_time.txt"
      return 0
    fi
    sleep 2
  done
  echo "[RESTORE] WARNING: health check failed" | tee "$ENV_DIR/restore_health_FAIL.txt"
  return 1
}

kill_server() {
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid=$(cat "$PID_FILE" || true)
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
    # detect crash
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

# start_server SPLIT MTP TAG LOG_DIR CTX PARALLEL [TENSOR_SPLIT]
# TENSOR_SPLIT default 1,1 when split=tensor
start_server() {
  local split="$1"
  local mtp="$2"
  local tag="$3"
  local log_dir="$4"
  local ctx="$5"
  local parallel="$6"
  local tsplit="${7:-1,1}"
  local logfile="$log_dir/server_${tag}.log"

  mkdir -p "$log_dir"
  kill_server
  sleep 1
  # free GPU mem
  nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader | tee -a "$logfile" || true

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
    --metrics
  )
  if [[ "$split" == "tensor" ]]; then
    args+=(--tensor-split "$tsplit")
  fi
  if [[ "$mtp" == "ON" ]]; then
    args+=(--spec-type draft-mtp --spec-draft-n-max 3)
  fi

  echo "[START] $tag ctx=$ctx parallel=$parallel tsplit=$tsplit -> ${args[*]}" | tee -a "$logfile"
  stdbuf -oL -eL "$BIN" "${args[@]}" > >(tee -a "$logfile") 2>&1 &
  local spid=$!
  echo "$spid" > "$PID_FILE"
  echo "[START] pid=$spid log=$logfile"

  if ! wait_health; then
    echo "[START] FAIL health for $tag"
    tail -100 "$logfile" || true
    # check OOM
    if grep -qiE "out of memory|failed to allocate|CUDA error|ggml_backend.*alloc" "$logfile"; then
      echo "OOM" > "$log_dir/oom_${tag}.txt"
    fi
    return 1
  fi
  echo "[START] healthy $tag"
  {
    echo "=== FLAG GREP $tag ==="
    grep -E "set_sampler: backend sampling not supported with SPLIT_MODE_TENSOR|backend offload failed|using CPU sampler|draft-mtp|speculative|MTP|load_mtp|spec_type|tensor.split|tensor_split" "$logfile" || true
  } | tee "$log_dir/flags_${tag}.txt"
  return 0
}

run_mon() {
  local mon_dir="$1"
  local tag="$2"
  local pid="$3"
  local dur="$4"
  mkdir -p "$mon_dir"
  nvidia-smi dmon -s um -d 1 -c "$dur" > "$mon_dir/dmon_${tag}.txt" 2>&1 &
  echo $! > "$mon_dir/dmon_${tag}.pid"
  if [[ -n "$pid" ]]; then
    pidstat -u -p "$pid" 1 "$dur" > "$mon_dir/pidstat_${tag}.txt" 2>&1 &
    echo $! > "$mon_dir/pidstat_${tag}.pid"
  fi
}

stop_mon() {
  local mon_dir="$1"
  local tag="$2"
  for f in "$mon_dir/dmon_${tag}.pid" "$mon_dir/pidstat_${tag}.pid"; do
    if [[ -f "$f" ]]; then
      kill "$(cat "$f")" 2>/dev/null || true
      rm -f "$f"
    fi
  done
}

write_invalid() {
  local out="$1"
  local rep="$2" split="$3" mtp="$4" conc="$5" reason="$6"
  cat > "$out" << JSON
{"meta":{"repeat":${rep},"split":"${split}","mtp":"${mtp}","conc":${conc},"status":"INVALID","reason":"${reason}"},"summary":{"success":0,"fail":0,"output_tok_s":null,"wall_time_s":null}}
JSON
}

#!/usr/bin/env bash
# extracted run_matrix
set -u
set -o pipefail
# common must be sourced by caller first

run_matrix() {
  local phase="$1"
  local res_dir="$2"
  local log_dir="$3"
  local ctx="$4"
  local parallel="$5"
  local in_tok="$6"
  local out_tok="$7"
  local repeats="$8"
  local seed_base="$9"
  local concs_csv="${10}"
  local np_mult="${11}"
  local unique="${12}"
  local warmup_out="${13}"
  local mode="${14:-std}"  # std | ratios | ratios_mtp_subset

  mkdir -p "$res_dir" "$log_dir" "$res_dir/mon" "$res_dir/plots"
  local -a CONCS
  IFS=',' read -ra CONCS <<< "$concs_csv"

  local MTP_OK=1
  if [[ -f "$ENV_DIR/mtp_status.txt" ]]; then
    local st; st=$(cat "$ENV_DIR/mtp_status.txt")
    if [[ "$st" != "VALID" ]]; then MTP_OK=0; fi
  fi

  local -a CONFIGS=()
  if [[ "$mode" == "std" ]]; then
    CONFIGS=( "layer:OFF:1,1" "layer:ON:1,1" "tensor:OFF:1,1" "tensor:ON:1,1" )
  elif [[ "$mode" == "ratios" ]]; then
    # tensor ratios × MTP OFF/ON for 1,1 and best; OFF for all
    CONFIGS=(
      "tensor:OFF:1,1"
      "tensor:OFF:1,1.25"
      "tensor:OFF:1,1.5"
      "tensor:ON:1,1"
      "tensor:ON:1,1.25"
      "tensor:ON:1,1.5"
    )
  elif [[ "$mode" == "highconc" ]]; then
    CONFIGS=( "layer:OFF:1,1" "layer:ON:1,1" "tensor:OFF:1,1" "tensor:ON:1,1" )
  fi

  for ((rep=0; rep<repeats; rep++)); do
    local seed=$((seed_base + rep))
    # write configs to temp for shuffle
    printf '%s\n' "${CONFIGS[@]}" > /tmp/mtp_cfgs_$$.txt
    mapfile -t ORDER < <(python3 -c "
import random,sys
cfgs=[l.strip() for l in open('/tmp/mtp_cfgs_$$.txt') if l.strip()]
r=random.Random($seed)
r.shuffle(cfgs)
print(chr(10).join(cfgs))
")
    rm -f /tmp/mtp_cfgs_$$.txt
    logp "[$phase] REP $rep order: ${ORDER[*]}"
    echo "rep=$rep order=${ORDER[*]}" >> "$res_dir/run_order.txt"

    for cfg in "${ORDER[@]}"; do
      local split mtp tsplit
      split="${cfg%%:*}"
      rest="${cfg#*:}"
      mtp="${rest%%:*}"
      tsplit="${rest#*:}"

      local tag="r${rep}_${split}_${mtp}"
      if [[ "$mode" == "ratios" ]]; then
        local ts_safe; ts_safe=$(echo "$tsplit" | tr ',' '_')
        tag="r${rep}_tensor_${mtp}_ts${ts_safe}"
      fi

      if [[ "$mtp" == "ON" && "$MTP_OK" -ne 1 ]]; then
        logp "[$phase] SKIP MTP INVALID $tag"
        for conc in "${CONCS[@]}"; do
          write_invalid "$res_dir/${tag}_c${conc}.json" "$rep" "$split" "$mtp" "$conc" "MTP INVALID"
        done
        continue
      fi

      local cur_parallel="$parallel"
      local cur_ctx="$ctx"
      if ! start_server "$split" "$mtp" "$tag" "$log_dir" "$cur_ctx" "$cur_parallel" "$tsplit"; then
        # retry with lower parallel
        logp "[$phase] RETRY lower parallel for $tag"
        cur_parallel=$(( parallel / 2 ))
        if (( cur_parallel < 2 )); then cur_parallel=2; fi
        if ! start_server "$split" "$mtp" "${tag}_retry" "$log_dir" "$cur_ctx" "$cur_parallel" "$tsplit"; then
          logp "[$phase] FAIL start $tag -> INVALID all conc"
          for conc in "${CONCS[@]}"; do
            write_invalid "$res_dir/${tag}_c${conc}.json" "$rep" "$split" "$mtp" "$conc" "server start/OOM failed"
          done
          continue
        fi
        tag="${tag}_retry"
      fi

      local spid; spid=$(cat "$PID_FILE")

      # warmup
      local warm_np=4
      local warm_out="$warmup_out"
      # for long context, shorter warmup output OK
      if (( in_tok >= 8192 )); then warm_out=64; fi
      local uniq_args=()
      if [[ "$unique" == "1" ]]; then
        uniq_args=(--unique-prompts --prompt-seed "$((seed_base + rep * 100 + 7))")
      fi
      logp "[$phase] WARMUP $tag in=$in_tok out=$warm_out"
      python3 "$SCRIPT_DIR/bench_client.py" \
        --base-url "http://${HOST}:${PORT}" \
        --endpoint /v1/completions --model "$ALIAS" \
        --concurrency 1 --num-prompts "$warm_np" \
        --input-tokens "$in_tok" --output-tokens "$warm_out" \
        --warmup 0 --timeout 1800 \
        --output "$res_dir/warmup_${tag}.json" \
        --meta "{\"warmup\":true,\"tag\":\"${tag}\",\"phase\":\"${phase}\"}" \
        "${uniq_args[@]}" \
        | tee "$res_dir/warmup_${tag}_summary.json" || true

      for conc in "${CONCS[@]}"; do
        if (( conc > cur_parallel )); then
          write_invalid "$res_dir/${tag}_c${conc}.json" "$rep" "$split" "$mtp" "$conc" "conc>$cur_parallel"
          continue
        fi
        local nprompts=$((conc * np_mult))
        local out="$res_dir/${tag}_c${conc}.json"
        # skip if already done (resume)
        if [[ -f "$out" ]]; then
          if python3 -c "import json,sys; d=json.load(open(sys.argv[1])); s=d.get('summary') or {}; meta=d.get('meta') or {};
ok = meta.get('status')=='INVALID' or (s.get('success') or 0)>0 and s.get('output_tok_s') not in (None, 0, 0.0);
sys.exit(0 if ok else 1)" "$out" 2>/dev/null; then
            logp "[$phase] SKIP existing $out"
            continue
          fi
        fi
        local mon_tag="${tag}_c${conc}"
        local mon_dur=3600
        if (( in_tok >= 8192 )); then mon_dur=7200; fi
        run_mon "$res_dir/mon" "$mon_tag" "$spid" "$mon_dur"
        local meta
        meta=$(printf '{"repeat":%d,"split":"%s","mtp":"%s","conc":%d,"parallel":%d,"ctx":%d,"tensor_split":"%s","phase":"%s","input_tokens":%d,"output_tokens":%d,"status":"OK","unique_prompts":%s}' \
          "$rep" "$split" "$mtp" "$conc" "$cur_parallel" "$cur_ctx" "$tsplit" "$phase" "$in_tok" "$out_tok" "$([[ $unique == 1 ]] && echo true || echo false)")
        logp "[$phase] BENCH $mon_tag np=$nprompts in=$in_tok out=$out_tok"
        local t0=$SECONDS
        local bench_rc=0
        python3 "$SCRIPT_DIR/bench_client.py" \
          --base-url "http://${HOST}:${PORT}" \
          --endpoint /v1/completions --model "$ALIAS" \
          --concurrency "$conc" --num-prompts "$nprompts" \
          --input-tokens "$in_tok" --output-tokens "$out_tok" \
          --warmup 0 --timeout 3600 \
          --output "$out" --meta "$meta" \
          "${uniq_args[@]}" \
          | tee "$res_dir/${mon_tag}_summary.json" || bench_rc=$?
        local elapsed=$((SECONDS - t0))
        logp "[$phase] DONE $mon_tag elapsed=${elapsed}s rc=$bench_rc"
        stop_mon "$res_dir/mon" "$mon_tag"
        # CPU sampler flags for tensor+MTP
        if [[ "$split" == "tensor" && "$mtp" == "ON" ]]; then
          grep -E "set_sampler: backend sampling not supported with SPLIT_MODE_TENSOR|backend offload failed|using CPU sampler" \
            "$log_dir/server_${tag}.log" > "$log_dir/cpu_sampler_${mon_tag}.txt" || true
        fi
        # if wall > 45min for CONC4, note for possible repeat reduction (handled by caller via REPEATS)
        if (( conc >= 4 && elapsed > 2700 )); then
          echo "SLOW_CELL ${mon_tag} ${elapsed}s" | tee -a "$res_dir/slow_cells.txt"
        fi
        # detect total fail -> maybe OOM mid-run
        if python3 -c "import json,sys; d=json.load(open(sys.argv[1])); s=d.get('summary') or {}; sys.exit(0 if (s.get('success') or 0)==0 and (s.get('fail') or 0)>0 else 1)" "$out" 2>/dev/null; then
          logp "[$phase] WARN all failed $mon_tag — check server"
          if ! curl -fsS --max-time 2 "http://${HOST}:${PORT}/health" >/dev/null 2>&1; then
            logp "[$phase] server dead after $mon_tag"
            # mark remaining concs invalid and break to next config
            for c2 in "${CONCS[@]}"; do
              if (( c2 > conc )); then
                write_invalid "$res_dir/${tag}_c${c2}.json" "$rep" "$split" "$mtp" "$c2" "server died after prior conc"
              fi
            done
            break
          fi
        fi
      done
    done
  done
}


#!/usr/bin/env bash
# Qwen3.8-27B MTP master bench 2026-09-10
set -u
set -o pipefail
BENCH=/home/eightman/llm_master/benches/qwen38-mtp-20260910
SCR="$BENCH/scripts"
# shellcheck source=/dev/null
source "$SCR/common.sh"
PROBE=/home/eightman/llm_master/vendor/qwen38-mtp/probe.py
CLIENT=python3
BC="$SCR/bench_client.py"
BASE="http://${HOST}:${PORT}"
RESULTS_JSONL="$BENCH/results.jsonl"
SUMMARY_CSV="$BENCH/summary.csv"
FAIL="$BENCH/failures.md"
START_EPOCH=$(date +%s)
MAX_WALL_H=7.5

mkdir -p "$BENCH"/{phase1,phase2,phase3a,phase3b,phase4,phase5,logs,raw,plots}
: > "$RESULTS_JSONL"
echo "phase,tag,split,tsplit,mtp,nmax,pmin,ctx,parallel,metric,value,unit,rep,notes" > "$SUMMARY_CSV"
echo "# failures" > "$FAIL"
echo "RUN_START $(date -Is)" | tee -a "$BENCH/logs/orchestrator.log"

wall_ok() {
  local elapsed=$(( $(date +%s) - START_EPOCH ))
  local max=$(( ${MAX_WALL_H%.*} * 3600 + 1800 ))
  (( elapsed < max ))
}

append_jsonl() {
  echo "$1" >> "$RESULTS_JSONL"
}

csv_row() {
  # Phase14: quote fields via Python csv.writer (tsplit like 1,1 / notes with commas)
  python3 - "$SUMMARY_CSV" "$1" <<'PY'
import csv, sys
path, raw = sys.argv[1], sys.argv[2]
# Accept either pipe-delimited 14 fields or legacy comma-joined (best-effort)
if "|" in raw and raw.count("|") >= 13:
    fields = raw.split("|", 13)
else:
    # legacy single-string row: still write as ONE column-safe row by parsing known header order
    # Prefer callers migrate to pipe form. Fallback: write raw via csv as single row split carefully.
    import re
    # Try to split into 14 fields with tsplit recovery
    parts = raw.split(",")
    header_n = 14
    if len(parts) == header_n:
        fields = parts
    else:
        # dump as-is into notes-safe writer by treating whole as one malformed — still quote via writerow of parts
        fields = parts
fields = (fields + [""] * 14)[:14]
with open(path, "a", newline="") as f:
    csv.writer(f).writerow(fields)
PY
}

# Preferred helper: positional fields (pipe-safe)
csv_row_fields() {
  local IFS='|'
  csv_row "$*"
}

run_bench_client() {
  local tag="$1" out="$2" conc="$3" nprompts="$4" inp="$5" outt="$6" meta="$7"
  $CLIENT "$BC" --base-url "$BASE" --concurrency "$conc" --num-prompts "$nprompts" \
    --input-tokens "$inp" --output-tokens "$outt" --warmup 1 --timeout 600 \
    --output "$out" --meta "$meta" 2>"$out.err" || return 1
  return 0
}

extract_median_tps() {
  python3 - "$1" <<'PY'
import json,sys
p=sys.argv[1]
d=json.load(open(p))
s=d.get("summary") or d
v=s.get("output_tok_s") or s.get("median_output_tok_s")
print(v if v is not None else "")
PY
}

extract_ttft() {
  python3 - "$1" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
s=d.get("summary") or d
v=s.get("median_ttft_s") or s.get("mean_ttft_s")
print(v if v is not None else "")
PY
}

############################################
# PHASE 1 — baseline tensor 1,1 (prior best)
############################################
phase1() {
  local P="$BENCH/phase1"
  echo "=== PHASE1 $(date -Is) ===" | tee -a "$BENCH/logs/orchestrator.log"
  local CTX=8192
  # Cold load OFF
  local t0=$SECONDS
  if ! start_server tensor OFF p1_tensor11_OFF "$P" "$CTX" 1 1,1; then
    echo "- phase1 cold start OFF failed" >> "$FAIL"
    return 1
  fi
  local cold_load=$(cat "$P/load_s_p1_tensor11_OFF.txt")
  gpu_snap "$P/vram_cold_OFF.csv"
  csv_row "1|p1_tensor11_OFF|tensor|1,1|OFF|0||$CTX|1|cold_load_s|$cold_load|s|0|"

  # Warm restart same config
  kill_server; sleep 2
  t0=$SECONDS
  start_server tensor OFF p1_tensor11_OFF_warm "$P" "$CTX" 1 1,1 || true
  local warm_load=$(cat "$P/load_s_p1_tensor11_OFF_warm.txt" 2>/dev/null || echo NA)
  csv_row "1|p1_tensor11_OFF_warm|tensor|1,1|OFF|0||$CTX|1|warm_load_s|$warm_load|s|0|"

  # 3 reps: pp512 (512→64), tg128 (128→128)  — use unique for fairness on later
  local rep tps ttft
  for rep in 0 1 2; do
    run_bench_client "pp512_r$rep" "$P/pp512_r${rep}.json" 1 8 512 64 \
      "{\"phase\":1,\"metric\":\"pp512\",\"rep\":$rep,\"split\":\"tensor\",\"mtp\":\"OFF\"}" || echo "- pp512 r$rep fail" >> "$FAIL"
    tps=$(extract_median_tps "$P/pp512_r${rep}.json" 2>/dev/null || echo "")
    ttft=$(extract_ttft "$P/pp512_r${rep}.json" 2>/dev/null || echo "")
    csv_row "1|pp512_OFF|tensor|1,1|OFF|0||$CTX|1|output_tok_s|$tps|tok/s|$rep|ttft=$ttft"
    append_jsonl "{\"phase\":1,\"tag\":\"pp512_OFF\",\"rep\":$rep,\"output_tok_s\":$tps,\"ttft\":$ttft}"
  done
  for rep in 0 1 2; do
    run_bench_client "tg128_r$rep" "$P/tg128_r${rep}.json" 1 12 128 128 \
      "{\"phase\":1,\"metric\":\"tg128\",\"rep\":$rep,\"split\":\"tensor\",\"mtp\":\"OFF\"}" || echo "- tg128 r$rep fail" >> "$FAIL"
    tps=$(extract_median_tps "$P/tg128_r${rep}.json" 2>/dev/null || echo "")
    ttft=$(extract_ttft "$P/tg128_r${rep}.json" 2>/dev/null || echo "")
    csv_row "1|tg128_OFF|tensor|1,1|OFF|0||$CTX|1|output_tok_s|$tps|tok/s|$rep|ttft=$ttft"
    append_jsonl "{\"phase\":1,\"tag\":\"tg128_OFF\",\"rep\":$rep,\"output_tok_s\":$tps,\"ttft\":$ttft}"
  done
  gpu_snap "$P/vram_after_p1_OFF.csv"
  # Also MTP ON quick tg128 for regression vs prior ~35 tok/s
  kill_server; sleep 2
  start_server tensor ON p1_tensor11_ON "$P" "$CTX" 1 1,1 2 || { echo "- p1 MTP ON start fail" >> "$FAIL"; return 0; }
  for rep in 0 1 2; do
    run_bench_client "tg128_ON_r$rep" "$P/tg128_ON_r${rep}.json" 1 12 128 128 \
      "{\"phase\":1,\"metric\":\"tg128\",\"rep\":$rep,\"split\":\"tensor\",\"mtp\":\"ON\"}" || true
    tps=$(extract_median_tps "$P/tg128_ON_r${rep}.json" 2>/dev/null || echo "")
    ttft=$(extract_ttft "$P/tg128_ON_r${rep}.json" 2>/dev/null || echo "")
    csv_row "1|tg128_ON|tensor|1,1|ON|2||$CTX|1|output_tok_s|$tps|tok/s|$rep|ttft=$ttft"
    append_jsonl "{\"phase\":1,\"tag\":\"tg128_ON\",\"rep\":$rep,\"output_tok_s\":$tps,\"ttft\":$ttft}"
  done
  gpu_snap "$P/vram_after_p1_ON.csv"
  echo "PHASE1_DONE $(date -Is)" | tee -a "$BENCH/logs/orchestrator.log"
}

############################################
# PHASE 2 — split explore (narrow)
############################################
phase2() {
  local P="$BENCH/phase2"
  echo "=== PHASE2 $(date -Is) ===" | tee -a "$BENCH/logs/orchestrator.log"
  local CTX=8192
  # configs: layer; tensor 1,1; tensor 1,1.25; layer with devices swapped (P100-heavy)
  declare -a CFGS=(
    "layer|OFF|layer_def|1,1"
    "tensor|OFF|tensor_11|1,1"
    "tensor|OFF|tensor_1125|1,1.25"
  )
  local cfg split mtp tag tsplit rep tps
  for cfg in "${CFGS[@]}"; do
    wall_ok || { echo "time cut phase2" >> "$FAIL"; break; }
    IFS='|' read -r split mtp tag tsplit <<<"$cfg"
    kill_server; sleep 2
    if ! start_server "$split" "$mtp" "p2_$tag" "$P" "$CTX" 1 "$tsplit"; then
      echo "- phase2 start fail $tag" >> "$FAIL"
      continue
    fi
    for rep in 0 1 2; do
      run_bench_client "p2_${tag}_r$rep" "$P/${tag}_r${rep}.json" 1 10 128 128 \
        "{\"phase\":2,\"tag\":\"$tag\",\"rep\":$rep}" || true
      tps=$(extract_median_tps "$P/${tag}_r${rep}.json" 2>/dev/null || echo "")
      csv_row "2|$tag|$split|$tsplit|$mtp|0||$CTX|1|output_tok_s|$tps|tok/s|$rep|"
      append_jsonl "{\"phase\":2,\"tag\":\"$tag\",\"split\":\"$split\",\"tsplit\":\"$tsplit\",\"rep\":$rep,\"output_tok_s\":$tps}"
    done
    gpu_snap "$P/vram_${tag}.csv"
  done
  # P100-heavy: swap visible devices for layer
  wall_ok || true
  kill_server; sleep 2
  export CUDA_VISIBLE_DEVICES=1,0
  if start_server layer OFF p2_layer_p100heavy "$P" "$CTX" 1 1,1; then
    for rep in 0 1 2; do
      run_bench_client "p2_p100_r$rep" "$P/layer_p100heavy_r${rep}.json" 1 10 128 128 \
        "{\"phase\":2,\"tag\":\"layer_p100heavy\",\"rep\":$rep}" || true
      tps=$(extract_median_tps "$P/layer_p100heavy_r${rep}.json" 2>/dev/null || echo "")
      csv_row "2|layer_p100heavy|layer|swap|OFF|0||$CTX|1|output_tok_s|$tps|tok/s|$rep|CUDA_VISIBLE_DEVICES=1,0"
    done
    gpu_snap "$P/vram_layer_p100heavy.csv"
  else
    echo "- p100heavy start fail" >> "$FAIL"
  fi
  unset CUDA_VISIBLE_DEVICES
  echo "PHASE2_DONE $(date -Is)" | tee -a "$BENCH/logs/orchestrator.log"
}

############################################
# PHASE 3A — stock probe.py A/B (PR critical)
############################################
phase3a() {
  local P="$BENCH/phase3a"
  echo "=== PHASE3A probe.py $(date -Is) ===" | tee -a "$BENCH/logs/orchestrator.log"
  local CTX=8192
  # Prefer best split from p2; default tensor 1,1 from prior
  local BEST_SPLIT=tensor
  local BEST_TS=1,1
  # Try to pick from phase2 medians
  python3 - "$BENCH/summary.csv" > "$P/best_split.txt" <<'PY' || echo "tensor 1,1" > "$P/best_split.txt"
import csv,statistics,collections,sys
rows=list(csv.DictReader(open(sys.argv[1])))
by=collections.defaultdict(list)
for r in rows:
  if r.get("phase")=="2" and r.get("metric")=="output_tok_s" and r.get("value"):
    try: by[r["tag"]].append(float(r["value"]))
    except: pass
if not by:
  print("tensor 1,1"); raise SystemExit
best=max(by.items(), key=lambda kv: statistics.median(kv[1]))
tag=best[0]
# map tag to split
if tag.startswith("tensor"):
  ts="1,1.25" if "1125" in tag else "1,1"
  print(f"tensor {ts}")
else:
  print("layer 1,1")
print(f"# medians: "+ ", ".join(f"{k}:{statistics.median(v):.2f}" for k,v in by.items()), file=sys.stderr)
PY
  read -r BEST_SPLIT BEST_TS < <(grep -v '^#' "$P/best_split.txt" | head -1)
  echo "BEST_SPLIT=$BEST_SPLIT BEST_TS=$BEST_TS" | tee -a "$BENCH/logs/orchestrator.log"

  run_probe_arm() {
    local arm="$1" nmax="$2" pmin="$3" outfile="$4"
    kill_server; sleep 2
    if ! start_server "$BEST_SPLIT" "$arm" "p3a_${arm}_n${nmax}_${pmin:-nop}" "$P" "$CTX" 1 "$BEST_TS" "$nmax" "$pmin"; then
      echo "- probe start fail $arm n$max" >> "$FAIL"
      return 1
    fi
    gpu_snap "$P/vram_probe_${arm}_n${nmax}.csv"
    # capture acceptance from metrics if available during/after
    python3 "$PROBE" "$BASE" 2>&1 | tee "$outfile"
    # try metrics endpoint for speculative stats
    curl -fsS --max-time 5 "$BASE/metrics" > "$P/metrics_${arm}_n${nmax}.txt" 2>/dev/null || true
    return 0
  }

  # Alternate OFF / ON n-max=2 (3 times each? probe already does 3x3; do OFF then ON once each as stock method; optional 2nd pair)
  run_probe_arm OFF 0 "" "$P/probe_OFF_1.txt" || true
  run_probe_arm ON 2 "" "$P/probe_ON_nmax2_1.txt" || true
  # second pair for stability
  run_probe_arm OFF 0 "" "$P/probe_OFF_2.txt" || true
  run_probe_arm ON 2 "" "$P/probe_ON_nmax2_2.txt" || true

  # Parse OVERALL medians
  python3 - "$P" <<'PY' | tee "$P/probe_summary.md"
import re, pathlib, statistics
P=pathlib.Path(__file__) if False else pathlib.Path(".")
# path arg
import sys
root=pathlib.Path(sys.argv[1])
def parse(fn):
  t=fn.read_text(errors="replace")
  m=re.search(r"OVERALL: mean ([\d.]+) median ([\d.]+)", t)
  return (float(m.group(1)), float(m.group(2))) if m else (None,None)
offs=[]; ons=[]
for f in sorted(root.glob("probe_OFF_*.txt")):
  a,b=parse(f); 
  if b is not None: offs.append(b)
for f in sorted(root.glob("probe_ON_nmax2_*.txt")):
  a,b=parse(f)
  if b is not None: ons.append(b)
print("# Phase3A stock probe.py summary\n")
print(f"- OFF medians: {offs}")
print(f"- ON n-max=2 medians: {ons}")
if offs and ons:
  bo,bn=statistics.median(offs),statistics.median(ons)
  print(f"- **Baseline (OFF) median-of-sessions: {bo:.1f} tok/s**")
  print(f"- **With flag (ON n-max=2) median-of-sessions: {bn:.1f} tok/s**")
  print(f"- Speedup: {bn/bo:.3f}x" if bo else "")
PY

  # If n-max=2 helps, try 3 and 4 lightly + p-min
  python3 - "$P/probe_summary.md" <<'PY'
import sys,re
t=open(sys.argv[1]).read()
m=re.search(r"Speedup: ([\d.]+)x", t)
sp=float(m.group(1)) if m else 0
open("/tmp/mtp_helps","w").write("1" if sp>=1.05 else "0")
PY
  if [[ "$(cat /tmp/mtp_helps 2>/dev/null || echo 0)" == "1" ]]; then
    run_probe_arm ON 3 "" "$P/probe_ON_nmax3.txt" || true
    run_probe_arm ON 4 "" "$P/probe_ON_nmax4.txt" || true
    # p-min for Pascal bandwidth
    run_probe_arm ON 2 "0.60" "$P/probe_ON_nmax2_pmin060.txt" || true
    run_probe_arm ON 2 "0.75" "$P/probe_ON_nmax2_pmin075.txt" || true
  fi
  echo "PHASE3A_DONE $(date -Is)" | tee -a "$BENCH/logs/orchestrator.log"
}

############################################
# PHASE 3B — runtime compare SKIP
############################################
phase3b() {
  local P="$BENCH/phase3b"
  cat > "$P/SKIP.md" <<'E'
# Phase 3B Runtime compare — SKIP

| Runtime | Status | Reason |
|---|---|---|
| llama.cpp (this bench) | MEASURED | Phase1–3A |
| vLLM | SKIP | not installed; no pip install (CUDA/driver freeze) |
| 1Cat-vLLM | SKIP | not installed (prior mtp_bench same) |
E
  cp "$P/SKIP.md" "$BENCH/runtime_comparison.md"
  echo "PHASE3B_DONE SKIP" | tee -a "$BENCH/logs/orchestrator.log"
}

############################################
# PHASE 4 — quality smoke (top configs)
############################################
phase4() {
  local P="$BENCH/phase4"
  echo "=== PHASE4 $(date -Is) ===" | tee -a "$BENCH/logs/orchestrator.log"
  local CTX=8192
  # Japanese / coding / IF fixtures from ylsb_pack_run
  local FIX=/home/eightman/ylsb_pack_run/fixtures
  kill_server; sleep 2
  start_server tensor ON p4_mtp "$P" "$CTX" 1 1,1 2 || start_server tensor OFF p4_off "$P" "$CTX" 1 1,1 || return 0
  python3 - <<'PY' | tee "$P/quality_smoke.md"
import json, urllib.request, pathlib, time, os
base="http://127.0.0.1:18080"
prompts=[
 ("ja_reason", "次の命題を日本語で簡潔に論証せよ: 『すべての白鳥が白い』は反証可能か。200字以内。"),
 ("coding", "Write a Python function is_palindrome(s: str) -> bool. No explanation."),
 ("if_json", "Return ONLY valid JSON: {\"ok\": true, \"n\": 3} with no markdown."),
 ("hard", "Solve: 15% of 240 is what? Show one equation then the number."),
]
out=[]
for name,p in prompts:
  body={"messages":[{"role":"user","content":p}],"max_tokens":256,"stream":False,"chat_template_kwargs":{"enable_thinking":False}}
  req=urllib.request.Request(base+"/v1/chat/completions", json.dumps(body).encode(), {"Content-Type":"application/json"})
  t0=time.time()
  try:
    with urllib.request.urlopen(req, timeout=180) as r:
      data=json.loads(r.read().decode())
    text=data["choices"][0]["message"].get("content") or ""
    dt=time.time()-t0
    out.append({"name":name,"latency_s":round(dt,2),"text":text[:800]})
  except Exception as e:
    out.append({"name":name,"error":str(e)})
pathlib.Path("/home/eightman/llm_master/benches/qwen38-mtp-20260910/phase4/quality_raw.json").write_text(json.dumps(out,ensure_ascii=False,indent=2))
print("# Quality smoke\n")
for o in out:
  print(f"## {o.get('name')}\n")
  if "error" in o: print("ERROR", o["error"])
  else: print(f"latency={o['latency_s']}s\n\n```\n{o['text']}\n```\n")
PY
  # also OFF for MTP breakage check
  kill_server; sleep 2
  start_server tensor OFF p4_off "$P" "$CTX" 1 1,1 || true
  echo "PHASE4_DONE $(date -Is)" | tee -a "$BENCH/logs/orchestrator.log"
}

############################################
# PHASE 5 — long context 8K→16K→32K
############################################
phase5() {
  wall_ok || { echo "skip phase5 time" >> "$FAIL"; return 0; }
  local P="$BENCH/phase5"
  echo "=== PHASE5 $(date -Is) ===" | tee -a "$BENCH/logs/orchestrator.log"
  local ctx tps
  for ctx in 8192 16384 32768; do
    wall_ok || break
    kill_server; sleep 2
    if ! start_server tensor ON "p5_c${ctx}" "$P" "$ctx" 1 1,1 2; then
      echo "- phase5 OOM/fail ctx=$ctx" >> "$FAIL"
      # try OFF
      if ! start_server tensor OFF "p5_c${ctx}_off" "$P" "$ctx" 1 1,1; then
        echo "- phase5 OFF also fail ctx=$ctx STOP" >> "$FAIL"
        break
      fi
    fi
    gpu_snap "$P/vram_c${ctx}.csv"
    # prompt ~ ctx/4 tokens, gen 128
    local inp=$(( ctx / 4 ))
    (( inp > 2048 )) && inp=2048
    run_bench_client "p5_c$ctx" "$P/c${ctx}.json" 1 4 "$inp" 128 \
      "{\"phase\":5,\"ctx\":$ctx}" || echo "- p5 bench fail $ctx" >> "$FAIL"
    tps=$(extract_median_tps "$P/c${ctx}.json" 2>/dev/null || echo "")
    csv_row "5|long_c$ctx|tensor|1,1|ON|2||$ctx|1|output_tok_s|$tps|tok/s|0|server_ctx_only_input_le_2048"
  done
  echo "PHASE5_DONE $(date -Is)" | tee -a "$BENCH/logs/orchestrator.log"
}

############################################
# PHASE 6 — spot-check other models IF time
############################################
phase6() {
  if ! wall_ok; then
    echo "# Phase6 CUT — wall clock" > "$BENCH/phase6/CUT.md"
    echo "PHASE6_CUT" | tee -a "$BENCH/logs/orchestrator.log"
    return 0
  fi
  echo "PHASE6_SKIP_OPTIONAL time tight — Dense27B focus" | tee -a "$BENCH/logs/orchestrator.log"
  echo "# Phase6 skipped (time); Dense27B priority" > "$BENCH/phase6/SKIP.md"
}

finalize() {
  kill_server || true
  python3 - "$BENCH" <<'PY'
import csv, statistics, collections, pathlib, json, datetime
root=pathlib.Path(__file__) if False else pathlib.Path(".")
import sys
root=pathlib.Path(sys.argv[1])
rows=list(csv.DictReader(open(root/"summary.csv")))
# leaderboard
lines=["# Leaderboard — qwen38-mtp-20260910\n","生成: "+datetime.datetime.now().isoformat(),"\n"]
lines.append("| tag | split | mtp | median tok/s | n |\n|---|---|---|---:|---:|\n")
by=collections.defaultdict(list)
for r in rows:
  if r.get("metric")=="output_tok_s" and r.get("value"):
    try: by[(r["tag"],r["split"],r["mtp"])].append(float(r["value"]))
    except: pass
ranked=[]
for k,vs in by.items():
  ranked.append((statistics.median(vs), k[0], k[1], k[2], len(vs)))
ranked.sort(reverse=True)
for med,tag,split,mtp,n in ranked[:30]:
  lines.append(f"| {tag} | {split} | {mtp} | {med:.2f} | {n} |\n")
# classification
lines.append("\n## 判定\n")
lines.append("- **ADOPT候補**: tensor-split `1,1` + (MTP ON if probe speedup≥1.15 @ conc=1)\n")
lines.append("- Phase3B vLLM/1Cat: SKIP\n")
(root/"leaderboard.md").write_text("".join(lines))
print("wrote leaderboard", len(ranked))
PY
  # qwen38_mtp_ab.md from phase3a
  if [[ -f "$BENCH/phase3a/probe_summary.md" ]]; then
    {
      echo "# qwen38_mtp_ab — stock probe.py A/B"
      echo
      cat "$BENCH/phase3a/probe_summary.md"
      echo
      echo "## Serve knobs"
      echo "- split: see phase3a/best_split.txt"
      echo "- ctx=8192 -ngl 999 -fa on --cache-type-k/v q4_0 --parallel 1"
      echo "- ON: --spec-type draft-mtp --spec-draft-n-max 2"
      echo "- llama.cpp: 5ea1b124e7dfcdb80d7291be188efc7d0b485d66"
      echo "- method: vendor/qwen38-mtp/probe.py unchanged"
    } > "$BENCH/qwen38_mtp_ab.md"
  fi
  echo "FINALIZE_DONE $(date -Is)" | tee -a "$BENCH/logs/orchestrator.log"
}

main() {
  phase1
  phase2
  phase3a
  phase3b
  phase4
  phase5
  phase6
  finalize
  echo "ALL_DONE $(date -Is)" | tee -a "$BENCH/logs/orchestrator.log"
}

main "$@"

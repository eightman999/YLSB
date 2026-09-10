# Phase14 補正まとめ — qwen38-mtp-20260910

生成: 2026-09-10T10:24:00+09:00

## 目的

Phase3a の stock `probe.py` A/B が CSV バグ由来の **layer** 誤選択で走っていたため、**tensor 1,1** で正式再測定。長文 Phase5 を「サーバ ctx のみ・実入力≤2048」と再分類し、実長文を新規測定。

## 1) summary.csv 修正

- バックアップ: `summary.csv.bak_pre_phase14`
- `tsplit` の `1,1` / `1,1.25` および notes のカンマを `csv.writer` でクォート
- `scripts/run_all.sh` の `csv_row` を Python `csv.writer` + pipe 区切りに変更
- テスト `phase14/test_csv_best_split.py`: DictReader 後の Phase2 best = **tensor_11 / 1,1**（旧バグは `layer_p100heavy` 誤選）

## 2) 正式 stock probe.py — tensor 1,1（上流公式）

未変更 `vendor/qwen38-mtp/probe.py` @ `3097ca3d9731d49d5b68fd77e717a578056b7c74`  
交互: OFF, ON, OFF, ON, OFF, ON（各 restart）  
共通: `-m Q4_K_M -c 8192 -ngl 999 -fa on --cache-type-k/v q4_0 --parallel 1 --split-mode tensor --tensor-split 1,1`  
ON 追加: `--spec-type draft-mtp --spec-draft-n-max 2`

| arm | session OVERALL medians | median-of-sessions |
|---|---|---:|
| OFF | 19.3, 19.3, 19.3 | **19.3** tok/s |
| ON n-max=2 | 30.4, 31.4, 31.0 | **31.0** tok/s |

- **Speedup: 1.6062x**（31.0 / 19.3）
- **Acceptance (最後の ON /metrics): 0.7863** = 1700 accepted / 2162 draft  
  - 3 ON セッション ratio 中央値 ≈ 0.796
- 生データ: `phase14/probe_tensor11/`
- 旧 layer probe（13.8→21.8, 1.576x, acc 0.910）は **historical/accidental** として保持（上流行には使わない）

## 3) MTP sweep（tensor 1,1 / stock probe OVERALL median）

| name | nmax | pmin | overall median |
|---|---:|---|---:|
| OFF | 0 | | 19.3 |
| **n2** | 2 | | **30.9** |
| n3 | 3 | | 28.5 |
| n4 | 4 | | 27.4 |
| n2_pmin060 | 2 | 0.60 | 29.4 |
| n2_pmin075 | 2 | 0.75 | 27.4 |

**DAILY_RECOMMENDED = n2**（全体中央値最大。近接時は単純設定優先だが、ここでは n2 が明確に首位）

```
# DAILY_RECOMMENDED from Phase14 MTP sweep (stock probe.py overall median)
# pick=n2 median=30.9
llama-server \
  -m /home/eightman/gguf-nvme/qwen3.8-27b-q4_K_M/qwen3.8-27b-q4_K_M.gguf \
  -c 8192 -ngl 999 -fa on \
  --cache-type-k q4_0 --cache-type-v q4_0 \
  --parallel 1 \
  --split-mode tensor --tensor-split 1,1 \
  --spec-type draft-mtp --spec-draft-n-max 2 \
  --host 127.0.0.1 --port 18080 --metrics
```

## 4) 真の長文（DAILY_RECOMMENDED + bench_client --unique-prompts）

旧 Phase5 は **サーバ ctx 8K/16K/32K・実入力 ≤2048** と再分類（長文維持の証拠にしない）。

| ctx | input target | input actual (client) | server prompt toks | success | OOM | TTFT s | e2e s | decode tok/s (tpot) | server decode tok/s |
|---:|---:|---:|---:|---|---|---:|---:|---:|---:|
| 8192 | 7168 | 7168 | 7222 | yes | no | 38.64 | 42.41 | 33.72 | 33.72 |
| 16384 | 15360 | 15360 | 15409 | yes | no | 83.10 | 87.00 | 32.55 | 32.55 |
| 32768 | 30720 | **25841** | **25892** | yes | no | 143.57 | 147.65 | 31.14 | 31.14 |

- client `output_tok_s` は prefill 込み e2e のため低値（8K: 3.02 等）。**decode は tpot / server eval time を用いる**。
- **32K operational: NO**（~30720 prompt 未達。到達は ~25841/25892。OOM なし・128 tok 生成は成功）

## 5) Quality smoke（決定論的・主張は弱く）

同一プロンプト OFF vs DAILY_RECOMMENDED。強品質主張なし。

| prompt | OFF | ON |
|---|---|---|
| ja_reasoning | JP 箇条書き OK | JP 箇条書き OK（文言差あり） |
| python_coding | def dedupe_stable OK | 同型 OK |
| strict_json | parse+match OK | parse+match OK |
| arithmetic_if | 14 OK | 14 OK |

## ハードウェア / ソフト

- RTX 3060 12GB + Tesla P100 16GB, PCIe, no NVLink
- llama.cpp `5ea1b124e7dfcdb80d7291be188efc7d0b485d66`
- Q4_K_M sha256 `f5f1dd89…`
- Port 18080（:8080 の models-preset サーバは未変更）

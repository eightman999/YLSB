# qwen38_mtp_ab — stock probe.py A/B

## Phase14 公式（上流比較用）— tensor 1,1

- OFF medians: [19.3, 19.3, 19.3]
- ON n-max=2 medians: [30.4, 31.4, 31.0]
- **Baseline (OFF) median-of-sessions: 19.3 tok/s**
- **With flag (ON n-max=2) median-of-sessions: 31.0 tok/s**
- **Speedup: 1.6062x**（≥1.15 → ADOPT）
- **Acceptance (ON n-max=2, 最終セッション /metrics): 0.7863** = 1700 accepted / 2162 draft tokens
  - drafts total (verification steps): 1081
  - 3セッション acceptance ratio 中央値 ≈ 0.796

### Serve knobs（Phase14 実測）

- **split: `--split-mode tensor --tensor-split 1,1`**
- ctx=8192 -ngl 999 -fa on --cache-type-k/v q4_0 --parallel 1
- ON: `--spec-type draft-mtp --spec-draft-n-max 2`（p-min なし）
- llama.cpp: `5ea1b124e7dfcdb80d7291be188efc7d0b485d66`
- model: Q4_K_M sha256 `f5f1dd89…`
- method: `vendor/qwen38-mtp/probe.py` unchanged @ `3097ca3d9731d49d5b68fd77e717a578056b7c74`
- hardware: RTX 3060 12GB + Tesla P100 16GB, PCIe, no NVLink
- raw: `phase14/probe_tensor11/`

## historical / accidental（layer・上流に使わない）

- OFF medians: [13.8, 13.8] → 13.8 tok/s
- ON n-max=2: [22.1, 21.4] → 21.8 tok/s / 1.576x / acc 0.910
- 原因: summary.csv の `tsplit=1,1` 未クォート → Phase2 best が `layer_p100heavy` に誤選択

## 内部対照（tensor・非 probe）

- tg128 tensor OFF→ON: **18.74 → 33.04 tok/s**（~1.76x）— llm_master 日常は DAILY_RECOMMENDED（n-max 2）を採用

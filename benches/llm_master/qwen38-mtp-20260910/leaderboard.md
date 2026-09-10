# Leaderboard — qwen38-mtp-20260910

生成: 2026-09-10T10:24:00+09:00 / Phase14 補正済み

## 標準構成（ADOPT）

**ADOPT**: `llama-server` + Qwen3.8-27B **Q4_K_M** + `--split-mode tensor --tensor-split 1,1` + `--spec-type draft-mtp --spec-draft-n-max 2` + `-c 8192 -ngl 999 -fa on --cache-type-k q4_0 --cache-type-v q4_0 --parallel 1`（PCIe / no NVLink, RTX 3060 12GB + Tesla P100 16GB）。

### 表A — 内部 TG128（非 probe・参考）

| tag | split | mtp | median tok/s | n |
|---|---|---|---:|---:|
| tg128_ON | tensor | ON n2 | 33.04 | 3 |
| tg128_OFF | tensor | OFF | 18.74 | 3 |
| pp512_OFF | tensor | OFF | 18.17 | 3 |

内部 TG128 OFF→ON: **18.74 → 33.04 tok/s（~1.76x）**。上流比較には使わない。

### 表B — stock probe.py tensor 1,1（上流公式・Phase14）

| arm | split | median tok/s | note |
|---|---|---:|---|
| OFF | **tensor 1,1** | **19.3** | 3 sessions 中央値の中央 |
| ON n-max=2 | **tensor 1,1** | **31.0** | **1.606x** / acceptance **0.786**（1700/2162） |

判定: probe speedup ≥1.15 → **ADOPT**。Community 行はこの表B。

### 表C — accidental layer probe（historical・上流に使わない）

| arm | split | median tok/s | note |
|---|---|---:|---|
| OFF | layer（誤選択） | 13.8 | CSV バグ由来 |
| ON n-max=2 | layer | 21.8 | 1.576x / acc 0.910 |

### 表D — Phase14 真長文（DAILY_RECOMMENDED）

| ctx | input actual | TTFT s | decode tok/s (server) | 判定 |
|---:|---:|---:|---:|---|
| 8192 | 7168 | 38.64 | 33.72 | PASS |
| 16384 | 15360 | 83.10 | 32.55 | PASS |
| 32768 | 25841（target 30720） | 143.57 | 31.14 | **32K operational 否**（~30720 未達） |

旧 Phase5（long_c* ~32.8 tok/s）は **サーバ ctx のみ・実入力≤2048**。長文維持の証拠にしない。

### Phase2 OFF split 比較

| tag | median tok/s |
|---|---:|
| tensor_11 | 18.72 |
| tensor_1125 | 17.23 |
| layer_p100heavy | 13.66 |
| layer_def | 13.53 |

## その他

- Phase3B vLLM / 1Cat: **SKIP**（未インストール）
- llama.cpp: `5ea1b124e7dfcdb80d7291be188efc7d0b485d66`
- model Q4_K_M sha256 `f5f1dd89…`
- probe.py unchanged @ `3097ca3d9731d49d5b68fd77e717a578056b7c74`

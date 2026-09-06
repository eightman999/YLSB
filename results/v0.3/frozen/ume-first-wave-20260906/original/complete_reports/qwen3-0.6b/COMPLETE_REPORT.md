# YLSB v0.3 梅 — 完全レポート — `qwen3-0.6b`

- 生成日時(JST): 2026-09-07T00:03:30.894678+09:00
- 試験ID: YLSB-UME / course ume / version 0.3
- Lane: R0（split-mode=layer, Tensor off, MTP off）
- API: `http://100.74.160.53:8080`
- 総壁時計（オリジナル）: **17.323 s**
- 実施: 2026-09-06T23:24:25.690116+09:00 → 2026-09-06T23:24:43.013053+09:00


## 環境・再現メタ

### Runtime
- llama.cpp commit: `5ea1b124e7dfcdb80d7291be188efc7d0b485d66` (short `5ea1b12`)
- binary: `/home/eightman/dev/tools/llama.cpp/build/bin/llama-server`
- version: 0.3.0-dev (build 1, commit 5ea1b12)
- built with: GNU 13.4.0 for Linux x86_64

### GPU / RAM / OS
- GPU ×2: NVIDIA GeForce RTX 3060 12288 MiB + Tesla P100-PCIE-16GB 16384 MiB
- Driver: `580.173.02`
- RAM: MemTotal `32036492` kB（≈30.56 GiB）、Swap 8 GiB
- OS: Ubuntu 26.04 LTS / `Linux master 7.0.0-30-generic #30-Ubuntu SMP PREEMPT_DYNAMIC Fri Jul 31 18:22:54 UTC 2026 x86_64 GNU/Linux`
- CUDA toolkit (nvcc): `12.4.131`

### ctx / KV / batch / FA / seed / max_tokens
- model path: `/home/eightman/gguf-nvme/qwen3-0.6b/Qwen3-0.6B-Q8_0.gguf`
- quant: `Q8_0`
- ctx-size: **32768**
- KV cache-type-k: `f16`（default・未上書き）
- KV cache-type-v: `f16`（default・未上書き）
- KV offload: enabled（default）
- batch-size: **2048** / ubatch-size: **512**（default・未上書き）
- Flash Attention: **auto**（CLI default。実効 on/off は `/props` 非露出のため未解決）
- split-mode: layer / n-gpu-layers: 999 / parallel: 1 / fit: on / jinja: true
- seed: リクエスト未指定 / server default `-1`（props uint32 4294967295）
- temperature: 0.0
- max_tokens: core=256 / sentinel=1024 / api_smoke=64 / PP=1 / TG=target_n
- thinking: `chat_template_kwargs.enable_thinking=false`, `reasoning_effort=none`

### SHA-256
- model: `9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031`
- fixtures:
  - core_ume_28.jsonl: `7ab11a3c2c785c059e5d2f833ce4fe19c61d76089dc18dcb953dc748ec27c270`
  - sentinel_ume_4.jsonl: `1cea1d13bd71a318eeb49590c6c8c9fcd1b55395e981819fa1f0585d7073beae`
  - api_smoke_10.jsonl: `db7dd19622ff68935f9b6745d9680271f2403f6a261ea5abc6b26ba3feba56f7`
- grader `common/grader_basic.py`: `d235f77af3593d8da8f0e456980aa6cf4fdce3610bb6d4fb71246a05f20fc1cb`
- chat template SHA-256: `57f1fd00f0013a2be96aa79b857391f27e23df5b5f847072b524c897e24d0361` (len=4100)

## ハードウェア / モデルカード

### GPU
- 枚数: **2**
- GPU0: NVIDIA GeForce RTX 3060 / 世代 **Ampere (GA106)** / VRAM **12288 MiB GDDR6** / メモリ帯域 **360 GB/s**（公開スペック） / PCIe gen4 x16
- GPU1: Tesla P100-PCIE-16GB / 世代 **Pascal (GP100)** / VRAM **16384 MiB HBM2** / メモリ帯域 **732 GB/s**（公開スペック） / PCIe gen3 x4（max x16）
- interconnect: **PCIe host only** / NVLink=False — heterogeneous 3060+P100; no NVLink/NVSwitch; llama-master split-mode=layer over PCIe

### Runtime / fork
- runtime: `llama.cpp llama-server`
- fork: upstream (ggml-org/llama.cpp), not a custom fork
- commit: `5ea1b124e7dfcdb80d7291be188efc7d0b485d66`
- served via: llama-master multi-model router

### 本モデル
- Dense/MoE: **Dense**
- total params: **0.6B**
- active params: **0.6B**
- quant: **Q8_0**
- quant nominal bpw: **8.0**
- bpw estimate (filesize×8/total_params): **8.526**
- bpw estimate (filesize×8/active_params): **8.526** （参考・MoEでは物理bpwではない）
- GGUF size: **0.596 GiB**
- source: Qwen3-0.6B naming + Q8_0 GGUF

## 品質スコア

| 区分 | 正答 | format | non-empty | INFRA | INVALID | 壁時計 |
|---|---:|---:|---:|---:|---:|---:|
| core | 14/28 (50.0%) | 28/28 (100.0%) | 28/28 (100.0%) | 0 | 0 | 4.1s |
| sentinel | 0/4 (0.0%) | 4/4 (100.0%) | 4/4 (100.0%) | 0 | 0 | 0.5s |
| api_smoke | 3/10 (30.0%) | 10/10 (100.0%) | 10/10 (100.0%) | 0 | 0 | 0.8s |

## ゲート判定

- ❌ **Smallest Meaningful候補**: Core>=60%(50.0%) format>=80%(100.0%) non-empty=100%(100.0%) INFRA=0(0)
- ❌ **Fastest Useful候補**: Core>=80%(50.0%) format>=90%(100.0%) non-empty=100%(100.0%) INFRA=0(0)
- ❌ **梅・難問全通過**: Sentinel 0/4 INVALID=0 INFRA=0 non-empty=4/4

## Cold load（記述のみ・品質ゲート非混在）

- cold_wall_ms: **1041.0**
- was_loaded_before: False
- note: descriptive_only_not_quality_gate; includes_model_load_if_unloaded

## PP（オリジナル run・各 repeat）

| target | rep | actual | prompt_n | cache_n | wall_ms | tps | prompt_ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 1 | 183 | 183 | 0 | 55.3 | 5821.351 | 31.436 |
| 128 | 2 | 182 | 171 | 11 | 65.2 | 5640.4 | 30.317 |
| 128 | 3 | 182 | 171 | 11 | 54.1 | 5776.637 | 29.602 |
| 512 | 1 | 565 | 565 | 0 | 107.5 | 7525.507 | 75.078 |
| 512 | 2 | 568 | 557 | 11 | 112.8 | 7106.223 | 78.382 |
| 512 | 3 | 569 | 558 | 11 | 112.7 | 7124.344 | 78.323 |
| 2048 | 1 | 2104 | 2104 | 0 | 474.7 | 8621.255 | 244.048 |
| 2048 | 2 | 2103 | 2091 | 12 | 373.1 | 8151.951 | 256.503 |
| 2048 | 3 | 2105 | 2093 | 12 | 372.8 | 8155.52 | 256.636 |

| target | n | tps mean | tps median | tps stdev | wall mean | wall median | wall stdev | cache_n |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 128 | 3 | 5746.129 | 5776.637 | 94.254 | 58.2 | 55.3 | 6.1 | [0, 11, 11] |
| 512 | 3 | 7252.025 | 7124.344 | 237.016 | 111.0 | 112.7 | 3.0 | [0, 11, 11] |
| 2048 | 3 | 8309.575 | 8155.520 | 269.928 | 406.9 | 373.1 | 58.7 | [0, 12, 12] |

- section wall: 2.281s
- オリジナル run 中の VRAM: **未計測**（下の再測定節を正とする）

## TG（オリジナル run・各 repeat）

| target | rep | tg_actual | prompt_n | cache_n | wall_ms | tps | predicted_ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 32 | 1 | 32 | 99 | 0 | 190.4 | 192.213 | 161.279 |
| 32 | 2 | 32 | 88 | 11 | 193.9 | 212.198 | 146.09 |
| 32 | 3 | 32 | 88 | 11 | 176.1 | 214.951 | 144.219 |
| 128 | 1 | 128 | 93 | 7 | 619.8 | 216.091 | 587.716 |
| 128 | 2 | 128 | 88 | 12 | 643.7 | 209.614 | 605.875 |
| 128 | 3 | 128 | 88 | 12 | 623.7 | 216.727 | 585.991 |

| target | n | tps mean | tps median | tps stdev | wall mean | wall median | wall stdev | cache_n |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 32 | 3 | 206.454 | 212.198 | 12.410 | 186.8 | 190.4 | 9.4 | [0, 11, 11] |
| 128 | 3 | 214.144 | 216.091 | 3.936 | 629.1 | 623.7 | 12.8 | [7, 12, 12] |

- section wall: 2.622s
- オリジナル run 中の VRAM: **未計測**（下の再測定節を正とする）

## PP/TG 再測定 + VRAM

- 再測定日時(JST): `2026-09-07T00:05:45.092957+09:00`
- API: `http://100.74.160.53:8080`
- 方法: strong unique prefix cache-bust / PP は cache_n==0 優先（rep あたり最大5試行）
- VRAM: `nvidia-smi` をリクエスト中 50ms 間隔でサンプリング（before/during/after）
- Flash Attention: server default -fa auto; effective on/off 未解決（ログ/metricsから確定できず）
- load_wall_s: `1.3` / ok=`True`
- VRAM after load: GPU0=`2204` MiB / GPU1=`2768` MiB

### PP 生値（再測定・各 repeat）

| target | rep | attempt | usage_pt | prompt_n | cache_n | wall_ms | tps | prompt_ms | prompt_per_second | VRAM0_max | VRAM1_max | n_smi |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 1 | 1 | 437 | 436 | 1 | 73.5 | 7850.763 | 55.536 | 7850.763468740996 | 2206 | 2794 | 1 |
| 128 | 2 | 1 | 438 | 427 | 11 | 147.9 | 7498.068 | 56.948 | 7498.068413289317 | 2206 | 2804 | 2 |
| 128 | 3 | 1 | 438 | 427 | 11 | 135.6 | 7780.329 | 54.882 | 7780.328705222113 | 2206 | 2804 | 2 |
| 512 | 1 | 1 | 825 | 819 | 6 | 192.2 | 8008.84 | 102.262 | 8008.84003833291 | 2206 | 2804 | 3 |
| 512 | 2 | 1 | 826 | 815 | 11 | 252.1 | 8167.478 | 99.786 | 8167.478403784098 | 2206 | 2804 | 4 |
| 512 | 3 | 1 | 826 | 815 | 11 | 255.3 | 8135.925 | 100.173 | 8135.924850009484 | 2206 | 2804 | 4 |
| 2048 | 1 | 1 | 2389 | 2383 | 6 | 457.1 | 7751.383 | 307.429 | 7751.383246212947 | 2206 | 2804 | 6 |
| 2048 | 2 | 1 | 2389 | 2377 | 12 | 580.6 | 8202.633 | 289.785 | 8202.632986524492 | 2206 | 2804 | 8 |
| 2048 | 3 | 1 | 2388 | 2376 | 12 | 561.7 | 8175.568 | 290.622 | 8175.568263930466 | 2206 | 2804 | 8 |

### PP 要約（再測定）

| target | n | tps mean | tps median | tps stdev | wall mean | wall median | wall stdev | cache_n | VRAM0_peak | VRAM1_peak |
|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| 128 | 3 | 7709.72 | 7780.329 | 186.649 | 119.0 | 135.6 | 39.9 | [1, 11, 11] | 2206 | 2804 |
| 512 | 3 | 8104.081 | 8135.925 | 83.976 | 233.2 | 252.1 | 35.5 | [6, 11, 11] | 2206 | 2804 |
| 2048 | 3 | 8043.195 | 8175.568 | 253.078 | 533.1 | 561.7 | 66.5 | [6, 12, 12] | 2206 | 2804 |

#### PP 確定値（cache_n==0 優先。不可なら最小 cache_n）

- **PP 128**: method=`no cache_n==0; first rep fallback` zero_count=`0` rep=`1` attempt=`1` usage_pt=`437` prompt_n=`436` cache_n=`1` wall_ms=`73.5` tps=`7850.763` prompt_ms=`55.536` prompt_per_second=`7850.763468740996` VRAM0_max=`2206` VRAM1_max=`2794` n_smi=`1`
- **PP 512**: method=`no cache_n==0; first rep fallback` zero_count=`0` rep=`1` attempt=`1` usage_pt=`825` prompt_n=`819` cache_n=`6` wall_ms=`192.2` tps=`8008.84` prompt_ms=`102.262` prompt_per_second=`8008.84003833291` VRAM0_max=`2206` VRAM1_max=`2804` n_smi=`3`
- **PP 2048**: method=`no cache_n==0; first rep fallback` zero_count=`0` rep=`1` attempt=`1` usage_pt=`2389` prompt_n=`2383` cache_n=`6` wall_ms=`457.1` tps=`7751.383` prompt_ms=`307.429` prompt_per_second=`7751.383246212947` VRAM0_max=`2206` VRAM1_max=`2804` n_smi=`6`

### TG 生値（再測定・各 repeat）

| target | rep | tg_actual | prompt_n | cache_n | wall_ms | tps | predicted_ms | predicted_per_second | VRAM0_max | VRAM1_max | n_smi |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 32 | 1 | 32 | 368 | 3 | 464.1 | 196.827 | 157.499 | 196.8266465183906 | 2206 | 2804 | 6 |
| 32 | 2 | 32 | 360 | 11 | 275.4 | 203.918 | 152.022 | 203.91785399481654 | 2206 | 2804 | 4 |
| 32 | 3 | 32 | 360 | 11 | 277.5 | 200.035 | 154.973 | 200.0348447794132 | 2206 | 2804 | 4 |
| 128 | 1 | 128 | 366 | 7 | 741.3 | 208.812 | 608.203 | 208.81186051367717 | 2206 | 2804 | 10 |
| 128 | 2 | 128 | 362 | 12 | 750.0 | 209.855 | 605.181 | 209.85457243370163 | 2206 | 2804 | 10 |
| 128 | 3 | 128 | 362 | 12 | 759.5 | 208.261 | 609.811 | 208.2612481572159 | 2206 | 2804 | 10 |

### TG 要約（再測定）

| target | n | tps mean | tps median | tps stdev | wall mean | wall median | wall stdev | cache_n | tg_actual | VRAM0_peak | VRAM1_peak |
|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|
| 32 | 3 | 200.26 | 200.035 | 3.551 | 339.0 | 277.5 | 108.3 | [3, 11, 11] | [32, 32, 32] | 2206 | 2804 |
| 128 | 3 | 208.976 | 208.812 | 0.81 | 750.3 | 750.0 | 9.1 | [7, 12, 12] | [128, 128, 128] | 2206 | 2804 |

### VRAM ピーク要約（再測定中）

- PP/TG 全体ピーク: GPU0(RTX3060)=`2206` MiB / GPU1(P100)=`2804` MiB
- after_load: GPU0=`2204` / GPU1=`2768` MiB
- idle（unload後）: GPU0=`43` / GPU1=`6` MiB

- note: PP/TG via /v1/completions; strong unique prefixes; prefer cache_n==0 (up to 5 attempts/rep)
- note: VRAM sampled via nvidia-smi every 50ms during each request (before/during/after)
- note: tps for PP prefers timings.prompt_ms; TG prefers timings.predicted_per_second


## 再計測 PP（qwen3-0.6b / 既存 pp_remeasure.json）

**PP 512 確定**（cache_n==0 rep1）: wall_ms=`155.4`, tps=`7475.62`, pt=`565`, prompt_n=`565`, cache_n=0, prompt_per_second=`7475.621535082498`

詳細は `pp_remeasure.json` 参照（128/2048 の各 repeat・cache_n 含む）。

## Depth

- d0: pp=540 tg=128 wall_ms=773.8 pp_tps=7035.188972992691 tg_tps=209.32777763126666 note=calibrated_cpt=5.510_hit_rep1
- d8K: pp=8222 tg=128 wall_ms=2928.7 pp_tps=5566.564863479693 tg_tps=141.02555560737596 note=calibrated_cpt=5.510_hit_rep1
- section wall: 5.415s

## 失敗ケース（Core/Sentinel/API）

- `core` `CORE-MATH_WORD-001` [CAPABILITY] gold=440 ans='1000円' note=wrong
- `core` `CORE-MATH_WORD-002` [CAPABILITY] gold=180 ans='3.6 分' note=wrong
- `core` `CORE-MATH_WORD-004` [CAPABILITY] gold=343 ans='380' note=wrong
- `core` `CORE-CONSTRAINT-001` [CAPABILITY] gold='ABEDC' ans='- A-B-C-D-E' note=wrong
- `core` `CORE-CONSTRAINT-002` [CAPABILITY] gold='EDACB' ans='- A-C-E-D-B' note=wrong
- `core` `CORE-CONSTRAINT-003` [CAPABILITY] gold='DCABE' ans='["C", "B", "A", "D", "E"]' note=wrong
- `core` `CORE-CONSTRAINT-004` [CAPABILITY] gold='DACEB' ans='- E: B' note=wrong
- `core` `CORE-READING-001` [CAPABILITY] gold='アキ' ans='{"name": "アキ", "score": 95}' note=wrong
- `core` `CORE-READING-002` [CAPABILITY] gold='Python' ans='Rust' note=wrong
- `core` `CORE-COMMON_SENSE-002` [CAPABILITY] gold='A' ans='D' note=wrong
- `core` `CORE-INSTRUCTION-001` [CAPABILITY] gold={'result': [10, 16, 19, 23, 29, 39]} ans='[19, 29, 10, 23, 16, 39]' note=wrong
- `core` `CORE-INSTRUCTION-002` [CAPABILITY] gold={'even': [2, 2], 'count': 2} ans='{"even":[7,13,1,2,13,19,15,2], "count":8}' note=wrong
- `core` `CORE-INSTRUCTION-003` [CAPABILITY] gold='ACE' ans='Ab3Cd4Ef' note=wrong
- `core` `CORE-INSTRUCTION-004` [CAPABILITY] gold='4,2,6,1,7' ans='[4, 6, 6, 6, 7, 6]' note=wrong
- `sentinel` `H01` [CAPABILITY] gold=362 ans='10' note=wrong
- `sentinel` `H02` [CAPABILITY] gold='AEBDC' ans='{"A": "C", "B": "E", "C": "D", "E": "B", "D": "A"}' note=wrong
- `sentinel` `H03` [CAPABILITY] gold='10:A-C-B-D-E' ans='A→C→E' note=wrong
- `sentinel` `H04` [CAPABILITY] gold=75 ans='[1, 2, 3, 4, 5]' note=wrong
- `api_smoke` `REL-001` [CAPABILITY] gold=111 ans='157' note=wrong
- `api_smoke` `REL-002` [CAPABILITY] gold=119 ans='114+5' note=wrong
- `api_smoke` `REL-004` [CAPABILITY] gold=135 ans='196' note=wrong
- `api_smoke` `REL-005` [CAPABILITY] gold=143 ans='135+8' note=wrong
- `api_smoke` `REL-006` [CAPABILITY] gold=151 ans='242' note=wrong
- `api_smoke` `REL-009` [CAPABILITY] gold=166 ans='163+3' note=wrong
- `api_smoke` `REL-010` [CAPABILITY] gold=174 ans='210' note=wrong

## 成果物
- `raw.jsonl` / `summary.json` / `run.log`
- `remeasure_pp_tg_vram.json` / `pp_tg_vram.jsonl`
- 本ファイル `COMPLETE_REPORT.md`

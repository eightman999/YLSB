# YLSB v0.3 梅 — 完全レポート — `nemotron-3.5-lightning-30b-a3b`

- 生成日時(JST): 2026-09-07T00:03:30.904041+09:00
- 試験ID: YLSB-UME / course ume / version 0.3
- Lane: R0（split-mode=layer, Tensor off, MTP off）
- API: `http://100.74.160.53:8080`
- 総壁時計（オリジナル）: **174.437 s**
- 実施: 2026-09-06T23:44:56.950105+09:00 → 2026-09-06T23:47:51.386623+09:00


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
- model path: `/home/eightman/gguf-nvme/nemotron-3.5-lightning-30b-a3b/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Q4_0.gguf`
- quant: `Q4_0`
- ctx-size: **65536**
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
- model: `61f87e75974e4b535dcdf9aad056541a9514f1dfa4538b463b081d19b7a00e3c`
- fixtures:
  - core_ume_28.jsonl: `7ab11a3c2c785c059e5d2f833ce4fe19c61d76089dc18dcb953dc748ec27c270`
  - sentinel_ume_4.jsonl: `1cea1d13bd71a318eeb49590c6c8c9fcd1b55395e981819fa1f0585d7073beae`
  - api_smoke_10.jsonl: `db7dd19622ff68935f9b6745d9680271f2403f6a261ea5abc6b26ba3feba56f7`
- grader `common/grader_basic.py`: `d235f77af3593d8da8f0e456980aa6cf4fdce3610bb6d4fb71246a05f20fc1cb`
- chat template SHA-256: `58933db77d3099b4f78c55a38347a72e1ea05b97d6bd8f38775303dc0194e0a9` (len=9867)

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
- Dense/MoE: **MoE**
- total params: **30B**
- active params: **3B (A3B)**
- quant: **Q4_0**
- quant nominal bpw: **4.5**
- bpw estimate (filesize×8/total_params): **5.039**
- bpw estimate (filesize×8/active_params): **50.395** （参考・MoEでは物理bpwではない）
- GGUF size: **17.6 GiB**
- source: NVIDIA Nemotron 3.5 Lightning 30B-A3B naming + Q4_0 GGUF

## 品質スコア

| 区分 | 正答 | format | non-empty | INFRA | INVALID | 壁時計 |
|---|---:|---:|---:|---:|---:|---:|
| core | 13/28 (46.4%) | 28/28 (100.0%) | 28/28 (100.0%) | 0 | 0 | 36.7s |
| sentinel | 0/4 (0.0%) | 4/4 (100.0%) | 4/4 (100.0%) | 0 | 0 | 5.5s |
| api_smoke | 10/10 (100.0%) | 10/10 (100.0%) | 10/10 (100.0%) | 0 | 0 | 9.6s |

## ゲート判定

- ❌ **Smallest Meaningful候補**: Core>=60%(46.4%) format>=80%(100.0%) non-empty=100%(100.0%) INFRA=0(0)
- ❌ **Fastest Useful候補**: Core>=80%(46.4%) format>=90%(100.0%) non-empty=100%(100.0%) INFRA=0(0)
- ❌ **梅・難問全通過**: Sentinel 0/4 INVALID=0 INFRA=0 non-empty=4/4

## Cold load（記述のみ・品質ゲート非混在）

- cold_wall_ms: **20603.9**
- was_loaded_before: False
- note: descriptive_only_not_quality_gate; includes_model_load_if_unloaded

## PP（オリジナル run・各 repeat）

| target | rep | actual | prompt_n | cache_n | wall_ms | tps | prompt_ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 1 | 236 | 236 | 0 | 1388.9 | 361.826 | 652.247 |
| 128 | 2 | 235 | 235 | 0 | 1427.2 | 361.815 | 649.504 |
| 128 | 3 | 236 | 236 | 0 | 1404.4 | 365.345 | 645.965 |
| 512 | 1 | 621 | 621 | 0 | 2121.8 | 521.904 | 1189.873 |
| 512 | 2 | 623 | 623 | 0 | 2073.7 | 522.855 | 1191.536 |
| 512 | 3 | 623 | 623 | 0 | 2065.6 | 521.621 | 1194.353 |
| 2048 | 1 | 2157 | 2157 | 0 | 3744.6 | 837.164 | 2576.556 |
| 2048 | 2 | 2156 | 2156 | 0 | 3647.1 | 841.88 | 2560.935 |
| 2048 | 3 | 2157 | 2157 | 0 | 3792.7 | 844.531 | 2554.079 |

| target | n | tps mean | tps median | tps stdev | wall mean | wall median | wall stdev | cache_n |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 128 | 3 | 362.995 | 361.826 | 2.035 | 1406.8 | 1404.4 | 19.3 | [0, 0, 0] |
| 512 | 3 | 522.127 | 521.904 | 0.646 | 2087.0 | 2073.7 | 30.4 | [0, 0, 0] |
| 2048 | 3 | 841.192 | 841.880 | 3.731 | 3728.1 | 3744.6 | 74.2 | [0, 0, 0] |

- section wall: 38.892s
- オリジナル run 中の VRAM: **未計測**（下の再測定節を正とする）

## TG（オリジナル run・各 repeat）

| target | rep | tg_actual | prompt_n | cache_n | wall_ms | tps | predicted_ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 32 | 1 | 32 | 99 | 0 | 1632.8 | 80.673 | 384.268 |
| 32 | 2 | 32 | 99 | 0 | 1578.4 | 80.974 | 382.838 |
| 32 | 3 | 32 | 99 | 0 | 1588.3 | 80.85 | 383.424 |
| 128 | 1 | 128 | 100 | 0 | 2766.8 | 81.073 | 1566.489 |
| 128 | 2 | 128 | 100 | 0 | 2879.3 | 80.695 | 1573.833 |
| 128 | 3 | 128 | 100 | 0 | 2828.8 | 80.445 | 1578.726 |

| target | n | tps mean | tps median | tps stdev | wall mean | wall median | wall stdev | cache_n |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 32 | 3 | 80.832 | 80.850 | 0.151 | 1599.8 | 1588.3 | 29.0 | [0, 0, 0] |
| 128 | 3 | 80.738 | 80.695 | 0.316 | 2825.0 | 2828.8 | 56.3 | [0, 0, 0] |

- section wall: 17.484s
- オリジナル run 中の VRAM: **未計測**（下の再測定節を正とする）

## PP/TG 再測定 + VRAM

- 再測定日時(JST): `2026-09-07T00:12:00.823431+09:00`
- API: `http://100.74.160.53:8080`
- 方法: strong unique prefix cache-bust / PP は cache_n==0 優先（rep あたり最大5試行）
- VRAM: `nvidia-smi` をリクエスト中 50ms 間隔でサンプリング（before/during/after）
- Flash Attention: server default -fa auto; effective on/off 未解決（ログ/metricsから確定できず）
- load_wall_s: `17.313` / ok=`True`
- VRAM after load: GPU0=`8260` MiB / GPU1=`10980` MiB

### PP 生値（再測定・各 repeat）

| target | rep | attempt | usage_pt | prompt_n | cache_n | wall_ms | tps | prompt_ms | prompt_per_second | VRAM0_max | VRAM1_max | n_smi |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 1 | 1 | 468 | 468 | 0 | 951.8 | 569.112 | 822.334 | 569.1118207443692 | 8302 | 11058 | 13 |
| 128 | 2 | 1 | 468 | 468 | 0 | 953.0 | 570.628 | 820.149 | 570.6280200305066 | 8302 | 11058 | 13 |
| 128 | 3 | 1 | 468 | 468 | 0 | 953.3 | 571.157 | 819.39 | 571.1565920990005 | 8302 | 11058 | 13 |
| 512 | 1 | 1 | 844 | 844 | 0 | 1622.1 | 567.176 | 1488.075 | 567.1757135897047 | 8302 | 11058 | 22 |
| 512 | 2 | 1 | 846 | 846 | 0 | 1655.6 | 573.002 | 1476.434 | 573.0022473066863 | 8302 | 11058 | 23 |
| 512 | 3 | 1 | 845 | 845 | 0 | 1652.4 | 573.37 | 1473.742 | 573.3703728332367 | 8302 | 11058 | 23 |
| 2048 | 1 | 1 | 2443 | 2443 | 0 | 3274.8 | 791.679 | 3085.848 | 791.6786568878313 | 8302 | 11058 | 45 |
| 2048 | 2 | 1 | 2443 | 2443 | 0 | 3280.9 | 789.073 | 3096.037 | 789.0732571994457 | 8302 | 11058 | 45 |
| 2048 | 3 | 1 | 2443 | 2443 | 0 | 3279.0 | 791.618 | 3086.084 | 791.6181153850641 | 8302 | 11058 | 45 |

### PP 要約（再測定）

| target | n | tps mean | tps median | tps stdev | wall mean | wall median | wall stdev | cache_n | VRAM0_peak | VRAM1_peak |
|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| 128 | 3 | 570.299 | 570.628 | 1.061 | 952.7 | 953.0 | 0.8 | [0, 0, 0] | 8302 | 11058 |
| 512 | 3 | 571.183 | 573.002 | 3.475 | 1643.4 | 1652.4 | 18.5 | [0, 0, 0] | 8302 | 11058 |
| 2048 | 3 | 790.79 | 791.618 | 1.487 | 3278.2 | 3279.0 | 3.1 | [0, 0, 0] | 8302 | 11058 |

#### PP 確定値（cache_n==0 優先。不可なら最小 cache_n）

- **PP 128**: method=`cache_n==0 first available` zero_count=`3` rep=`1` attempt=`1` usage_pt=`468` prompt_n=`468` cache_n=`0` wall_ms=`951.8` tps=`569.112` prompt_ms=`822.334` prompt_per_second=`569.1118207443692` VRAM0_max=`8302` VRAM1_max=`11058` n_smi=`13`
- **PP 512**: method=`cache_n==0 first available` zero_count=`3` rep=`1` attempt=`1` usage_pt=`844` prompt_n=`844` cache_n=`0` wall_ms=`1622.1` tps=`567.176` prompt_ms=`1488.075` prompt_per_second=`567.1757135897047` VRAM0_max=`8302` VRAM1_max=`11058` n_smi=`22`
- **PP 2048**: method=`cache_n==0 first available` zero_count=`3` rep=`1` attempt=`1` usage_pt=`2443` prompt_n=`2443` cache_n=`0` wall_ms=`3274.8` tps=`791.679` prompt_ms=`3085.848` prompt_per_second=`791.6786568878313` VRAM0_max=`8302` VRAM1_max=`11058` n_smi=`45`

### TG 生値（再測定・各 repeat）

| target | rep | tg_actual | prompt_n | cache_n | wall_ms | tps | predicted_ms | predicted_per_second | VRAM0_max | VRAM1_max | n_smi |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 32 | 1 | 32 | 400 | 0 | 1324.9 | 81.547 | 380.15 | 81.54675785873997 | 8302 | 11058 | 18 |
| 32 | 2 | 32 | 400 | 0 | 1272.8 | 81.943 | 378.314 | 81.94251336191628 | 8302 | 11058 | 18 |
| 32 | 3 | 32 | 399 | 0 | 1275.3 | 82.005 | 378.024 | 82.00537532008549 | 8302 | 11058 | 18 |
| 128 | 1 | 128 | 403 | 0 | 2446.0 | 82.019 | 1548.429 | 82.01861370459994 | 8302 | 11058 | 34 |
| 128 | 2 | 128 | 403 | 0 | 2458.1 | 81.799 | 1552.591 | 81.79874802829593 | 8302 | 11058 | 34 |
| 128 | 3 | 128 | 404 | 0 | 2458.2 | 81.633 | 1555.75 | 81.63265306122449 | 8302 | 11058 | 34 |

### TG 要約（再測定）

| target | n | tps mean | tps median | tps stdev | wall mean | wall median | wall stdev | cache_n | tg_actual | VRAM0_peak | VRAM1_peak |
|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|
| 32 | 3 | 81.832 | 81.943 | 0.248 | 1291.0 | 1275.3 | 29.4 | [0, 0, 0] | [32, 32, 32] | 8302 | 11058 |
| 128 | 3 | 81.817 | 81.799 | 0.194 | 2454.1 | 2458.1 | 7.0 | [0, 0, 0] | [128, 128, 128] | 8302 | 11058 |

### VRAM ピーク要約（再測定中）

- PP/TG 全体ピーク: GPU0(RTX3060)=`8302` MiB / GPU1(P100)=`11058` MiB
- after_load: GPU0=`8260` / GPU1=`10980` MiB
- idle（unload後）: GPU0=`43` / GPU1=`6` MiB

- note: PP/TG via /v1/completions; strong unique prefixes; prefer cache_n==0 (up to 5 attempts/rep)
- note: VRAM sampled via nvidia-smi every 50ms during each request (before/during/after)
- note: tps for PP prefers timings.prompt_ms; TG prefers timings.predicted_per_second


## Depth

- d0: pp=543 tg=128 wall_ms=3434.3 pp_tps=588.2110800335378 tg_tps=80.44400020776088 note=calibrated_cpt=5.236_hit_rep1
- d8K: pp=8222 tg=128 wall_ms=10925.0 pp_tps=1037.0688413410808 tg_tps=80.50258971126193 note=calibrated_cpt=5.236_hit_rep1
- section wall: 36.29s

## 失敗ケース（Core/Sentinel/API）

- `core` `CORE-ARITHMETIC-002` [CAPABILITY] gold=84 ans='79' note=wrong
- `core` `CORE-ARITHMETIC-003` [CAPABILITY] gold=117 ans='103' note=wrong
- `core` `CORE-ARITHMETIC-004` [CAPABILITY] gold=156 ans='142' note=wrong
- `core` `CORE-MATH_WORD-001` [CAPABILITY] gold=440 ans='295' note=wrong
- `core` `CORE-MATH_WORD-002` [CAPABILITY] gold=180 ans='150' note=wrong
- `core` `CORE-MATH_WORD-003` [CAPABILITY] gold=40 ans='55' note=wrong
- `core` `CORE-MATH_WORD-004` [CAPABILITY] gold=343 ans='391' note=wrong
- `core` `CORE-LOGIC-004` [CAPABILITY] gold=0 ans='1' note=wrong
- `core` `CORE-CONSTRAINT-001` [CAPABILITY] gold='ABEDC' ans='BACDE' note=wrong
- `core` `CORE-CONSTRAINT-002` [CAPABILITY] gold='EDACB' ans='C-B-D-A-E' note=wrong
- `core` `CORE-CONSTRAINT-003` [CAPABILITY] gold='DCABE' ans='C-B-A-D-E' note=wrong
- `core` `CORE-CONSTRAINT-004` [CAPABILITY] gold='DACEB' ans='C-A-D-E-B' note=wrong
- `core` `CORE-COMMON_SENSE-001` [CAPABILITY] gold='A' ans='A:溶ける' note=wrong
- `core` `CORE-COMMON_SENSE-004` [CAPABILITY] gold='A' ans='A:あふれる' note=wrong
- `core` `CORE-INSTRUCTION-003` [CAPABILITY] gold='ACE' ans='ABCDEf' note=wrong
- `sentinel` `H01` [CAPABILITY] gold=362 ans='101' note=wrong
- `sentinel` `H02` [CAPABILITY] gold='AEBDC' ans='CDEAB' note=wrong
- `sentinel` `H03` [CAPABILITY] gold='10:A-C-B-D-E' ans='cost:19,path:A→C→B→D→E' note=wrong
- `sentinel` `H04` [CAPABILITY] gold=75 ans='100' note=wrong

## 成果物
- `raw.jsonl` / `summary.json` / `run.log`
- `remeasure_pp_tg_vram.json` / `pp_tg_vram.jsonl`
- 本ファイル `COMPLETE_REPORT.md`

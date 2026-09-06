# YLSB v0.3 梅 — 完全レポート — `glm-4.7-flash`

- 生成日時(JST): 2026-09-07T00:03:30.901651+09:00
- 試験ID: YLSB-UME / course ume / version 0.3
- Lane: R0（split-mode=layer, Tensor off, MTP off）
- API: `http://100.74.160.53:8080`
- 総壁時計（オリジナル）: **189.213 s**
- 実施: 2026-09-06T23:41:39.693232+09:00 → 2026-09-06T23:44:48.906016+09:00


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
- model path: `/home/eightman/gguf-nvme/glm-4.7-flash/GLM-4.7-Flash-Q4_K_M.gguf`
- quant: `Q4_K_M`
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
- model: `29837ed2c0fc5f51981adf8ac8083fcf80743c598381f13e9f06cbad0498b174`
- fixtures:
  - core_ume_28.jsonl: `7ab11a3c2c785c059e5d2f833ce4fe19c61d76089dc18dcb953dc748ec27c270`
  - sentinel_ume_4.jsonl: `1cea1d13bd71a318eeb49590c6c8c9fcd1b55395e981819fa1f0585d7073beae`
  - api_smoke_10.jsonl: `db7dd19622ff68935f9b6745d9680271f2403f6a261ea5abc6b26ba3feba56f7`
- grader `common/grader_basic.py`: `d235f77af3593d8da8f0e456980aa6cf4fdce3610bb6d4fb71246a05f20fc1cb`
- chat template SHA-256: `d63ad536c3c81880043e22ec7fd08db42b4d8fb7c89c7138bc562bfa25281375` (len=3120)

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
- active params: **~3B (A3B)**
- quant: **Q4_K_M**
- quant nominal bpw: **4.83**
- bpw estimate (filesize×8/total_params): **4.883**
- bpw estimate (filesize×8/active_params): **48.833** （参考・MoEでは物理bpwではない）
- GGUF size: **17.055 GiB**
- source: Z.AI/Zhipu GLM-4.7-Flash 30B-A3B MoE model card

## 品質スコア

| 区分 | 正答 | format | non-empty | INFRA | INVALID | 壁時計 |
|---|---:|---:|---:|---:|---:|---:|
| core | 17/28 (60.7%) | 28/28 (100.0%) | 28/28 (100.0%) | 0 | 0 | 29.8s |
| sentinel | 0/4 (0.0%) | 4/4 (100.0%) | 4/4 (100.0%) | 0 | 0 | 4.4s |
| api_smoke | 10/10 (100.0%) | 10/10 (100.0%) | 10/10 (100.0%) | 0 | 0 | 8.0s |

## ゲート判定

- ✅ **Smallest Meaningful候補**: Core>=60%(60.7%) format>=80%(100.0%) non-empty=100%(100.0%) INFRA=0(0)
- ❌ **Fastest Useful候補**: Core>=80%(60.7%) format>=90%(100.0%) non-empty=100%(100.0%) INFRA=0(0)
- ❌ **梅・難問全通過**: Sentinel 0/4 INVALID=0 INFRA=0 non-empty=4/4

## Cold load（記述のみ・品質ゲート非混在）

- cold_wall_ms: **24853.2**
- was_loaded_before: False
- note: descriptive_only_not_quality_gate; includes_model_load_if_unloaded

## PP（オリジナル run・各 repeat）

| target | rep | actual | prompt_n | cache_n | wall_ms | tps | prompt_ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 1 | 170 | 170 | 0 | 1305.7 | 302.541 | 561.907 |
| 128 | 2 | 169 | 160 | 9 | 1189.2 | 294.699 | 542.926 |
| 128 | 3 | 168 | 159 | 9 | 1183.0 | 293.112 | 542.454 |
| 512 | 1 | 552 | 552 | 0 | 1917.8 | 491.853 | 1122.287 |
| 512 | 2 | 553 | 544 | 9 | 1813.5 | 493.733 | 1101.81 |
| 512 | 3 | 555 | 546 | 9 | 1859.8 | 481.667 | 1133.564 |
| 2048 | 1 | 2091 | 2091 | 0 | 4592.7 | 599.054 | 3490.501 |
| 2048 | 2 | 2091 | 2081 | 10 | 4781.8 | 582.818 | 3570.585 |
| 2048 | 3 | 2093 | 2083 | 10 | 4622.7 | 581.82 | 3580.145 |

| target | n | tps mean | tps median | tps stdev | wall mean | wall median | wall stdev | cache_n |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 128 | 3 | 296.784 | 294.699 | 5.048 | 1226.0 | 1189.2 | 69.1 | [0, 9, 9] |
| 512 | 3 | 489.084 | 491.853 | 6.492 | 1863.7 | 1859.8 | 52.3 | [0, 9, 9] |
| 2048 | 3 | 587.897 | 582.818 | 9.675 | 4665.7 | 4622.7 | 101.6 | [0, 10, 10] |

- section wall: 39.124s
- オリジナル run 中の VRAM: **未計測**（下の再測定節を正とする）

## TG（オリジナル run・各 repeat）

| target | rep | tg_actual | prompt_n | cache_n | wall_ms | tps | predicted_ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 32 | 1 | 32 | 91 | 0 | 1587.1 | 54.192 | 572.036 |
| 32 | 2 | 32 | 80 | 10 | 1546.1 | 54.155 | 572.433 |
| 32 | 3 | 32 | 81 | 10 | 1588.6 | 53.647 | 577.852 |
| 128 | 1 | 128 | 84 | 7 | 3328.8 | 54.465 | 2331.788 |
| 128 | 2 | 128 | 81 | 10 | 3337.5 | 54.33 | 2337.568 |
| 128 | 3 | 128 | 80 | 10 | 3312.9 | 54.357 | 2336.404 |

| target | n | tps mean | tps median | tps stdev | wall mean | wall median | wall stdev | cache_n |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 32 | 3 | 53.998 | 54.155 | 0.305 | 1573.9 | 1587.1 | 24.1 | [0, 10, 10] |
| 128 | 3 | 54.384 | 54.357 | 0.071 | 3326.4 | 3328.8 | 12.5 | [7, 10, 10] |

- section wall: 18.073s
- オリジナル run 中の VRAM: **未計測**（下の再測定節を正とする）

## PP/TG 再測定 + VRAM

- 再測定日時(JST): `2026-09-07T00:10:50.364063+09:00`
- API: `http://100.74.160.53:8080`
- 方法: strong unique prefix cache-bust / PP は cache_n==0 優先（rep あたり最大5試行）
- VRAM: `nvidia-smi` をリクエスト中 50ms 間隔でサンプリング（before/during/after）
- Flash Attention: server default -fa auto; effective on/off 未解決（ログ/metricsから確定できず）
- load_wall_s: `26.262` / ok=`True`
- VRAM after load: GPU0=`9444` MiB / GPU1=`12380` MiB

### PP 生値（再測定・各 repeat）

| target | rep | attempt | usage_pt | prompt_n | cache_n | wall_ms | tps | prompt_ms | prompt_per_second | VRAM0_max | VRAM1_max | n_smi |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 1 | 1 | 378 | 377 | 1 | 844.8 | 469.825 | 802.426 | 469.8252549144719 | 9468 | 12472 | 12 |
| 128 | 2 | 1 | 380 | 371 | 9 | 831.5 | 471.288 | 787.204 | 471.28825564910755 | 9468 | 12472 | 12 |
| 128 | 3 | 1 | 381 | 372 | 9 | 816.9 | 478.749 | 777.025 | 478.749074997587 | 9468 | 12472 | 11 |
| 512 | 1 | 1 | 762 | 756 | 6 | 1493.5 | 521.087 | 1450.813 | 521.0871421747669 | 9468 | 12472 | 21 |
| 512 | 2 | 1 | 758 | 749 | 9 | 1514.7 | 519.535 | 1441.675 | 519.53456916434 | 9468 | 12472 | 21 |
| 512 | 3 | 1 | 765 | 756 | 9 | 1525.4 | 520.627 | 1452.096 | 520.6267354224514 | 9468 | 12472 | 21 |
| 2048 | 1 | 1 | 2301 | 2295 | 6 | 4068.2 | 575.69 | 3986.518 | 575.6903643731196 | 9468 | 12472 | 56 |
| 2048 | 2 | 1 | 2303 | 2293 | 10 | 4191.1 | 573.085 | 4001.155 | 573.0845218443175 | 9468 | 12472 | 58 |
| 2048 | 3 | 1 | 2302 | 2292 | 10 | 4214.0 | 573.475 | 3996.688 | 573.4748371651729 | 9468 | 12472 | 58 |

### PP 要約（再測定）

| target | n | tps mean | tps median | tps stdev | wall mean | wall median | wall stdev | cache_n | VRAM0_peak | VRAM1_peak |
|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| 128 | 3 | 473.287 | 471.288 | 4.786 | 831.1 | 831.5 | 14.0 | [1, 9, 9] | 9468 | 12472 |
| 512 | 3 | 520.416 | 520.627 | 0.797 | 1511.2 | 1514.7 | 16.2 | [6, 9, 9] | 9468 | 12472 |
| 2048 | 3 | 574.083 | 573.475 | 1.405 | 4157.8 | 4191.1 | 78.4 | [6, 10, 10] | 9468 | 12472 |

#### PP 確定値（cache_n==0 優先。不可なら最小 cache_n）

- **PP 128**: method=`no cache_n==0; first rep fallback` zero_count=`0` rep=`1` attempt=`1` usage_pt=`378` prompt_n=`377` cache_n=`1` wall_ms=`844.8` tps=`469.825` prompt_ms=`802.426` prompt_per_second=`469.8252549144719` VRAM0_max=`9468` VRAM1_max=`12472` n_smi=`12`
- **PP 512**: method=`no cache_n==0; first rep fallback` zero_count=`0` rep=`1` attempt=`1` usage_pt=`762` prompt_n=`756` cache_n=`6` wall_ms=`1493.5` tps=`521.087` prompt_ms=`1450.813` prompt_per_second=`521.0871421747669` VRAM0_max=`9468` VRAM1_max=`12472` n_smi=`21`
- **PP 2048**: method=`no cache_n==0; first rep fallback` zero_count=`0` rep=`1` attempt=`1` usage_pt=`2301` prompt_n=`2295` cache_n=`6` wall_ms=`4068.2` tps=`575.69` prompt_ms=`3986.518` prompt_per_second=`575.6903643731196` VRAM0_max=`9468` VRAM1_max=`12472` n_smi=`56`

### TG 生値（再測定・各 repeat）

| target | rep | tg_actual | prompt_n | cache_n | wall_ms | tps | predicted_ms | predicted_per_second | VRAM0_max | VRAM1_max | n_smi |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 32 | 1 | 32 | 312 | 3 | 1548.1 | 51.513 | 601.79 | 51.512986257664636 | 9468 | 12472 | 20 |
| 32 | 2 | 32 | 303 | 10 | 1314.6 | 54.003 | 574.045 | 54.00273497722304 | 9468 | 12472 | 18 |
| 32 | 3 | 32 | 303 | 10 | 1317.0 | 53.455 | 579.929 | 53.45481946927986 | 9468 | 12472 | 17 |
| 128 | 1 | 128 | 306 | 7 | 3088.5 | 54.039 | 2350.133 | 54.03949478603977 | 9468 | 12472 | 42 |
| 128 | 2 | 128 | 304 | 10 | 3113.9 | 53.857 | 2358.079 | 53.857398331438425 | 9468 | 12472 | 42 |
| 128 | 3 | 128 | 304 | 10 | 3110.4 | 53.842 | 2358.738 | 53.842351291241336 | 9468 | 12472 | 42 |

### TG 要約（再測定）

| target | n | tps mean | tps median | tps stdev | wall mean | wall median | wall stdev | cache_n | tg_actual | VRAM0_peak | VRAM1_peak |
|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|
| 32 | 3 | 52.99 | 53.455 | 1.308 | 1393.2 | 1317.0 | 134.1 | [3, 10, 10] | [32, 32, 32] | 9468 | 12472 |
| 128 | 3 | 53.913 | 53.857 | 0.11 | 3104.3 | 3110.4 | 13.8 | [7, 10, 10] | [128, 128, 128] | 9468 | 12472 |

### VRAM ピーク要約（再測定中）

- PP/TG 全体ピーク: GPU0(RTX3060)=`9468` MiB / GPU1(P100)=`12472` MiB
- after_load: GPU0=`9444` / GPU1=`12380` MiB
- idle（unload後）: GPU0=`43` / GPU1=`6` MiB

- note: PP/TG via /v1/completions; strong unique prefixes; prefer cache_n==0 (up to 5 attempts/rep)
- note: VRAM sampled via nvidia-smi every 50ms during each request (before/during/after)
- note: tps for PP prefers timings.prompt_ms; TG prefers timings.predicted_per_second


## Depth

- d0: pp=532 tg=128 wall_ms=4098.5 pp_tps=511.93718184355123 tg_tps=53.90416857488838 note=calibrated_cpt=5.510_hit_rep1
- d8K: pp=8213 tg=128 wall_ms=22303.6 pp_tps=466.2348445291573 tg_tps=43.70891104238525 note=calibrated_cpt=5.510_hit_rep1
- section wall: 56.378s

## 失敗ケース（Core/Sentinel/API）

- `core` `CORE-ARITHMETIC-001` [CAPABILITY] gold=57 ans='63' note=wrong
- `core` `CORE-ARITHMETIC-002` [CAPABILITY] gold=84 ans='91' note=wrong
- `core` `CORE-ARITHMETIC-003` [CAPABILITY] gold=117 ans='112' note=wrong
- `core` `CORE-ARITHMETIC-004` [CAPABILITY] gold=156 ans='152' note=wrong
- `core` `CORE-MATH_WORD-001` [CAPABILITY] gold=440 ans='415' note=wrong
- `core` `CORE-MATH_WORD-004` [CAPABILITY] gold=343 ans='321' note=wrong
- `core` `CORE-CONSTRAINT-001` [CAPABILITY] gold='ABEDC' ans='B-A-E-C-D' note=wrong
- `core` `CORE-CONSTRAINT-002` [CAPABILITY] gold='EDACB' ans='B-?-?-?-?' note=wrong
- `core` `CORE-CONSTRAINT-003` [CAPABILITY] gold='DCABE' ans='B-A-C-D-E' note=wrong
- `core` `CORE-CONSTRAINT-004` [CAPABILITY] gold='DACEB' ans='B-E-C-A-D' note=wrong
- `core` `CORE-INSTRUCTION-003` [CAPABILITY] gold='ACE' ans='AbCdEf' note=wrong
- `sentinel` `H01` [CAPABILITY] gold=362 ans='5' note=wrong
- `sentinel` `H02` [CAPABILITY] gold='AEBDC' ans='EADC B' note=wrong
- `sentinel` `H03` [CAPABILITY] gold='10:A-C-B-D-E' ans='4:A→B→D→E' note=wrong
- `sentinel` `H04` [CAPABILITY] gold=75 ans='48' note=wrong

## 成果物
- `raw.jsonl` / `summary.json` / `run.log`
- `remeasure_pp_tg_vram.json` / `pp_tg_vram.jsonl`
- 本ファイル `COMPLETE_REPORT.md`

# YLSB v0.3 梅 — 完全レポート — `gemma-4-e4b-it`

- 生成日時(JST): 2026-09-07T00:03:30.899534+09:00
- 試験ID: YLSB-UME / course ume / version 0.3
- Lane: R0（split-mode=layer, Tensor off, MTP off）
- API: `http://100.74.160.53:8080`
- 総壁時計（オリジナル）: **130.004 s**
- 実施: 2026-09-06T23:39:21.644226+09:00 → 2026-09-06T23:41:31.648669+09:00


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
- model path: `/home/eightman/gguf-nvme/gemma-4-e4b-it/gemma-4-E4B-it-Q4_K_M.gguf`
- quant: `Q4_K_M`
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
- model: `0ffb122c8b6921f13cbc34186e052524d0b5803b17f4867b7197a561400b3770`
- fixtures:
  - core_ume_28.jsonl: `7ab11a3c2c785c059e5d2f833ce4fe19c61d76089dc18dcb953dc748ec27c270`
  - sentinel_ume_4.jsonl: `1cea1d13bd71a318eeb49590c6c8c9fcd1b55395e981819fa1f0585d7073beae`
  - api_smoke_10.jsonl: `db7dd19622ff68935f9b6745d9680271f2403f6a261ea5abc6b26ba3feba56f7`
- grader `common/grader_basic.py`: `d235f77af3593d8da8f0e456980aa6cf4fdce3610bb6d4fb71246a05f20fc1cb`
- chat template SHA-256: `603a42db292c25278e9b23d94c7abbe77453f13e26a053c43c5c2f900b4136f7` (len=18566)

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
- Dense/MoE: **Dense+PLE (Effective)**
- total params: **~8B with embeddings / 4.5B effective**
- active params: **4.5B effective**
- quant: **Q4_K_M**
- quant nominal bpw: **4.83**
- bpw estimate (filesize×8/total_params): **5.335**
- bpw estimate (filesize×8/active_params): **9.485** （参考・MoEでは物理bpwではない）
- GGUF size: **4.969 GiB**
- source: Google Gemma 4 model card: E4B = 4.5B effective (8B with embeddings); Dense+PLE not MoE

## 品質スコア

| 区分 | 正答 | format | non-empty | INFRA | INVALID | 壁時計 |
|---|---:|---:|---:|---:|---:|---:|
| core | 17/28 (60.7%) | 28/28 (100.0%) | 28/28 (100.0%) | 0 | 0 | 24.9s |
| sentinel | 0/4 (0.0%) | 4/4 (100.0%) | 4/4 (100.0%) | 0 | 0 | 3.6s |
| api_smoke | 10/10 (100.0%) | 10/10 (100.0%) | 10/10 (100.0%) | 0 | 0 | 8.3s |

## ゲート判定

- ✅ **Smallest Meaningful候補**: Core>=60%(60.7%) format>=80%(100.0%) non-empty=100%(100.0%) INFRA=0(0)
- ❌ **Fastest Useful候補**: Core>=80%(60.7%) format>=90%(100.0%) non-empty=100%(100.0%) INFRA=0(0)
- ❌ **梅・難問全通過**: Sentinel 0/4 INVALID=0 INFRA=0 non-empty=4/4

## Cold load（記述のみ・品質ゲート非混在）

- cold_wall_ms: **8348.6**
- was_loaded_before: False
- note: descriptive_only_not_quality_gate; includes_model_load_if_unloaded

## PP（オリジナル run・各 repeat）

| target | rep | actual | prompt_n | cache_n | wall_ms | tps | prompt_ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 1 | 191 | 190 | 1 | 993.1 | 751.324 | 252.887 |
| 128 | 2 | 190 | 189 | 1 | 842.3 | 857.598 | 220.383 |
| 128 | 3 | 191 | 190 | 1 | 848.0 | 855.96 | 221.973 |
| 512 | 1 | 575 | 574 | 1 | 1394.4 | 1005.136 | 571.067 |
| 512 | 2 | 576 | 575 | 1 | 1237.7 | 1015.157 | 566.415 |
| 512 | 3 | 575 | 574 | 1 | 1224.4 | 1020.938 | 562.228 |
| 2048 | 1 | 2115 | 2114 | 1 | 2862.5 | 1133.134 | 1865.622 |
| 2048 | 2 | 2117 | 2116 | 1 | 2890.2 | 1138.626 | 1858.381 |
| 2048 | 3 | 2115 | 2114 | 1 | 2888.7 | 1140.238 | 1853.999 |

| target | n | tps mean | tps median | tps stdev | wall mean | wall median | wall stdev | cache_n |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 128 | 3 | 821.627 | 855.960 | 60.890 | 894.5 | 848.0 | 85.5 | [1, 1, 1] |
| 512 | 3 | 1013.744 | 1015.157 | 7.995 | 1285.5 | 1237.7 | 94.5 | [1, 1, 1] |
| 2048 | 3 | 1137.333 | 1138.626 | 3.724 | 2880.5 | 2888.7 | 15.6 | [1, 1, 1] |

- section wall: 28.287s
- オリジナル run 中の VRAM: **未計測**（下の再測定節を正とする）

## TG（オリジナル run・各 repeat）

| target | rep | tg_actual | prompt_n | cache_n | wall_ms | tps | predicted_ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 32 | 1 | 32 | 97 | 1 | 1363.8 | 52.052 | 595.557 |
| 32 | 2 | 2 | 97 | 1 | 793.8 | 48.457 | 20.637 |
| 32 | 3 | 32 | 97 | 1 | 1352.5 | 52.136 | 594.597 |
| 128 | 1 | 128 | 98 | 1 | 3197.9 | 52.275 | 2429.442 |
| 128 | 2 | 128 | 98 | 1 | 3209.7 | 52.325 | 2427.125 |
| 128 | 3 | 7 | 98 | 1 | 874.7 | 51.462 | 116.592 |

| target | n | tps mean | tps median | tps stdev | wall mean | wall median | wall stdev | cache_n |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 32 | 3 | 50.882 | 52.052 | 2.100 | 1170.0 | 1352.5 | 325.9 | [1, 1, 1] |
| 128 | 3 | 52.021 | 52.275 | 0.484 | 2427.4 | 3197.9 | 1344.7 | [1, 1, 1] |

- section wall: 14.591s
- オリジナル run 中の VRAM: **未計測**（下の再測定節を正とする）

## PP/TG 再測定 + VRAM

- 再測定日時(JST): `2026-09-07T00:07:56.452367+09:00`
- API: `http://100.74.160.53:8080`
- 方法: strong unique prefix cache-bust / PP は cache_n==0 優先（rep あたり最大5試行）
- VRAM: `nvidia-smi` をリクエスト中 50ms 間隔でサンプリング（before/during/after）
- Flash Attention: server default -fa auto; effective on/off 未解決（ログ/metricsから確定できず）
- load_wall_s: `7.233` / ok=`True`
- VRAM after load: GPU0=`2010` MiB / GPU1=`2484` MiB

### PP 生値（再測定・各 repeat）

| target | rep | attempt | usage_pt | prompt_n | cache_n | wall_ms | tps | prompt_ms | prompt_per_second | VRAM0_max | VRAM1_max | n_smi |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 1 | 1 | 435 | 435 | 0 | 440.8 | 1024.248 | 424.702 | 1024.2475900749232 | 2032 | 2560 | 6 |
| 128 | 2 | 1 | 435 | 435 | 0 | 483.0 | 1028.456 | 422.964 | 1028.4563225239028 | 2032 | 2560 | 7 |
| 128 | 3 | 1 | 434 | 434 | 0 | 479.9 | 1028.251 | 422.076 | 1028.25083634227 | 2032 | 2560 | 7 |
| 512 | 1 | 1 | 812 | 812 | 0 | 818.9 | 1071.356 | 757.918 | 1071.3560042115375 | 2032 | 2560 | 11 |
| 512 | 2 | 1 | 813 | 813 | 0 | 839.3 | 1088.447 | 746.936 | 1088.4466674520977 | 2032 | 2560 | 12 |
| 512 | 3 | 1 | 813 | 813 | 0 | 835.9 | 1089.862 | 745.966 | 1089.8620044345184 | 2032 | 2560 | 12 |
| 2048 | 1 | 1 | 2405 | 2405 | 0 | 2176.4 | 1158.052 | 2076.763 | 1158.0522187654537 | 2032 | 2560 | 30 |
| 2048 | 2 | 1 | 2406 | 2406 | 0 | 2203.2 | 1167.514 | 2060.789 | 1167.5139958530444 | 2032 | 2560 | 31 |
| 2048 | 3 | 1 | 2405 | 2405 | 0 | 2220.2 | 1159.512 | 2074.149 | 1159.5116840689846 | 2032 | 2560 | 31 |

### PP 要約（再測定）

| target | n | tps mean | tps median | tps stdev | wall mean | wall median | wall stdev | cache_n | VRAM0_peak | VRAM1_peak |
|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| 128 | 3 | 1026.985 | 1028.251 | 2.373 | 467.9 | 479.9 | 23.5 | [0, 0, 0] | 2032 | 2560 |
| 512 | 3 | 1083.222 | 1088.447 | 10.3 | 831.4 | 835.9 | 10.9 | [0, 0, 0] | 2032 | 2560 |
| 2048 | 3 | 1161.693 | 1159.512 | 5.094 | 2199.9 | 2203.2 | 22.1 | [0, 0, 0] | 2032 | 2560 |

#### PP 確定値（cache_n==0 優先。不可なら最小 cache_n）

- **PP 128**: method=`cache_n==0 first available` zero_count=`3` rep=`1` attempt=`1` usage_pt=`435` prompt_n=`435` cache_n=`0` wall_ms=`440.8` tps=`1024.248` prompt_ms=`424.702` prompt_per_second=`1024.2475900749232` VRAM0_max=`2032` VRAM1_max=`2560` n_smi=`6`
- **PP 512**: method=`cache_n==0 first available` zero_count=`3` rep=`1` attempt=`1` usage_pt=`812` prompt_n=`812` cache_n=`0` wall_ms=`818.9` tps=`1071.356` prompt_ms=`757.918` prompt_per_second=`1071.3560042115375` VRAM0_max=`2032` VRAM1_max=`2560` n_smi=`11`
- **PP 2048**: method=`cache_n==0 first available` zero_count=`3` rep=`1` attempt=`1` usage_pt=`2405` prompt_n=`2405` cache_n=`0` wall_ms=`2176.4` tps=`1158.052` prompt_ms=`2076.763` prompt_per_second=`1158.0522187654537` VRAM0_max=`2032` VRAM1_max=`2560` n_smi=`30`

### TG 生値（再測定・各 repeat）

| target | rep | tg_actual | prompt_n | cache_n | wall_ms | tps | predicted_ms | predicted_per_second | VRAM0_max | VRAM1_max | n_smi |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 32 | 1 | 32 | 368 | 0 | 1124.2 | 49.703 | 623.704 | 49.703064274078734 | 2032 | 2560 | 15 |
| 32 | 2 | 32 | 368 | 0 | 1017.1 | 51.629 | 600.438 | 51.62897751308211 | 2032 | 2560 | 14 |
| 32 | 3 | 32 | 369 | 0 | 1040.9 | 51.059 | 607.143 | 51.05881151557376 | 2032 | 2560 | 14 |
| 128 | 1 | 128 | 372 | 0 | 2886.4 | 51.683 | 2457.287 | 51.68301464175736 | 2032 | 2560 | 39 |
| 128 | 2 | 128 | 371 | 0 | 2901.2 | 51.544 | 2463.917 | 51.54394405331024 | 2032 | 2560 | 38 |
| 128 | 3 | 128 | 371 | 0 | 2906.8 | 51.371 | 2472.202 | 51.371206721780815 | 2032 | 2560 | 38 |

### TG 要約（再測定）

| target | n | tps mean | tps median | tps stdev | wall mean | wall median | wall stdev | cache_n | tg_actual | VRAM0_peak | VRAM1_peak |
|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|
| 32 | 3 | 50.797 | 51.059 | 0.989 | 1060.7 | 1040.9 | 56.2 | [0, 0, 0] | [32, 32, 32] | 2032 | 2560 |
| 128 | 3 | 51.533 | 51.544 | 0.156 | 2898.1 | 2901.2 | 10.5 | [0, 0, 0] | [128, 128, 128] | 2032 | 2560 |

### VRAM ピーク要約（再測定中）

- PP/TG 全体ピーク: GPU0(RTX3060)=`2032` MiB / GPU1(P100)=`2560` MiB
- after_load: GPU0=`2010` / GPU1=`2484` MiB
- idle（unload後）: GPU0=`43` / GPU1=`6` MiB

- note: PP/TG via /v1/completions; strong unique prefixes; prefer cache_n==0 (up to 5 attempts/rep)
- note: VRAM sampled via nvidia-smi every 50ms during each request (before/during/after)
- note: tps for PP prefers timings.prompt_ms; TG prefers timings.predicted_per_second


## Depth

- d0: pp=539 tg=128 wall_ms=3665.8 pp_tps=967.2031827816259 tg_tps=52.05570862575389 note=calibrated_cpt=5.495_hit_rep1
- d8K: pp=8220 tg=128 wall_ms=11208.8 pp_tps=1129.3521072262045 tg_tps=50.40540631718653 note=calibrated_cpt=5.495_hit_rep1
- section wall: 33.224s

## 失敗ケース（Core/Sentinel/API）

- `core` `CORE-ARITHMETIC-001` [CAPABILITY] gold=57 ans='67' note=wrong
- `core` `CORE-ARITHMETIC-003` [CAPABILITY] gold=117 ans='119' note=wrong
- `core` `CORE-ARITHMETIC-004` [CAPABILITY] gold=156 ans='162' note=wrong
- `core` `CORE-MATH_WORD-001` [CAPABILITY] gold=440 ans='110円' note=wrong
- `core` `CORE-MATH_WORD-002` [CAPABILITY] gold=180 ans='120' note=wrong
- `core` `CORE-MATH_WORD-004` [CAPABILITY] gold=343 ans='378' note=wrong
- `core` `CORE-CONSTRAINT-001` [CAPABILITY] gold='ABEDC' ans='CADEB' note=wrong
- `core` `CORE-CONSTRAINT-002` [CAPABILITY] gold='EDACB' ans='A B C D E' note=wrong
- `core` `CORE-CONSTRAINT-003` [CAPABILITY] gold='DCABE' ans='DABCE' note=wrong
- `core` `CORE-CONSTRAINT-004` [CAPABILITY] gold='DACEB' ans='EDCAB' note=wrong
- `core` `CORE-INSTRUCTION-003` [CAPABILITY] gold='ACE' ans='ACEf' note=wrong
- `sentinel` `H01` [CAPABILITY] gold=362 ans='185' note=wrong
- `sentinel` `H02` [CAPABILITY] gold='AEBDC' ans='D A E B C' note=wrong
- `sentinel` `H03` [CAPABILITY] gold='10:A-C-B-D-E' ans='cost:A→C→B→E' note=wrong
- `sentinel` `H04` [CAPABILITY] gold=75 ans='115' note=wrong

## 成果物
- `raw.jsonl` / `summary.json` / `run.log`
- `remeasure_pp_tg_vram.json` / `pp_tg_vram.jsonl`
- 本ファイル `COMPLETE_REPORT.md`

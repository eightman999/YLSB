# YLSB v0.3 梅 — 完全レポート — `qwen3-4b`

- 生成日時(JST): 2026-09-07T00:03:30.897439+09:00
- 試験ID: YLSB-UME / course ume / version 0.3
- Lane: R0（split-mode=layer, Tensor off, MTP off）
- API: `http://100.74.160.53:8080`
- 総壁時計（オリジナル）: **57.677 s**
- 実施: 2026-09-06T23:28:30.363815+09:00 → 2026-09-06T23:29:28.041300+09:00


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
- model path: `/home/eightman/gguf-nvme/qwen3-4b/qwen3-4b-q4_K_M.gguf`
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
- model: `bbfa887855d5566c22d55c1814cb6e666fa176e74267e0ced32c35207b5d0242`
- fixtures:
  - core_ume_28.jsonl: `7ab11a3c2c785c059e5d2f833ce4fe19c61d76089dc18dcb953dc748ec27c270`
  - sentinel_ume_4.jsonl: `1cea1d13bd71a318eeb49590c6c8c9fcd1b55395e981819fa1f0585d7073beae`
  - api_smoke_10.jsonl: `db7dd19622ff68935f9b6745d9680271f2403f6a261ea5abc6b26ba3feba56f7`
- grader `common/grader_basic.py`: `d235f77af3593d8da8f0e456980aa6cf4fdce3610bb6d4fb71246a05f20fc1cb`
- chat template SHA-256: `c979e0e71a3e21b8f208e6ab120d5cb29327885f29d2a8b18fda67a723798e18` (len=4051)

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
- total params: **4B**
- active params: **4B**
- quant: **Q4_K_M**
- quant nominal bpw: **4.83**
- bpw estimate (filesize×8/total_params): **4.995**
- bpw estimate (filesize×8/active_params): **4.995** （参考・MoEでは物理bpwではない）
- GGUF size: **2.326 GiB**
- source: Qwen3-4B + Q4_K_M (nominal ~4.83 bpw typical for Q4_K_M)

## 品質スコア

| 区分 | 正答 | format | non-empty | INFRA | INVALID | 壁時計 |
|---|---:|---:|---:|---:|---:|---:|
| core | 16/28 (57.1%) | 28/28 (100.0%) | 28/28 (100.0%) | 0 | 0 | 15.6s |
| sentinel | 0/4 (0.0%) | 4/4 (100.0%) | 4/4 (100.0%) | 0 | 0 | 1.0s |
| api_smoke | 10/10 (100.0%) | 10/10 (100.0%) | 10/10 (100.0%) | 0 | 0 | 1.4s |

## ゲート判定

- ❌ **Smallest Meaningful候補**: Core>=60%(57.1%) format>=80%(100.0%) non-empty=100%(100.0%) INFRA=0(0)
- ❌ **Fastest Useful候補**: Core>=80%(57.1%) format>=90%(100.0%) non-empty=100%(100.0%) INFRA=0(0)
- ❌ **梅・難問全通過**: Sentinel 0/4 INVALID=0 INFRA=0 non-empty=4/4

## Cold load（記述のみ・品質ゲート非混在）

- cold_wall_ms: **4071.7**
- was_loaded_before: False
- note: descriptive_only_not_quality_gate; includes_model_load_if_unloaded

## PP（オリジナル run・各 repeat）

| target | rep | actual | prompt_n | cache_n | wall_ms | tps | prompt_ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 1 | 183 | 183 | 0 | 165.7 | 1188.188 | 154.016 |
| 128 | 2 | 182 | 171 | 11 | 168.5 | 1120.841 | 152.564 |
| 128 | 3 | 182 | 171 | 11 | 169.0 | 1119.256 | 152.78 |
| 512 | 1 | 565 | 565 | 0 | 473.1 | 1309.304 | 431.527 |
| 512 | 2 | 568 | 557 | 11 | 484.1 | 1265.955 | 439.984 |
| 512 | 3 | 569 | 558 | 11 | 484.2 | 1268.505 | 439.888 |
| 2048 | 1 | 2104 | 2104 | 0 | 1509.3 | 1544.26 | 1362.465 |
| 2048 | 2 | 2103 | 2091 | 12 | 1545.9 | 1497.747 | 1396.097 |
| 2048 | 3 | 2105 | 2093 | 12 | 1547.6 | 1497.884 | 1397.304 |

| target | n | tps mean | tps median | tps stdev | wall mean | wall median | wall stdev | cache_n |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 128 | 3 | 1142.762 | 1120.841 | 39.348 | 167.7 | 168.5 | 1.8 | [0, 11, 11] |
| 512 | 3 | 1281.255 | 1268.505 | 24.325 | 480.5 | 484.1 | 6.4 | [0, 11, 11] |
| 2048 | 3 | 1513.297 | 1497.884 | 26.815 | 1534.3 | 1545.9 | 21.6 | [0, 12, 12] |

- section wall: 8.611s
- オリジナル run 中の VRAM: **未計測**（下の再測定節を正とする）

## TG（オリジナル run・各 repeat）

| target | rep | tg_actual | prompt_n | cache_n | wall_ms | tps | predicted_ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 32 | 1 | 32 | 99 | 0 | 561.5 | 70.283 | 441.076 |
| 32 | 2 | 32 | 88 | 11 | 565.8 | 69.871 | 443.673 |
| 32 | 3 | 32 | 88 | 11 | 568.5 | 69.834 | 443.911 |
| 128 | 1 | 128 | 93 | 7 | 1938.8 | 70.027 | 1813.586 |
| 128 | 2 | 128 | 88 | 12 | 1944.3 | 70.043 | 1813.168 |
| 128 | 3 | 128 | 88 | 12 | 1962.9 | 70.023 | 1813.684 |

| target | n | tps mean | tps median | tps stdev | wall mean | wall median | wall stdev | cache_n |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 32 | 3 | 69.996 | 69.871 | 0.249 | 565.3 | 565.8 | 3.5 | [0, 11, 11] |
| 128 | 3 | 70.031 | 70.027 | 0.011 | 1948.7 | 1944.3 | 12.6 | [7, 12, 12] |

- section wall: 7.81s
- オリジナル run 中の VRAM: **未計測**（下の再測定節を正とする）

## PP/TG 再測定 + VRAM

- 再測定日時(JST): `2026-09-07T00:07:09.473287+09:00`
- API: `http://100.74.160.53:8080`
- 方法: strong unique prefix cache-bust / PP は cache_n==0 優先（rep あたり最大5試行）
- VRAM: `nvidia-smi` をリクエスト中 50ms 間隔でサンプリング（before/during/after）
- Flash Attention: server default -fa auto; effective on/off 未解決（ログ/metricsから確定できず）
- load_wall_s: `4.073` / ok=`True`
- VRAM after load: GPU0=`3364` MiB / GPU1=`4528` MiB

### PP 生値（再測定・各 repeat）

| target | rep | attempt | usage_pt | prompt_n | cache_n | wall_ms | tps | prompt_ms | prompt_per_second | VRAM0_max | VRAM1_max | n_smi |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 1 | 1 | 439 | 438 | 1 | 344.1 | 1353.08 | 323.706 | 1353.079646345758 | 3370 | 4600 | 5 |
| 128 | 2 | 1 | 439 | 428 | 11 | 422.8 | 1326.7 | 322.605 | 1326.6998341625206 | 3370 | 4600 | 6 |
| 128 | 3 | 1 | 438 | 427 | 11 | 421.4 | 1324.146 | 322.472 | 1324.145972363492 | 3370 | 4600 | 6 |
| 512 | 1 | 1 | 825 | 819 | 6 | 663.9 | 1460.5 | 560.767 | 1460.4996371041802 | 3370 | 4600 | 9 |
| 512 | 2 | 1 | 827 | 816 | 11 | 729.4 | 1469.558 | 555.269 | 1469.5579980153764 | 3370 | 4600 | 10 |
| 512 | 3 | 1 | 826 | 815 | 11 | 723.2 | 1473.132 | 553.243 | 1473.13205951092 | 3370 | 4600 | 10 |
| 2048 | 1 | 1 | 2389 | 2383 | 6 | 1760.1 | 1513.881 | 1574.1 | 1513.8809478432122 | 3370 | 4600 | 24 |
| 2048 | 2 | 1 | 2389 | 2377 | 12 | 1882.1 | 1510.885 | 1573.25 | 1510.8851104401717 | 3370 | 4600 | 26 |
| 2048 | 3 | 1 | 2389 | 2377 | 12 | 1885.2 | 1510.031 | 1574.14 | 1510.0308740010416 | 3370 | 4600 | 26 |

### PP 要約（再測定）

| target | n | tps mean | tps median | tps stdev | wall mean | wall median | wall stdev | cache_n | VRAM0_peak | VRAM1_peak |
|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| 128 | 3 | 1334.642 | 1326.7 | 16.019 | 396.1 | 421.4 | 45.0 | [1, 11, 11] | 3370 | 4600 |
| 512 | 3 | 1467.73 | 1469.558 | 6.511 | 705.5 | 723.2 | 36.2 | [6, 11, 11] | 3370 | 4600 |
| 2048 | 3 | 1511.599 | 1510.885 | 2.022 | 1842.5 | 1882.1 | 71.3 | [6, 12, 12] | 3370 | 4600 |

#### PP 確定値（cache_n==0 優先。不可なら最小 cache_n）

- **PP 128**: method=`no cache_n==0; first rep fallback` zero_count=`0` rep=`1` attempt=`1` usage_pt=`439` prompt_n=`438` cache_n=`1` wall_ms=`344.1` tps=`1353.08` prompt_ms=`323.706` prompt_per_second=`1353.079646345758` VRAM0_max=`3370` VRAM1_max=`4600` n_smi=`5`
- **PP 512**: method=`no cache_n==0; first rep fallback` zero_count=`0` rep=`1` attempt=`1` usage_pt=`825` prompt_n=`819` cache_n=`6` wall_ms=`663.9` tps=`1460.5` prompt_ms=`560.767` prompt_per_second=`1460.4996371041802` VRAM0_max=`3370` VRAM1_max=`4600` n_smi=`9`
- **PP 2048**: method=`no cache_n==0; first rep fallback` zero_count=`0` rep=`1` attempt=`1` usage_pt=`2389` prompt_n=`2383` cache_n=`6` wall_ms=`1760.1` tps=`1513.881` prompt_ms=`1574.1` prompt_per_second=`1513.8809478432122` VRAM0_max=`3370` VRAM1_max=`4600` n_smi=`24`

### TG 生値（再測定・各 repeat）

| target | rep | tg_actual | prompt_n | cache_n | wall_ms | tps | predicted_ms | predicted_per_second | VRAM0_max | VRAM1_max | n_smi |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 32 | 1 | 32 | 368 | 3 | 1031.6 | 68.485 | 452.655 | 68.4848284013211 | 3370 | 4600 | 14 |
| 32 | 2 | 32 | 360 | 11 | 832.2 | 68.306 | 453.838 | 68.3063119439095 | 3370 | 4600 | 11 |
| 32 | 3 | 32 | 360 | 11 | 854.1 | 68.446 | 452.914 | 68.44566518146934 | 3370 | 4600 | 12 |
| 128 | 1 | 128 | 366 | 7 | 2243.1 | 68.002 | 1867.593 | 68.00196830894097 | 3370 | 4600 | 29 |
| 128 | 2 | 128 | 362 | 12 | 2240.7 | 68.754 | 1847.157 | 68.75430729494028 | 3370 | 4600 | 31 |
| 128 | 3 | 128 | 362 | 12 | 2243.2 | 68.673 | 1849.346 | 68.67292545580979 | 3370 | 4600 | 31 |

### TG 要約（再測定）

| target | n | tps mean | tps median | tps stdev | wall mean | wall median | wall stdev | cache_n | tg_actual | VRAM0_peak | VRAM1_peak |
|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|
| 32 | 3 | 68.412 | 68.446 | 0.094 | 906.0 | 854.1 | 109.4 | [3, 11, 11] | [32, 32, 32] | 3370 | 4600 |
| 128 | 3 | 68.476 | 68.673 | 0.413 | 2242.3 | 2243.1 | 1.4 | [7, 12, 12] | [128, 128, 128] | 3370 | 4600 |

### VRAM ピーク要約（再測定中）

- PP/TG 全体ピーク: GPU0(RTX3060)=`3370` MiB / GPU1(P100)=`4600` MiB
- after_load: GPU0=`3364` / GPU1=`4528` MiB
- idle（unload後）: GPU0=`43` / GPU1=`6` MiB

- note: PP/TG via /v1/completions; strong unique prefixes; prefer cache_n==0 (up to 5 attempts/rep)
- note: VRAM sampled via nvidia-smi every 50ms during each request (before/during/after)
- note: tps for PP prefers timings.prompt_ms; TG prefers timings.predicted_per_second


## Depth

- d0: pp=540 tg=128 wall_ms=2306.6 pp_tps=1264.5955401930614 tg_tps=69.09767146287932 note=calibrated_cpt=5.510_hit_rep1
- d8K: pp=8222 tg=128 wall_ms=9341.4 pp_tps=1247.6977457522205 tg_tps=58.41419713365674 note=calibrated_cpt=5.510_hit_rep1
- section wall: 18.284s

## 失敗ケース（Core/Sentinel/API）

- `core` `CORE-ARITHMETIC-001` [CAPABILITY] gold=57 ans='49' note=wrong
- `core` `CORE-ARITHMETIC-002` [CAPABILITY] gold=84 ans='[78]' note=wrong
- `core` `CORE-ARITHMETIC-004` [CAPABILITY] gold=156 ans='141' note=wrong
- `core` `CORE-CONSTRAINT-001` [CAPABILITY] gold='ABEDC' ans='["B", "A", "E", "C", "D"]' note=wrong
- `core` `CORE-CONSTRAINT-002` [CAPABILITY] gold='EDACB' ans='1（' note=wrong
- `core` `CORE-CONSTRAINT-003` [CAPABILITY] gold='DCABE' ans='BEADC' note=wrong
- `core` `CORE-CONSTRAINT-004` [CAPABILITY] gold='DACEB' ans='A-C-D-B-E → DはCの直後 → DはAより後 →' note=wrong
- `core` `CORE-READING-002` [CAPABILITY] gold='Python' ans='["Python"]' note=wrong
- `core` `CORE-COMMON_SENSE-003` [CAPABILITY] gold='A' ans='A:待つ' note=wrong
- `core` `CORE-INSTRUCTION-002` [CAPABILITY] gold={'even': [2, 2], 'count': 2} ans='{"even":[2,19,2],"count":3}' note=wrong
- `core` `CORE-INSTRUCTION-003` [CAPABILITY] gold='ACE' ans='["A", "B", "C", "E", "F"]' note=wrong
- `core` `CORE-INSTRUCTION-004` [CAPABILITY] gold='4,2,6,1,7' ans='[4, 2, 6, 1, 7, 6, 1, 6]' note=wrong
- `sentinel` `H01` [CAPABILITY] gold=362 ans='107' note=wrong
- `sentinel` `H02` [CAPABILITY] gold='AEBDC' ans='["C", "A", "E", "D", "B"]' note=wrong
- `sentinel` `H03` [CAPABILITY] gold='10:A-C-B-D-E' ans='4:A→B→D→E:11' note=wrong
- `sentinel` `H04` [CAPABILITY] gold=75 ans='105' note=wrong

## 成果物
- `raw.jsonl` / `summary.json` / `run.log`
- `remeasure_pp_tg_vram.json` / `pp_tg_vram.jsonl`
- 本ファイル `COMPLETE_REPORT.md`

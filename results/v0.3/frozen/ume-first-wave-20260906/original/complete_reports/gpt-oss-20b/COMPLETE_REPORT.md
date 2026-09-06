# YLSB v0.3 梅 — 完全レポート — `gpt-oss-20b`

- 生成日時(JST): 2026-09-07T00:03:30.906166+09:00
- 試験ID: YLSB-UME / course ume / version 0.3
- Lane: R0（split-mode=layer, Tensor off, MTP off）
- API: `http://100.74.160.53:8080`
- 総壁時計（オリジナル）: **242.276 s**
- 実施: 2026-09-06T23:47:59.364080+09:00 → 2026-09-06T23:52:01.640261+09:00


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
- model path: `/home/eightman/gguf-nvme/gpt-oss-20b/gpt-oss-20b-MXFP4.gguf`
- quant: `MXFP4`
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
- model: `27cd6c432c7672cb812a92f611cf3ba7bbc35928262bb1e1253ff4ee6ae35901`
- fixtures:
  - core_ume_28.jsonl: `7ab11a3c2c785c059e5d2f833ce4fe19c61d76089dc18dcb953dc748ec27c270`
  - sentinel_ume_4.jsonl: `1cea1d13bd71a318eeb49590c6c8c9fcd1b55395e981819fa1f0585d7073beae`
  - api_smoke_10.jsonl: `db7dd19622ff68935f9b6745d9680271f2403f6a261ea5abc6b26ba3feba56f7`
- grader `common/grader_basic.py`: `d235f77af3593d8da8f0e456980aa6cf4fdce3610bb6d4fb71246a05f20fc1cb`
- chat template SHA-256 (**runtime /props**): `b2215de6da8ba369957eece8c5aa18f4af94f6c4d311d85e691373a421d80e89` (len=16616)
- chat template SHA-256 (**GGUF tokenizer.chat_template**): `a4c9919cbbd4acdd51ccffe22da049264b1b73e59055fa58811a99efbd7c8146` (len=16714)
- 注: 二重。実測ランは runtime `/props` を正とする

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
- total params: **20.9B**
- active params: **3.6B**
- quant: **MXFP4**
- quant nominal bpw: **4.25**
- bpw estimate (filesize×8/total_params): **4.633**
- bpw estimate (filesize×8/active_params): **26.836** （参考・MoEでは物理bpwではない）
- GGUF size: **11.278 GiB**
- source: OpenAI gpt-oss model card: 20.9B total / 3.6B active; MoE MXFP4 ~4.25 bpw on MoE weights

## 品質スコア

| 区分 | 正答 | format | non-empty | INFRA | INVALID | 壁時計 |
|---|---:|---:|---:|---:|---:|---:|
| core | 22/28 (78.6%) | 22/28 (78.6%) | 22/28 (78.6%) | 0 | 0 | 84.6s |
| sentinel | 3/4 (75.0%) | 4/4 (100.0%) | 4/4 (100.0%) | 0 | 0 | 30.0s |
| api_smoke | 0/10 (0.0%) | 0/10 (0.0%) | 0/10 (0.0%) | 0 | 0 | 16.1s |

## ゲート判定

- ❌ **Smallest Meaningful候補**: Core>=60%(78.6%) format>=80%(78.6%) non-empty=100%(78.6%) INFRA=0(0)
- ❌ **Fastest Useful候補**: Core>=80%(78.6%) format>=90%(78.6%) non-empty=100%(78.6%) INFRA=0(0)
- ❌ **梅・難問全通過**: Sentinel 3/4 INVALID=0 INFRA=0 non-empty=4/4

## Cold load（記述のみ・品質ゲート非混在）

- cold_wall_ms: **17795.6**
- was_loaded_before: False
- note: descriptive_only_not_quality_gate; includes_model_load_if_unloaded

## PP（オリジナル run・各 repeat）

| target | rep | actual | prompt_n | cache_n | wall_ms | tps | prompt_ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 1 | 165 | 165 | 0 | 1069.2 | 376.242 | 438.547 |
| 128 | 2 | 164 | 164 | 0 | 1052.7 | 374.254 | 438.205 |
| 128 | 3 | 165 | 165 | 0 | 1049.3 | 371.619 | 444.003 |
| 512 | 1 | 548 | 548 | 0 | 1567.0 | 631.689 | 867.515 |
| 512 | 2 | 548 | 548 | 0 | 1549.4 | 640.864 | 855.096 |
| 512 | 3 | 550 | 550 | 0 | 1634.1 | 587.478 | 936.206 |
| 2048 | 1 | 2087 | 2087 | 0 | 3619.0 | 811.528 | 2571.691 |
| 2048 | 2 | 2086 | 2086 | 0 | 3466.9 | 813.737 | 2563.482 |
| 2048 | 3 | 2086 | 2086 | 0 | 3547.8 | 819.927 | 2544.13 |

| target | n | tps mean | tps median | tps stdev | wall mean | wall median | wall stdev | cache_n |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 128 | 3 | 374.038 | 374.254 | 2.319 | 1057.1 | 1052.7 | 10.6 | [0, 0, 0] |
| 512 | 3 | 620.010 | 631.689 | 28.545 | 1583.5 | 1567.0 | 44.7 | [0, 0, 0] |
| 2048 | 3 | 815.064 | 813.737 | 4.354 | 3544.6 | 3547.8 | 76.1 | [0, 0, 0] |

- section wall: 32.847s
- オリジナル run 中の VRAM: **未計測**（下の再測定節を正とする）

## TG（オリジナル run・各 repeat）

| target | rep | tg_actual | prompt_n | cache_n | wall_ms | tps | predicted_ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 32 | 1 | 32 | 86 | 0 | 1403.9 | 76.331 | 406.128 |
| 32 | 2 | 32 | 86 | 0 | 1504.4 | 76.181 | 406.925 |
| 32 | 3 | 32 | 86 | 0 | 1298.7 | 76.58 | 404.806 |
| 128 | 1 | 128 | 86 | 0 | 2658.0 | 76.807 | 1653.504 |
| 128 | 2 | 128 | 86 | 0 | 2630.4 | 76.707 | 1655.645 |
| 128 | 3 | 128 | 86 | 0 | 2801.1 | 76.686 | 1656.101 |

| target | n | tps mean | tps median | tps stdev | wall mean | wall median | wall stdev | cache_n |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 32 | 3 | 76.364 | 76.331 | 0.202 | 1402.3 | 1403.9 | 102.9 | [0, 0, 0] |
| 128 | 3 | 76.733 | 76.707 | 0.065 | 2696.5 | 2658.0 | 91.6 | [0, 0, 0] |

- section wall: 16.042s
- オリジナル run 中の VRAM: **未計測**（下の再測定節を正とする）

## PP/TG 再測定 + VRAM

- 再測定日時(JST): `2026-09-07T00:14:02.448331+09:00`
- API: `http://100.74.160.53:8080`
- 方法: strong unique prefix cache-bust / PP は cache_n==0 優先（rep あたり最大5試行）
- VRAM: `nvidia-smi` をリクエスト中 50ms 間隔でサンプリング（before/during/after）
- Flash Attention: server default -fa auto; effective on/off 未解決（ログ/metricsから確定できず）
- load_wall_s: `14.255` / ok=`True`
- VRAM after load: GPU0=`5940` MiB / GPU1=`7764` MiB

### PP 生値（再測定・各 repeat）

| target | rep | attempt | usage_pt | prompt_n | cache_n | wall_ms | tps | prompt_ms | prompt_per_second | VRAM0_max | VRAM1_max | n_smi |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 1 | 1 | 332 | 331 | 1 | 567.3 | 591.683 | 559.421 | 591.6831867234157 | 5960 | 7806 | 9 |
| 128 | 2 | 1 | 333 | 332 | 1 | 570.5 | 593.996 | 558.926 | 593.9963429863702 | 5960 | 7806 | 8 |
| 128 | 3 | 1 | 334 | 333 | 1 | 569.7 | 595.933 | 558.788 | 595.9326256111441 | 5960 | 7806 | 8 |
| 512 | 1 | 1 | 721 | 720 | 1 | 1104.6 | 658.907 | 1092.719 | 658.9068186789101 | 5960 | 7806 | 16 |
| 512 | 2 | 1 | 723 | 722 | 1 | 1111.0 | 660.929 | 1092.401 | 660.9294572231258 | 5960 | 7806 | 16 |
| 512 | 3 | 1 | 722 | 721 | 1 | 1107.3 | 661.469 | 1089.998 | 661.4691036130341 | 5960 | 7806 | 16 |
| 2048 | 1 | 1 | 2251 | 2250 | 1 | 2718.6 | 834.231 | 2697.096 | 834.2305946840602 | 5960 | 7806 | 38 |
| 2048 | 2 | 1 | 2251 | 2250 | 1 | 2735.3 | 835.287 | 2693.684 | 835.2872868532463 | 5960 | 7806 | 38 |
| 2048 | 3 | 1 | 2251 | 2250 | 1 | 2820.5 | 830.976 | 2707.661 | 830.9755172453272 | 5960 | 7806 | 38 |

### PP 要約（再測定）

| target | n | tps mean | tps median | tps stdev | wall mean | wall median | wall stdev | cache_n | VRAM0_peak | VRAM1_peak |
|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| 128 | 3 | 593.871 | 593.996 | 2.128 | 569.2 | 569.7 | 1.7 | [1, 1, 1] | 5960 | 7806 |
| 512 | 3 | 660.435 | 660.929 | 1.351 | 1107.6 | 1107.3 | 3.2 | [1, 1, 1] | 5960 | 7806 |
| 2048 | 3 | 833.498 | 834.231 | 2.247 | 2758.1 | 2735.3 | 54.7 | [1, 1, 1] | 5960 | 7806 |

#### PP 確定値（cache_n==0 優先。不可なら最小 cache_n）

- **PP 128**: method=`no cache_n==0; first rep fallback` zero_count=`0` rep=`1` attempt=`1` usage_pt=`332` prompt_n=`331` cache_n=`1` wall_ms=`567.3` tps=`591.683` prompt_ms=`559.421` prompt_per_second=`591.6831867234157` VRAM0_max=`5960` VRAM1_max=`7806` n_smi=`9`
- **PP 512**: method=`no cache_n==0; first rep fallback` zero_count=`0` rep=`1` attempt=`1` usage_pt=`721` prompt_n=`720` cache_n=`1` wall_ms=`1104.6` tps=`658.907` prompt_ms=`1092.719` prompt_per_second=`658.9068186789101` VRAM0_max=`5960` VRAM1_max=`7806` n_smi=`16`
- **PP 2048**: method=`no cache_n==0; first rep fallback` zero_count=`0` rep=`1` attempt=`1` usage_pt=`2251` prompt_n=`2250` cache_n=`1` wall_ms=`2718.6` tps=`834.231` prompt_ms=`2697.096` prompt_per_second=`834.2305946840602` VRAM0_max=`5960` VRAM1_max=`7806` n_smi=`38`

### TG 生値（再測定・各 repeat）

| target | rep | tg_actual | prompt_n | cache_n | wall_ms | tps | predicted_ms | predicted_per_second | VRAM0_max | VRAM1_max | n_smi |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 32 | 1 | 32 | 266 | 1 | 963.5 | 74.75 | 414.718 | 74.74958887726117 | 5960 | 7806 | 14 |
| 32 | 2 | 32 | 267 | 1 | 922.6 | 76.884 | 403.204 | 76.88415789525897 | 5960 | 7806 | 13 |
| 32 | 3 | 32 | 267 | 1 | 926.5 | 76.646 | 404.459 | 76.64559324925393 | 5960 | 7806 | 13 |
| 128 | 1 | 128 | 267 | 1 | 2192.2 | 76.033 | 1670.327 | 76.03301628962473 | 5960 | 7806 | 30 |
| 128 | 2 | 128 | 266 | 1 | 2191.5 | 76.209 | 1666.46 | 76.2094499717965 | 5960 | 7806 | 30 |
| 128 | 3 | 117 | 268 | 1 | 2052.9 | 75.856 | 1529.216 | 75.85586339666862 | 5960 | 7806 | 28 |

### TG 要約（再測定）

| target | n | tps mean | tps median | tps stdev | wall mean | wall median | wall stdev | cache_n | tg_actual | VRAM0_peak | VRAM1_peak |
|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|
| 32 | 3 | 76.093 | 76.646 | 1.169 | 937.5 | 926.5 | 22.6 | [1, 1, 1] | [32, 32, 32] | 5960 | 7806 |
| 128 | 3 | 76.033 | 76.033 | 0.177 | 2145.5 | 2191.5 | 80.2 | [1, 1, 1] | [128, 128, 117] | 5960 | 7806 |

### VRAM ピーク要約（再測定中）

- PP/TG 全体ピーク: GPU0(RTX3060)=`5960` MiB / GPU1(P100)=`7806` MiB
- after_load: GPU0=`5940` / GPU1=`7764` MiB
- idle（unload後）: GPU0=`43` / GPU1=`6` MiB

- note: PP/TG via /v1/completions; strong unique prefixes; prefer cache_n==0 (up to 5 attempts/rep)
- note: VRAM sampled via nvidia-smi every 50ms during each request (before/during/after)
- note: tps for PP prefers timings.prompt_ms; TG prefers timings.predicted_per_second


## Depth

- d0: pp=528 tg=128 wall_ms=3240.0 pp_tps=644.7193456098641 tg_tps=76.76754244126829 note=calibrated_cpt=5.510_hit_rep1
- d8K: pp=8210 tg=128 wall_ms=12068.6 pp_tps=916.8891881901098 tg_tps=73.82128622256478 note=calibrated_cpt=5.510_hit_rep1
- section wall: 36.442s

## 失敗ケース（Core/Sentinel/API）

- `core` `CORE-CONSTRAINT-001` [CAPABILITY] gold='ABEDC' ans='' note=empty
- `core` `CORE-CONSTRAINT-002` [CAPABILITY] gold='EDACB' ans='' note=empty
- `core` `CORE-CONSTRAINT-003` [CAPABILITY] gold='DCABE' ans='' note=empty
- `core` `CORE-CONSTRAINT-004` [CAPABILITY] gold='DACEB' ans='' note=empty
- `core` `CORE-READING-002` [CAPABILITY] gold='Python' ans='' note=empty
- `core` `CORE-READING-003` [CAPABILITY] gold='札幌' ans='' note=empty
- `sentinel` `H03` [CAPABILITY] gold='10:A-C-B-D-E' ans='10:A->C->B->D->E' note=wrong
- `api_smoke` `REL-001` [CAPABILITY] gold=111 ans='' note=empty
- `api_smoke` `REL-002` [CAPABILITY] gold=119 ans='' note=empty
- `api_smoke` `REL-003` [CAPABILITY] gold=127 ans='' note=empty
- `api_smoke` `REL-004` [CAPABILITY] gold=135 ans='' note=empty
- `api_smoke` `REL-005` [CAPABILITY] gold=143 ans='' note=empty
- `api_smoke` `REL-006` [CAPABILITY] gold=151 ans='' note=empty
- `api_smoke` `REL-007` [CAPABILITY] gold=159 ans='' note=empty
- `api_smoke` `REL-008` [CAPABILITY] gold=167 ans='' note=empty
- `api_smoke` `REL-009` [CAPABILITY] gold=166 ans='' note=empty
- `api_smoke` `REL-010` [CAPABILITY] gold=174 ans='' note=empty

## 成果物
- `raw.jsonl` / `summary.json` / `run.log`
- `remeasure_pp_tg_vram.json` / `pp_tg_vram.jsonl`
- 本ファイル `COMPLETE_REPORT.md`

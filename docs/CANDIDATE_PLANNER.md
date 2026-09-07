# Candidate Planner v0.2 (v0.4-rc3)

Candidate Plannerはベンチマーク前の推薦器です。S/F/L/D/Xを確定せず、各候補の
`prediction_status: predicted`、runtime互換性、メモリ配置条件、近傍実測を返します。
最終slotは実測observationとpolicy評価で決まります。

## observed registry と candidate catalog

2026-09-07版catalogは、従来の比較用anchorを残し、Qwen3.5（0.8B / 4B / 9B）、Qwen3.6（27B / 35B-A3B）、Qwen3.8（27B / Flash-Next / 2.4T-A95B）を含む19候補を収録しています。各候補の公式出典、取得日、parameter scopeはcatalog内に保持します。Flash-Nextのメモリ推定は補助パラメータを含む180Bを使用し、vision encoderなどの未報告分と量子化artifactの実サイズは未確定として扱います。

`registries/models.json` は v0.3 から継承した観測モデルの正本です。実測の artifact、量子化、
provenance を保持するため、候補を追加する用途には使いません。ベンチマーク前に探索できる
モデルは `registries/candidate_models.json` に置き、`registries/candidate-model-catalog.schema.json`
で検証します。catalog の各レコードは `registry_kind: candidate`、`observed: false`、
`prediction_status: predicted` を持ち、公式モデルカードの URL と取得日、reported/estimated/unknown
の区別を保持します。catalog の推定 bpw は、公式カードが BF16 しか報告していない場合の
planner 用の見積もりであり、実 artifact の量子化事実ではありません。

```python
from ylsb_v04.planner import CandidatePlanner, load_candidate_catalog

catalog = load_candidate_catalog("registries/candidate_models.json")
plan = CandidatePlanner(hardware, catalog, runtimes, corpus=corpus).plan()
```

観測として扱うのは normalized corpus に実行結果が import された後だけです。catalog の
予測レコードは近傍 observation retrieval に混入せず、S/F/L/D/X の最終判定にもなりません。

## 入力とAPI

```python
from ylsb_v04.planner import CandidatePlanner, load_normalized_corpus

corpus = load_normalized_corpus("results/v0.3/normalized")
plan = CandidatePlanner(
    hardware={
        "driver": "580.173.02",
        "gpu_groups": [{
            "canonical_id": "gpu.nvidia.rtx3060", "count": 1,
            "vram_gib_each": 12, "architecture": "Ampere",
            "compute_capability": 8.6,
        }],
        "ram": {"total_gib": 30.56},
    },
    models=[{
        "canonical_id": "model.example.35b", "format": "GGUF",
        "artifact_bytes": 22_000_000_000,
        "architecture": {"type": "dense", "total_params_b": 35,
                         "active_params_b": 35},
    }],
    runtimes=[{
        "canonical_id": "runtime.llama-cpp", "name": "llama.cpp",
        "supported_formats": ["GGUF"], "architectures": ["Ampere"],
    }],
    corpus=corpus,
).plan()
```

`NormalizedCorpusAdapter`（`load_normalized_corpus`/`join_normalized_corpus`の内部）は、normalizedの
`runs.jsonl`、`models.jsonl`、`hardware.jsonl`、`machines.jsonl`、
`runtimes.jsonl`、`performance.jsonl`をIDでjoinします。返す近傍はperformanceを
伴うobserved rowで、model/runtime/hardwareと値ごとのprovenanceを含みます。
`v0.3_verdicts.jsonl`や`gates`、`policy_version`は読み込まず、verdictを教師labelに
しません。既存の凍結ファイルは読み取り専用です。
近傍だけを取得する場合は `retrieve_nearest_observations(corpus, hardware, model,
runtime)` を使えます。

CLI統合時は、planner入力に `--hardware`、`--models`、`--runtimes`、任意の
`--corpus`（normalized directoryまたはJSONL）を渡し、出力を `plan` JSONとして
保存します。`tools/ylsb.py`側では既定で `load_candidate_catalog()` も結合し、
`CandidatePlanner(..., corpus=..., candidate_catalog=...)` と
`next_benchmark_candidate(plan, observed)` を呼び出します。

## 出力の読み方

`anchor` はその hardware profile で score が最も高い比較候補、`envelope` はruntimeがrejectして
いない候補を hardware-aware score 順に並べた探索範囲です。`ranking` は同じ順位を全件返し、
`meaningful_window` は
`lower_bound`、`practical_lower_bound`、`sweet_spot`、`practical_upper_bound`、
`capacity_frontier`を持ち、すべて予測値として返ります。runtimeが全てrejectした
modelは通常候補・envelope・S/F/L/D/Xから除外し、`candidates`内にreject理由と
provenanceを残します。

`next_benchmark_candidate(plan, observed)` は観測結果に応じて境界を更新します。
successだけなら観測最大値より一段大きい候補、OOMだけならOOMより一段小さい候補、
両方あればその間の候補を選びます。例えば `35 easy / 110 barely / 235 OOM`
では、未観測の `70 practical` を選ぶカタログを想定できます。予測でfits=Falseの
frontierも、runtime互換性があれば探索対象です。

## hardware-aware score

各候補には `score` と `score_breakdown` を返します。内訳は memory headroom、total parameter
footprint、active compute pressure、compute capability、memory bandwidth、GPU count、
topology、runtime compatibility、historical evidence、benchmark cost、architecture prior です。
GPU 機種名による絶対ルールは使わず、報告された hardware facts から profile を作ります。
古い compute generation で aggregate VRAM が大きい場合は、total footprint が収まって active
parameters が小さい MoE に prior が付きます。単一 GPU で収まる Dense は daily-use prior を
持ち、異種 GPU 構成は topology penalty と low confidence を明示します。未知の値は neutral
component と low confidence に留め、v0.3 の gate label から補完しません。

P100 x13、V100 32 GiB x1、RTX 3060 12 GiB + P100 16 GiB の synthetic profile は、同一 catalog
でも score/order、topology component、候補説明が変わります。これは実測性能の保証ではなく、
次に測る候補を選ぶための deterministic heuristic です。

## fitとruntimeの制約

既知のartifact bytesをweight footprintに使い、未報告値を補完しません。KV cache、
workspace、safety marginは明示的なheuristicです。MoEはtotal parametersをmemory
pressure、active parametersをcompute pressureとして別々に返します。

複数GPUではaggregate VRAMだけでfitを断定せず、`per_device_fit`、`layer_split_fit`、
`allocation`、CPU offload条件を分けます。`fits`は観測結果ではありません。

runtimeはGPU groupを一つずつ検査します。GPU identity/compute capability不明、
architecture不一致、driver不適合、specification上のCC不足を個別に評価します。
ただし、GPU identityやdriverが未報告という未確認状態は既知の非対応とは分け、
`compatibility: unknown`、`validation_status: needs_validation`、low confidenceの
experimental候補として理由を残します。既知のarchitecture/CC/format非対応だけを
high confidenceのrejectとします。
vLLMはCC 7.5以上、OllamaはCC 5.0以上（CC 5.0--6.2はdriver 570以上）のregistry
条件をprovenance付きで保持します。vLLMのGGUFはregistry上experimentalとして扱い、
旧来の「safetensorsのみ」という誤った断定をしません。

## 限界

Plannerは少数のhistorical observationを近傍証拠として使うだけで、性能やS/F/L/D/Xを
学習・断定しません。GPU topology、layer splitの実装、CPU offload、runtime version、
context長、chat templateなどは実測に依存します。runtime registryのcompatibilityは
対象versionの実行で再確認してください。

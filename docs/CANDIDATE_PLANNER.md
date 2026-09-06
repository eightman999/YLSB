# Candidate Planner v0.1

Candidate Plannerはベンチマーク前の推薦器です。S/F/L/D/Xを確定せず、各候補の
`prediction_status: predicted`、runtime互換性、メモリ配置条件、近傍実測を返します。
最終slotは実測observationとpolicy評価で決まります。

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
保存します。`tools/ylsb.py`側では `CandidatePlanner(..., corpus=...)` と
`next_benchmark_candidate(plan, observed)` を呼び出します。

## 出力の読み方

`anchor` は比較可能なサイズ（現在は35B近傍）、`envelope` はruntimeがrejectして
いない候補をサイズ順に並べた実用範囲探索です。`meaningful_window` は
`lower_bound`、`practical_lower_bound`、`sweet_spot`、`practical_upper_bound`、
`capacity_frontier`を持ち、すべて予測値として返ります。runtimeが全てrejectした
modelは通常候補・envelope・S/F/L/D/Xから除外し、`candidates`内にreject理由と
provenanceを残します。

`next_benchmark_candidate(plan, observed)` は観測結果に応じて境界を更新します。
successだけなら観測最大値より一段大きい候補、OOMだけならOOMより一段小さい候補、
両方あればその間の候補を選びます。例えば `35 easy / 110 barely / 235 OOM`
では、未観測の `70 practical` を選ぶカタログを想定できます。予測でfits=Falseの
frontierも、runtime互換性があれば探索対象です。

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

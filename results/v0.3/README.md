# YLSB v0.3 result corpus

`frozen/ume-first-wave-20260906/original/` は、受領ZIPを展開したまま保持するFrozen Baselineです。修正・再採点・正規化で上書きしません。`manifest.json` が元ZIPと全56ファイルのSHA-256を固定します。

`normalized/` は `normalized-corpus-v0.1` の機械可読データです。観測値と再利用区分を保持しますが、v0.3 gate判定は混ぜません。判定と分析は `derived/` にあります。

## 構成

- `normalized/submissions.jsonl`: 6つの論理submission
- `normalized/machines.jsonl`: machine構成
- `normalized/hardware.jsonl`: 第一陣に現れたGPUのcanonicalization layer
- `normalized/models.jsonl`: model/quant/artifact metadata
- `normalized/runtimes.jsonl`: runtime identityと完全commit
- `normalized/runs.jsonl`: config、artifact hash、必須項目準拠状況
- `normalized/task_results.jsonl`: 1問1recordのraw回答・採点・監査・再利用区分
- `normalized/performance.jsonl`: repeat単位のPP/TG/depth/cold-load。originalとpost-hocを分離
- `derived/v0.3_verdicts.jsonl`: `policy_version=YLSB-v0.3` の歴史的判定
- `derived/calibration_report.md`: fixture、difficulty、gate、protocol監査
- `derived/corpus_health.md`: inventory、必須field coverage、既知問題
- `derived/candidate_planner_usage.json`: Planner用途別の利用条件

## 再生成と検証

```bash
python3 tools/normalized_corpus/build_corpus.py
python3 tools/normalized_corpus/build_corpus.py --check
python3 -m unittest discover -s tests -v
```

生成器はJSON Schemaと参照整合性・provenance・v0.3 verdict同一性を検証し、Frozen Baselineの全ファイルhashを実行前後で比較します。未知値はnullと`unknown` provenanceで保持し、aliasはexact registry ruleだけでcanonical化します。

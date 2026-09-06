# 梅試験 — 2時間コース

最小・最速で「この構成は測る意味があるか」を判定する入口試験。

## v0.4-rc2 の導線

このREADMEと `profile.json`、`tests/` は v0.3 の梅試験仕様を保持する。v0.4-rc2を実行するときは、明示fixture [`../fixtures/v0.4-rc1/`](../fixtures/v0.4-rc1/)、評価policy [`../policies/ylsb-v0.4-rc1.json`](../policies/ylsb-v0.4-rc1.json)、grader v2 [`../common/grader_basic.py`](../common/grader_basic.py)、schema v0.2 [`../schema/normalized-corpus-v0.2.schema.json`](../schema/normalized-corpus-v0.2.schema.json)を指定する。生成物は `python3 tools/regenerate_v04.py` で一括更新する。既存の梅fixtureを暗黙にv0.4へ読み替えない。

## 実行前の必須事項

`../common/run_record.schema.json`に従い、runtime完全commit hash、GPU/RAM、環境version、全runtime設定、model/fixture/grader/chat templateのSHA-256を先に記録する。PP/TGは全repeatのtok/s、VRAM、`timings.cache_n`、raw出力パスと、平均・標準偏差を保存する。欠落したrunは正式結果にしない。

## 試験量
- Core: 28問（7カテゴリ×4、Directのみ）
- Hard Sentinel: 4問
- API smoke: 10件
- PP: 128/512/2048 ×3
- TG: 32/128 ×3
- Depth: d0/d8K
- 必須Lane: R0 非Tensor Reference

## 判定
- Smallest Meaningful候補: Core>=60%、format>=80%、non-empty=100%、INFRA=0
- Fastest Useful候補: Core>=80%、format>=90%、non-empty=100%、INFRA=0
- `梅・難問全通過`: Sentinel 4/4かつINVALID/INFRA=0

## データ
- `tests/core_ume_28.jsonl`
- `tests/sentinel_ume_4.jsonl`
- `tests/api_smoke_10.jsonl`

梅ではAgent、64K、長時間安定性、Tensor/MTPの優劣を断定しない。

## v0.3 — Legacy Inverse Challenge
標準2時間にはLICを入れない。余裕がある場合のみ `LIC-S1` をbonus anchorとして追加できる。bonus結果は梅本体の合否と分ける。

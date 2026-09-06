# 松試験 — 半日×5日コース

研究・公開比較・大規模な構成変更に使う完全試験。

## v0.4-rc2 の導線

このREADMEと `profile.json`、`tests/` は v0.3 の松試験仕様と試験量を保持する。v0.4-rc2の記録は明示fixture [`../fixtures/v0.4-rc1/`](../fixtures/v0.4-rc1/)、評価policy [`../policies/ylsb-v0.4-rc1.json`](../policies/ylsb-v0.4-rc1.json)、grader v2 [`../common/grader_basic.py`](../common/grader_basic.py)、schema v0.2 [`../schema/normalized-corpus-v0.2.schema.json`](../schema/normalized-corpus-v0.2.schema.json)を指定し、`python3 tools/regenerate_v04.py` で派生物を更新する。松のv0.3 fixtureを暗黙にv0.4へ変更しない。

## 実行前の必須事項

`../common/run_record.schema.json`に従い、runtime完全commit hash、GPU/RAM、環境version、全runtime設定、model/fixture/grader/chat templateのSHA-256を先に記録する。PP/TGは全repeatのtok/s、VRAM、`timings.cache_n`、raw出力パスと、平均・標準偏差を保存する。欠落したrunは正式結果にしない。

## Day 1 — Performance topology
PP/TG full sweep、context depth、cold/warm、VRAM/RAM/power。R0を基準にTensor/MTP/FA/KVを1変数ずつ比較。

## Day 2 — Reasoning & language
Core 230問 × Direct/Reasoning-summary = 460応答。Hard Sentinel 12問。JA/EN parity 32件。

## Day 3 — Practical & long context
Coding 15問。Long Context 54件。64Kを主張するときだけoptional 12件を追加し、actual prompt_tokensを必須記録。

## Day 4 — Serving / reliability
60件mixed workloadをconcurrency 1/2/4で実施。p50/p95/p99、empty final、OOM、crash、model switch、fallbackを記録。

## Day 5 — Audit / replication / freeze
全failureをFIXTURE_INVALID / INFRA / CAPABILITY / OUTPUT_BUDGET / PROTOCOLへ再分類。gold/grader修正後の対象ケースを再実行し、raw/frozen/hashを固定。

## データ
- `tests/core_matsu_230.jsonl`
- `tests/sentinel_matsu_12.jsonl`
- `tests/coding_matsu_15.jsonl`
- `tests/long_context_matsu_54.jsonl`
- `tests/long_context_64k_optional_12.jsonl`
- `tests/japanese_parity_32.jsonl`
- `tests/reliability_matsu_60.jsonl`

`松・難問全通過` は12/12。別runでも12/12なら再現達成アラート対象。

## v0.3 — Legacy Inverse Challenge
Day 2で `LIC-S1` / `LIC-C1` を各1回、Day 5で別runによる再現確認とfailure audit。`tool_assisted`を追加する場合は別trackで集計する。

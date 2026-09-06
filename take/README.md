# 竹試験 — 半日コース

日常採用するモデル/GPU/runtime構成を決める標準試験。

## v0.4-rc1 の導線

このREADMEと `profile.json`、`tests/` は v0.3 の竹試験仕様を保持する。v0.4-rc1の再評価は梅の明示fixture [`../fixtures/v0.4-rc1/`](../fixtures/v0.4-rc1/)、versioned policy [`../policies/ylsb-v0.4-rc1.json`](../policies/ylsb-v0.4-rc1.json)、grader v2 [`../common/grader_basic.py`](../common/grader_basic.py)、schema v0.2 [`../schema/normalized-corpus-v0.2.schema.json`](../schema/normalized-corpus-v0.2.schema.json)を入口にする。竹の既存問題をv0.4 fixtureとして自動流用しない。

## 実行前の必須事項

`../common/run_record.schema.json`に従い、runtime完全commit hash、GPU/RAM、環境version、全runtime設定、model/fixture/grader/chat templateのSHA-256を先に記録する。PP/TGは全repeatのtok/s、VRAM、`timings.cache_n`、raw出力パスと、平均・標準偏差を保存する。欠落したrunは正式結果にしない。

## 試験量
- Core: 50問 × Direct/Reasoning-summary = 100応答
- Hard Sentinel: 8問
- Practical coding: 6問
- Long Context: 1K/8K/32K × begin/middle/end = 9ケース
- API mixed: 10件
- PP: 128/512/2048/8192 ×5
- TG: 32/128/512 ×5
- Depth: d0/d4K/d16K/d32K
- R0必須、R1 Tensor/R2 MTPは対応時に代表構成で対照

## 判定
- `竹・難問全通過`: Sentinel 8/8かつINVALID/INFRA=0
- R1/R2は同一モデル・quant・KV・context・batchのR0と対にする
- reasoning-summaryは内部CoTのfaithfulnessとはみなさず、finalとの整合率だけを測る

## データ
- `tests/core_take_50.jsonl`
- `tests/sentinel_take_8.jsonl`
- `tests/product_take_6.jsonl`
- `tests/long_context_take_9.jsonl`
- `tests/api_mixed_take_10.jsonl`

## v0.3 — Legacy Inverse Challenge
- `LIC-S1` と `LIC-C1` を各1回
- 標準trackは `model_only`
- stage score / wall / actual prompt_tokens / output-budget hitを記録
- 正解だけでなく途中到達度を残す

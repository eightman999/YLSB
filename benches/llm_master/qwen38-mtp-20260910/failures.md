# failures — qwen38-mtp-20260910

更新: 2026-09-10T10:24:00+09:00（Phase14）

## SKIP / 限界

- Phase3B vLLM / 1Cat: **SKIP**（未インストール）
- 旧 Phase5「長文 8K/16K/32K も ~32.8 tok/s」主張: **削除**。実態はサーバ ctx のみで実入力 ≤2048
- Phase14 32K 真長文: ctx=32768 で起動・OOM なし・128 tok 生成は成功したが、**input_actual=25841（target 30720）** のため **32K operational と主張しない**
- stock probe acceptance メトリクス名は `llamacpp:spec_decode_num_*`（旧パーサは不一致→Phase14 で後抽出）
- GitHub push: シェルに GH_TOKEN 無しの場合は PUSH_PENDING（親 MCP へ委譲）

## 修正済みバグ

- summary.csv 未クォート `tsplit=1,1` → Phase2 best 誤選（layer_p100heavy）。Phase14 で normalize + csv.writer 修正

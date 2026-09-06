# 梅試験 — 2時間コース

最小・最速で「この構成は測る意味があるか」を判定する入口試験。

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

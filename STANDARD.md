# 闇ネット Local LLM 標準試験要項 v0.3 — 松竹梅版

## 1. コース名

| 格 | 試験ID | 所要 | 用途 |
|---|---|---:|---|
| 梅 | YLSB-UME | 約2時間 | 新GPU・新モデル・新runtimeの足切り |
| 竹 | YLSB-TAKE | 半日 | 日常採用構成の決定 |
| 松 | YLSB-MATSU | 半日×5日 | 研究・公開比較・完全監査 |

**松竹梅はモデルの格付けではなく、試験の深さを表す。**

梅→竹→松は同じCore poolの累積subsetで、途中から上位試験へ進んでも基準点を失わない。
Hard Sentinelも梅4問→竹8問→松12問の累積anchorとする。

## 2. 原則

- PPとTGを分離する。
- `llama-bench` と実API TTFT/E2Eを混ぜない。
- R0 非Tensor Referenceを必須とし、Tensor/MTPは必ずR0との対照にする。
- モデルSHA、quant、template、runtime commit、GPU、split、KV、ctx、batch、seed、max_tokens、cold/warmを記録する。
- 正式記録は `fixture validation -> smoke -> raw -> automatic grader -> semantic audit -> frozen corrected result`。
- `FIXTURE_INVALID / INFRA / CAPABILITY / OUTPUT_BUDGET / PROTOCOL` を分離する。
- HTTP 200だけではPASSにしない。
- Long Contextは設定ctxではなくactual prompt_tokensを記録する。

## 3. 代表モデルスロット

- S: Smallest Meaningful
- F: Fastest Useful
- L: Largest Practical
- D: Daily/Default
- X: Experimental

### Smallest Meaningful暫定ゲート
Core-Mini>=60%、format>=80%、non-empty=100%、INFRA=0、かつHard Sentinel>=1または実用task>=1。

### Fastest Useful暫定ゲート
Core-Mini>=80%、format>=90%、non-empty=100%、INFRA=0を満たした中でR0 `tg128@d0` 最大。

## 4. Lane

### R0 Non-Tensor Reference【必須】
single GPUはsplit-mode none、multi GPUはlayer。MTP/speculative/Tensor splitはoff。

### R1 Tensor Split【対応時】
その他の条件をR0と同じにして比較。

### R2 MTP / Speculative【対応時】
Reference/Tensor × MTP off/on の2×2を可能な範囲で比較。CPU sampling fallback等は明記。

### R3 Runtime/Fork【任意】
upstream llama.cpp / fork / vLLM / Ollama等。weight形式が違う場合は純粋なruntime因果比較としない。

## 5. PP/TG

### 梅
PP=128,512,2048 ×3。TG=32,128 ×3。Depth=d0,d8K。

### 竹
PP=128,512,2048,8192 ×5。TG=32,128,512 ×5。Depth=d0,d4K,d16K,d32K。

### 松
PP=64,128,256,512,1024,2048,4096,8192 ×5。
TG=16,32,64,128,256,512 ×5。
Depth=d0,d4K,d16K,d32K。64K主張時だけd49K/d61K近傍を追加。

## 6. 品質データ

### Core pool
7カテゴリ合計230問:
- arithmetic 30
- math_word 40
- logic 40
- constraint 30
- reading 30
- common_sense 30
- instruction 30

梅は各4問=28問。竹は50問。松は230問。
竹・松はDirectとReasoning-summaryの両モードで測る。

Reasoning-summaryは内部CoTそのもののfaithfulnessを証明するものではない。
観測可能な短い根拠要約とfinalの整合をRFC、checkpoint整合をCPCとして扱う。

## 7. Hard Sentinel

- 梅: H01〜H04
- 竹: H01〜H08
- 松: H01〜H12

全問正解かつINVALID/INFRA=0でコース別アラート。
松12/12を別runでも再現した場合は再現達成。

## 8. Long Context

竹は9ケース、松は54ケース。1K/8K/32K × begin/middle/end。
松のみ64K optional 12ケース。
blueprintのtarget token数は設計値であり、正式評価では各モデル/APIのactual prompt_tokensを保存する。

## 9. 実務・耐久

竹: coding 6問、API mixed 10件。
松: coding 15問、JA/EN parity 32件、reliability mixed 60件をconcurrency 1/2/4。

## 10. ZIP構造

```text
common/
ume/
  README.md
  profile.json
  scrapbox_template.txt
  tests/
take/
  README.md
  profile.json
  scrapbox_template.txt
  tests/
matsu/
  README.md
  profile.json
  scrapbox_template.txt
  tests/
  scripts/
manifest.json
```

各コースは自己完結しており、ScrapBoxテンプレも別ファイル。
## 11. Legacy Inverse Challenge (v0.3)

マイコンREは標準パックから除外し、固定anchorとして2問だけ追加する。

### LIC-S1 — Sequence Algorithm Recovery
`answers_10001.txt` を与え、問題文は「この数列から元のアルゴリズムを導出してください」のみ。1〜10001の観測から生成規則を逆推定する。

採点: algorithm identification 35 / reproducible implementation 30 / observed-range consistency 15 / unseen-input consistency 15 / self-check consistency 5。

### LIC-C1 — Cipher Program Recovery
`message.txt` をそのまま与える。未知変換の同定、plaintext recovery、embedded program extraction、program semantics、self-checkを分離採点する。

採点: transform recovery 25 / plaintext recovery 30 / embedded program extraction 20 / program semantics 15 / self-check consistency 10。

### コース配置
- 梅: 標準では無し。LIC-S1をoptional bonusにできる
- 竹: LIC-S1 + LIC-C1を各1回
- 松: LIC-S1 + LIC-C1 + Day5再現/監査

### Track
標準は `model_only`。ネット検索・外部検索・別LLM・解析用ローカルコード実行なし。ツールを許可する場合は `tool_assisted` として別集計する。

### 固定anchorの注意
公開・共有済み固定問題であるため、将来のcontaminationを否定できない。過去モデルとの縦比較・回帰には使えるが、fresh未知問題性能の単独根拠にはしない。canonical solution / hidden inputsは公開ZIPに含めない。


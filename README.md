# YLSB v0.3 — 闇ネット Local LLM 標準試験「松竹梅」

YLSBは、ローカルLLMのモデル単体ではなく、`model / quant / runtime / GPU / split / MTP / KV / context` を含む**実運用構成全体**を比較するためのベンチマークです。

「最も賢いモデル」を1つ決めるのではなく、次のような実際の構成選定に使います。

- この新しいGPU・モデル・runtimeを詳しく試す価値があるか
- 量子化や高速化によって、品質や安定性を損なっていないか
- このマシンで普段使うなら、どの構成が最適か
- runtime更新や構成変更による回帰がないか
- 結果を研究・公開比較に使えるだけの再現性があるか

## 松竹梅の選び方

松竹梅はモデルの格付けではなく、**試験の深さ**を表します。迷ったら梅から始め、有望な構成だけ竹、松へ進めます。CoreとHard Sentinelは上位コースへ累積するため、段階を上げても比較基準を維持できます。

| コース | 試験ID | 所要 | 主な内容 | 判断できること |
|---|---|---:|---|---|
| [梅](ume/README.md) | YLSB-UME | 約2時間 | 速度、Core 28問、Hard Sentinel 4問、API smoke | 詳しく測る価値があるか |
| [竹](take/README.md) | YLSB-TAKE | 半日 | 梅 + Core 50問、実用Coding、32K長文、API mixed | 日常採用する構成はどれか |
| [松](matsu/README.md) | YLSB-MATSU | 半日×5日 | 竹 + Core 230問、Coding、日英比較、耐久、再現監査 | 研究・公開比較に使えるか |

包含関係は `梅 ⊂ 竹 ⊂ 松` です。

## 何を測るか

| 観点 | 測定内容 |
|---|---|
| 速度 | Prompt Processing（PP）、Token Generation（TG）、TTFT、E2E |
| 品質 | 計算、文章題、論理、制約、読解、常識、指示追従 |
| 難問 | 全コース共通の累積Hard Sentinel |
| 実用性 | Coding、実API、Long Context、日英parity |
| 運用性 | OOM、crash、空回答、fallback、並列実行、model switch |
| 再現性 | 別run再試験、failure audit、raw/frozen result、hash固定 |

速度、品質、実用性、運用性は別の指標です。異なる試験の点数を安易に1つの総合点へ合算しません。

## 比較する構成スロット

- **S — Smallest Meaningful**: 最低限使える中で最小の構成
- **F — Fastest Useful**: 最低限使える中で最速の構成
- **L — Largest Practical**: このマシンで実用できる最大級構成
- **D — Daily / Default**: 普段使う構成
- **X — Experimental**: Tensor Split、MTP、forkなどの実験構成

## 比較Lane

- **R0 Non-Tensor Reference（必須）**: 比較基準。Tensor Split、MTP、speculativeを無効化
- **R1 Tensor Split（対応時）**: R0からTensor Splitだけを変更
- **R2 MTP / Speculative（対応時）**: R0などとon/offを対照
- **R3 Runtime / Fork（任意）**: upstream、fork、vLLM、Ollamaなどを比較

高速化の効果を主張するときは、同じモデル・quant・KV・context・batchのR0と対にし、原則として一度に1変数だけ変更します。

## 重要な測定ルール

- `llama-bench` のPP/TGと、実APIのTTFT/E2Eを混ぜない
- R0 Non-Tensor Referenceを必ず残す
- Long Contextは設定上のctx-sizeではなく、API等が返した`actual prompt_tokens`を記録する
- HTTP 200だけでPASSにせず、応答内容をgraderとsemantic auditで確認する
- `FIXTURE_INVALID / INFRA / CAPABILITY / OUTPUT_BUDGET / PROTOCOL`を分離する
- model SHA、quant、template、runtime commit、GPU、split、KV、ctx、batch、seed、出力上限、cold/warmを記録する
- 正式記録は `fixture validation → smoke → raw → automatic grader → semantic audit → frozen corrected result` の順で作る
- raw resultを残し、修正後の結果で無言上書きしない

完全な規則と測定条件は [`STANDARD.md`](STANDARD.md) を正典とします。

## 始め方

1. [`STANDARD.md`](STANDARD.md) で共通ルールを確認する。
2. 目的に合うコースを選び、そのコースのREADMEと`profile.json`を読む。
3. 実行前にモデルとruntimeの識別情報、ハードウェア、Lane、seedなどを固定する。
4. コースの`tests/*.jsonl`を使用して試験を実行し、1 request = 1 JSONL recordでraw出力と測定値を保存する。
5. 自動採点後、異常ケースを意味監査し、failure classを分けてfrozen resultを作る。
6. 同条件のR0や過去runと比較し、用途別の構成スロットを決める。

このリポジトリは試験仕様、問題データ、記録テンプレート、補助スクリプトを収録した**データパック**です。特定runtime向けの統合runnerは含まないため、使用するruntime/APIに合わせて実行ハーネスを用意してください。基本的な採点補助は [`common/grader_basic.py`](common/grader_basic.py)、Long Context入力の生成補助は各コースの`build_long_context.py`を利用できます。

## ディレクトリ構成

```text
common/                         共通設定、grader、Legacy Inverse Challenge
ume/                            梅コースのprofile、問題、記録テンプレート
take/                           竹コースのprofile、問題、記録テンプレート
matsu/                          松コースのprofile、問題、記録テンプレート、補助script
STANDARD.md                     共通試験要項の正典
STANDARD_scrapbox.txt           Scrapbox掲載用テキスト
manifest.json                   バージョン、件数、SHA-256、配布情報
```

各コースの`profile.json`に試験構成、`tests/`にJSONL問題、`scrapbox_template.txt`に結果記録用テンプレートがあります。全収録ファイルのSHA-256とバイト数は[`manifest.json`](manifest.json)で確認できます。

## Legacy Inverse Challenge

v0.3では、公開済みの固定anchorとして次の2問を収録しています。

- **LIC-S1 — Sequence Algorithm Recovery**: 数列から生成規則を復元
- **LIC-C1 — Cipher Program Recovery**: 未知変換、平文、埋込programを復元

標準trackは`model_only`です。問題解決にネット検索、別LLM、解析コードを使う場合は`tool_assisted`として別集計します。固定公開問題なので、未知問題に対する能力の単独根拠にはできません。詳細は[`common/legacy_inverse_challenge/README.md`](common/legacy_inverse_challenge/README.md)を参照してください。

## Scrapbox要項

- [総合要項 v0.3 — 松竹梅版](https://scrapbox.io/Geek-SpaceBox/闇ネット_Local_LLM_標準試験要項_v0.3_—_松竹梅版)
- [梅試験](https://scrapbox.io/Geek-SpaceBox/闇ネット_Local_LLM_標準試験_—_梅)
- [竹試験](https://scrapbox.io/Geek-SpaceBox/闇ネット_Local_LLM_標準試験_—_竹)
- [松試験](https://scrapbox.io/Geek-SpaceBox/闇ネット_Local_LLM_標準試験_—_松)

## v0.3

Legacy Inverse ChallengeとしてLIC-S1（`answers_10001.txt`）とLIC-C1（`message.txt`）を追加しました。マイコンREは含みません。

# YLSB v0.3 — Your Local LLM 標準試験「松竹梅」

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

明示的に「任意」「optional」「対応時」と記載した試験要素だけが省略可能です。それ以外の測定、記録、検証は必須です。未対応項目は黙って省略せず、`NOT_APPLICABLE`と理由を記録します。

高速化の効果を主張するときは、同じモデル・quant・KV・context・batchのR0と対にし、一度に1変数だけ変更しなければなりません。複数変数を同時に変更したrunは因果比較に使用できません。

## AI・runner向け必須記録契約

以下は**全コース・全runで必須**です。空欄、`unknown`、`記録済み`のような代替表現は不可です。取得不能または非該当なら、値を省略せず理由とともに明示してください。1項目でも欠けるrunは「YLSB準拠の比較可能な正式結果」として扱いません。

| # | 必須項目 | 記録する具体値 |
|---:|---|---|
| 1 | runtime | runtime名・versionと、llama.cpp等の**完全なcommit hash** |
| 2 | GPU | 型番、枚数、1枚あたりのVRAM容量 |
| 3 | RAM | システムRAM容量 |
| 4 | context | runtimeへ指定したctx設定値 |
| 5 | KV cache | K/Vの型・量子化、offloadなど実際の設定 |
| 6 | seed | 実際に使用した整数値 |
| 7 | max tokens | 実際の出力上限値 |
| 8 | batch | batchとubatchの両方 |
| 9 | Flash Attention | on/off |
| 10 | 環境 | OS名・version、kernel、CUDA、driver等のversion |
| 11 | model | 対象model artifactのSHA-256 |
| 12 | fixture | 使用したfixtureのパスとSHA-256 |
| 13 | grader | 使用したgraderのパスとSHA-256 |
| 14 | chat template | 識別子、取得元、SHA-256、thinking無効化の有無と方法 |
| 15 | PP/TG VRAM | PP/TG各repeatのVRAM使用量と集計時のpeak |
| 16 | PP/TG標準偏差 | 各測定点の標準偏差と、標本・母標準偏差のどちらか |
| 17 | repeat生値 | 各repeatのtok/s、repeat番号、対応するraw出力パス |
| 18 | `timings.cache_n` | runtime出力に現れた具体的な整数値 |

既存の比較条件であるmodel quantization、Lane、split、Tensor/MTP、runtimeの全CLI引数、各repeatのcold/warm状態も同じく必須です。

機械可読な必須フィールドは[`common/run_record.schema.json`](common/run_record.schema.json)に定義しています。AIやrunnerは実行前に記録先を用意し、実行後に次を検証してください。

1. 必須フィールドが全て具体値で埋まっている。
2. PP/TGの各summaryに、コース所定回数分のraw sampleが対応している。
3. 標準偏差が対応するrepeat生値から再計算できる。
4. 各sampleにVRAM使用量と`timings.cache_n`がある。
5. model・fixture・grader・chat templateのSHA-256が実際に使用したartifactと一致する。
6. 不足があればPASSや比較結果を確定せず、`PROTOCOL`または適切なfailure classとして扱う。

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
3. [`common/run_record.schema.json`](common/run_record.schema.json)に従って、モデル、runtime、環境、設定、artifact hashの記録先を先に用意する。
4. コースの`tests/*.jsonl`を使用して試験を実行し、1 request = 1 JSONL recordでraw出力と測定値を保存する。PP/TGは各repeatの生値、VRAM、`timings.cache_n`も保存する。
5. 自動採点後、異常ケースを意味監査し、failure classを分けてfrozen resultを作る。
6. 同条件のR0や過去runと比較し、用途別の構成スロットを決める。

このリポジトリは試験仕様、問題データ、記録テンプレート、補助スクリプトを収録した**データパック**です。特定runtime向けの統合runnerは含まないため、使用するruntime/APIに合わせて実行ハーネスを用意してください。基本的な採点補助は [`common/grader_basic.py`](common/grader_basic.py)、Long Context入力の生成補助は各コースの`build_long_context.py`を利用できます。

## 公開結果とnormalized corpus

v0.3 UME第一陣（6モデル）の元レポートと、生の観測値を将来のpolicyで再解釈できる `normalized corpus v0.1` を [`results/v0.3/`](results/v0.3/README.md) に収録しています。

- Frozen Baselineは受領ZIPの全56ファイルを改変せず、ファイル別SHA-256 manifestとともに保持
- 6 submissions、1 machine、6 models、1 runtime、252 quality results、198 performance recordsを正規化
- observed measurement、metadata、v0.3 verdict、将来のregrade/rerun分類を別ファイルへ分離
- 未報告値は推測で補わず、`reported / derived / registry / inferred / unknown` provenanceを記録
- Core constraint fixture、Hard Sentinel、GPT-OSSの空回答、template hash不一致を監査
- Candidate Plannerではraw観測値を条件付き利用し、v0.3 gate labelsを教師ラベルにしない

入口は [`corpus health`](results/v0.3/derived/corpus_health.md) と [`calibration report`](results/v0.3/derived/calibration_report.md) です。生成・schema・semantic validationは [`tools/normalized_corpus/build_corpus.py`](tools/normalized_corpus/build_corpus.py) で再現できます。

## ディレクトリ構成

```text
common/                         共通設定、grader、Legacy Inverse Challenge
  run_record.schema.json        正式runに必要な記録項目のJSON Schema
results/v0.3/                   Frozen Baseline、normalized corpus、派生監査
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

## v0.4-rc2（再生成版）

YLSBを、hardwareに対して意味のあるbenchmark candidateを提案し、その構成を再現可能に比較するframeworkへ拡張します。`ylsb_v04` のversioned policy、v2 grader、異種GPU対応run schema、registry、Candidate Planner、generic importerを利用できます。

v0.3 frozen/raw/normalized/derivedは変更しません。同じ observation を `YLSB-v0.4-rc1` policy で再評価し、現行 planner とともに `results/v0.4-rc1/`へ決定論的に再生成します。thresholdはcalibration用でfinal確定値ではありません。

v0.4-rc2を新規実行する場合のfixture入口は [`fixtures/v0.4-rc1/`](fixtures/v0.4-rc1/) です。既存の`ume/`、`take/`、`matsu/` profileはv0.3のままなので、旧fixtureを暗黙にv0.4へ読み替えません。検証からレポートまでの最小手順は次の通りです。

```sh
python3 -m pip install -r requirements-v04.txt
python3 tools/regenerate_v04.py
python3 tools/regenerate_v04.py --check
```

生成器は normalized corpus、regrade、calibration、planner、schema mirror、manifestを一時treeで作り、出力を一括更新します。manifestには入力・fixture・grader・planner・registryのcontent hashと件数を保存し、生成時刻や変化するHEADは埋め込みません。差分があれば`--check`は非0で終了します。

v0.3 UMEのrawレポートdirectory／ZIPは `python3 tools/ylsb.py import-raw ./submission.zip --dry-run` で検査できます。取り込みと重複検知の手順は [Raw report import](docs/RAW_REPORT_IMPORT.md) を参照してください。

詳細な要求チェックは [`docs/V0.4_PLAN.md`](docs/V0.4_PLAN.md)、移行手順とbaselineは [`docs/V0.4_MIGRATION.md`](docs/V0.4_MIGRATION.md)、生成結果に基づく証拠は [`docs/V0.4_IMPLEMENTATION_REPORT.md`](docs/V0.4_IMPLEMENTATION_REPORT.md)を参照してください。評価policyはrc1のまま、生成engineの版をrc2として記録します。

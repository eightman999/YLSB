# YLSB v0.3 UME 第一陣 calibration report

本書はv0.4仕様の決定ではなく、凍結したv0.3観測値から得た校正材料である。観測値、監査結果、v0.3 policy verdictを分離している。

## 1. 第一陣の概要

- 6 submissions / 6 models / 1 machine / 1 runtime
- quality 252件（Core 168、Hard Sentinel 24、API smoke 60）
- original PP/TG 90件、depth 12件、cold load 6件
- VRAM付きpost-hoc PP/TG 90件。original runとは別phaseであり、代替値として結合しない。

## 2. モデル別v0.3結果

| model | Smallest Meaningful | Fastest Useful | Hard Sentinel | UME Full Clear |
|---|---:|---:|---:|---:|
| gemma-4-e4b-it | True | False | 0/4 | False |
| glm-4.7-flash | True | False | 0/4 | False |
| gpt-oss-20b | False | False | 3/4 | False |
| nemotron-3.5-lightning-30b-a3b | False | False | 0/4 | False |
| qwen3-0.6b | False | False | 0/4 | False |
| qwen3-4b | False | False | 0/4 | False |

## 3. カテゴリ別difficulty

| section | category | attempts | correct | accuracy | models attempted | models zero correct |
|---|---|---:|---:|---:|---:|---:|
| api_smoke | exact | 60 | 43 | 71.7% | 6 | 1 |
| core | arithmetic | 24 | 11 | 45.8% | 6 | 1 |
| core | common_sense | 24 | 20 | 83.3% | 6 | 0 |
| core | constraint | 24 | 0 | 0.0% | 6 | 6 |
| core | instruction | 24 | 14 | 58.3% | 6 | 1 |
| core | logic | 24 | 23 | 95.8% | 6 | 0 |
| core | math_word | 24 | 12 | 50.0% | 6 | 1 |
| core | reading | 24 | 19 | 79.2% | 6 | 0 |
| sentinel | CRT | 6 | 1 | 16.7% | 6 | 5 |
| sentinel | Python Trace | 6 | 1 | 16.7% | 6 | 5 |
| sentinel | Scheduling | 6 | 1 | 16.7% | 6 | 5 |
| sentinel | Shortest Path | 6 | 0 | 0.0% | 6 | 6 |

## 4. task別difficulty

| task | category | correct | success rate | reported failure modes | audit |
|---|---|---:|---:|---|---|
| CORE-ARITHMETIC-001 | arithmetic | 3/6 | 50.0% | CAPABILITY:3 | observed |
| CORE-ARITHMETIC-002 | arithmetic | 3/6 | 50.0% | CAPABILITY:3 | observed |
| CORE-ARITHMETIC-003 | arithmetic | 3/6 | 50.0% | CAPABILITY:3 | observed |
| CORE-ARITHMETIC-004 | arithmetic | 2/6 | 33.3% | CAPABILITY:4 | observed |
| CORE-COMMON_SENSE-001 | common_sense | 5/6 | 83.3% | CAPABILITY:1 | observed |
| CORE-COMMON_SENSE-002 | common_sense | 5/6 | 83.3% | CAPABILITY:1 | observed |
| CORE-COMMON_SENSE-003 | common_sense | 5/6 | 83.3% | CAPABILITY:1 | observed |
| CORE-COMMON_SENSE-004 | common_sense | 5/6 | 83.3% | CAPABILITY:1 | observed |
| CORE-CONSTRAINT-001 | constraint | 0/6 | 0.0% | CAPABILITY:6 | observed |
| CORE-CONSTRAINT-002 | constraint | 0/6 | 0.0% | CAPABILITY:6 | observed |
| CORE-CONSTRAINT-003 | constraint | 0/6 | 0.0% | CAPABILITY:6 | fixture_invalid |
| CORE-CONSTRAINT-004 | constraint | 0/6 | 0.0% | CAPABILITY:6 | observed |
| CORE-INSTRUCTION-001 | instruction | 5/6 | 83.3% | CAPABILITY:1 | observed |
| CORE-INSTRUCTION-002 | instruction | 4/6 | 66.7% | CAPABILITY:2 | observed |
| CORE-INSTRUCTION-003 | instruction | 1/6 | 16.7% | CAPABILITY:5 | observed |
| CORE-INSTRUCTION-004 | instruction | 4/6 | 66.7% | CAPABILITY:2 | observed |
| CORE-LOGIC-001 | logic | 6/6 | 100.0% | - | observed |
| CORE-LOGIC-002 | logic | 6/6 | 100.0% | - | observed |
| CORE-LOGIC-003 | logic | 6/6 | 100.0% | - | observed |
| CORE-LOGIC-004 | logic | 5/6 | 83.3% | CAPABILITY:1 | observed |
| CORE-MATH_WORD-001 | math_word | 2/6 | 33.3% | CAPABILITY:4 | observed |
| CORE-MATH_WORD-002 | math_word | 3/6 | 50.0% | CAPABILITY:3 | observed |
| CORE-MATH_WORD-003 | math_word | 5/6 | 83.3% | CAPABILITY:1 | observed |
| CORE-MATH_WORD-004 | math_word | 2/6 | 33.3% | CAPABILITY:4 | observed |
| CORE-READING-001 | reading | 5/6 | 83.3% | CAPABILITY:1 | observed |
| CORE-READING-002 | reading | 3/6 | 50.0% | CAPABILITY:3 | observed |
| CORE-READING-003 | reading | 5/6 | 83.3% | CAPABILITY:1 | observed |
| CORE-READING-004 | reading | 6/6 | 100.0% | - | observed |
| H01 | CRT | 1/6 | 16.7% | CAPABILITY:5 | observed |
| H02 | Scheduling | 1/6 | 16.7% | CAPABILITY:5 | observed |
| H03 | Shortest Path | 0/6 | 0.0% | CAPABILITY:6 | observed |
| H04 | Python Trace | 1/6 | 16.7% | CAPABILITY:5 | observed |
| REL-001 | exact | 4/6 | 66.7% | CAPABILITY:2 | observed |
| REL-002 | exact | 4/6 | 66.7% | CAPABILITY:2 | observed |
| REL-003 | exact | 5/6 | 83.3% | CAPABILITY:1 | observed |
| REL-004 | exact | 4/6 | 66.7% | CAPABILITY:2 | observed |
| REL-005 | exact | 4/6 | 66.7% | CAPABILITY:2 | observed |
| REL-006 | exact | 4/6 | 66.7% | CAPABILITY:2 | observed |
| REL-007 | exact | 5/6 | 83.3% | CAPABILITY:1 | observed |
| REL-008 | exact | 5/6 | 83.3% | CAPABILITY:1 | observed |
| REL-009 | exact | 4/6 | 66.7% | CAPABILITY:2 | observed |
| REL-010 | exact | 4/6 | 66.7% | CAPABILITY:2 | observed |

## 5. constraint監査

4問をA–Eの全120順列で独立に列挙した。001、002、004はreported goldが一意解と一致した。一方、`CORE-CONSTRAINT-003` の一意解は `DCBAE` で、fixtureのgold `DCABE` と一致しない。このtaskは `invalid / FIXTURE_INVALID` とし、0/6をモデル能力の根拠に使わない。残る3問も0/6だが、rawは非空でgraderは単純exact、列挙上fixtureは妥当である。難度過剰の有力な校正信号だが、第一陣だけから「問題が悪い」とは確定しない。

## 6. Hard Sentinel監査

v0.3採点ではGPT-OSSのみ3/4、他モデルは0/4。GPT-OSSのH03出力 `10:A->C->B->D->E` はreported gold `10:A-C-B-D-E` と意味内容が一致するように見えるが、exact表記差でFAILになっている。rawを再採点可能として保持し、Sentinelは通常合否よりdiscriminator/badgeとして分離する仮説を支持する。0/4 ordinary等の段階名は本データでは決定せず、案としてのみ扱う。

## 7. runtime / protocol問題

GPT-OSSはHTTP/INFRA失敗なしで、Core 6件とAPI smoke 10件が空回答だった（計16件）。同runでCore 22/28とSentinel 3/4を得ているため、単純な能力低下だけでは説明しにくい。GPT-OSSではruntime `/props` とGGUF metadata由来のchat-template hash候補も競合する。空回答は `PROTOCOL / requires_rerun` とし、template・endpoint・出力抽出の対照runが必要である。

## 8. v0.3 gateの問題点

- Core 80%のFastest Usefulは6モデルすべてFAILで、速度による候補選別に到達しない。第一陣は閾値が目的に対して強すぎる仮説Aを支持するが、母集団6件なので確定はしない。
- constraintは1問がfixture invalid、残る3問も0/6で、Core総率を大きく押し下げる。Essential / Practical / Hardへのtier分離という仮説Bを検討する根拠になる。
- Sentinelは通常のCore能力と異なる識別力を持ち、仮説Cのbadge分離に整合する。
- GPT-OSSの空回答群はModel Quality / Runtime Compatibility / Serving Correctness / Performanceを分ける仮説Dを強く支持する。

## 9. v0.4で変更を検討すべき点

1. Fastest Usefulを固定80%だけで閉じず、妥当性確認済みusefulness floorを満たす構成内のTG比較とする。
2. Core taskへdifficulty tierを付け、invalid fixtureをgateから除外する。
3. Hard SentinelはCore合否から独立した観測/badgeにする。
4. protocol/template/serving検査を能力採点の前段に置き、空回答をCAPABILITYへ直結させない。

## 10. 再ベンチが必要な項目

- GPT-OSSの空回答16件はtemplate/source、endpoint、出力抽出を固定して再実行する。
- 全runのeffective seed、Flash Attentionの実効on/off、明示tensor split、original-run PP/TG VRAMが欠けるため、現行必須記録契約に準拠する正式比較には再実行が必要。
- chat-template hash候補の不一致は、実際に適用されたtemplate bytesを保存して解消する。

## 11. 再採点のみで利用可能な項目

- 非空のquality raw outputは新policy/graderで再採点可能。
- `CORE-CONSTRAINT-003` はfixture修正後に再採点できるが、v0.3得点は上書きしない。
- H03を含む表記正規化はsemantic audit付きで再採点可能。
- PP/TG/depthのraw測定は再利用可能。post-hoc VRAMは別phaseとしてのみ利用する。

# YLSB normalized corpus v0.1 — corpus health

## Corpus inventory

- Submissions: 6
- Machines: 1
- GPU configurations: 1（heterogeneous RTX 3060 + Tesla P100）
- CPU configurations: 0（CPU情報は未報告）
- Models: 6（Dense 3 / MoE 3）
- Runtime families: 1（llama.cpp）
- Runs: 6
- Quality records: 252
- Performance records: 198

## Mandatory field coverage

Coverageは6 runを分母とする。`unknown`や曖昧な値を充足扱いにしていない。

| field | covered runs | coverage |
|---|---:|---:|
| runtime_commit | 6/6 | 100.0% |
| gpu_model | 6/6 | 100.0% |
| gpu_count | 6/6 | 100.0% |
| vram | 6/6 | 100.0% |
| ram | 6/6 | 100.0% |
| ctx | 6/6 | 100.0% |
| kv_cache | 6/6 | 100.0% |
| effective_seed | 0/6 | 0.0% |
| max_tokens | 6/6 | 100.0% |
| batch_ubatch | 6/6 | 100.0% |
| flash_attention_boolean | 0/6 | 0.0% |
| environment_versions | 6/6 | 100.0% |
| model_sha256 | 6/6 | 100.0% |
| fixture_sha256 | 6/6 | 100.0% |
| grader_sha256 | 6/6 | 100.0% |
| unambiguous_chat_template_hash | 5/6 | 83.3% |
| original_pp_tg_vram | 0/6 | 0.0% |
| pp_tg_stdev | 6/6 | 100.0% |
| repeat_raw_values | 6/6 | 100.0% |
| timings_cache_n | 6/6 | 100.0% |

## Reuse classification

- reusable_as_is: 198
- regradable: 231
- requires_rerun: 15
- invalid: 6

`CORE-CONSTRAINT-003`に該当する6件はfixture invalidを優先した。GPT-OSSの同taskも空回答だが、二重計上せずinvalidに含めたため、GPT-OSS空回答16件のうちrequires_rerunは15件である。

## Known issues

- `CORE-CONSTRAINT-003` のreported goldが全順列監査の一意解と不一致。
- GPT-OSSにHTTP成功下の空回答が16件あり、runtime/template/protocol要因が未分離。
- original PP/TGにはVRAMサンプルがなく、90件のVRAM測定は別のpost-hoc run。
- effective seedは未記録。server default `-1` は乱数指定であり、実際の整数seedではない。
- Flash Attentionは`auto`で実効on/offが不明。
- GPT-OSSでは`/props`とGGUF metadataのchat-template hash候補が一致せず、実適用templateを一意に確定できない。
- GemmaとGPT-OSSには2つのmodel-card間でtotal/active parameter値の差がある。両候補と出典を保持し、無言で統合しない。
- CPU、ROCm、GPU compute capability等は未報告のためnull/unknownのまま保持。

このため6 runすべて、現行の18項目必須記録契約を満たす正式な比較可能結果ではない。観測値は削除せず、用途ごとの制約を付けて再利用する。

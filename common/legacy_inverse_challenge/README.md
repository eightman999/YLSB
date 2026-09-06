# Legacy Inverse Challenge (LIC)

YLSB v0.3で追加する固定anchor。**マイコンREは含めない。**

## LIC-S1 — Sequence Algorithm Recovery

入力: `answers_10001.txt`

問題文は次の1文だけ。

> この数列から元のアルゴリズムを導出してください

1〜10001の観測から生成規則そのものを逆推定する。次項予測ではなく、program induction / system identificationとして扱う。

採点配分: algorithm identification 35 / reproducible implementation 30 / observed-range consistency 15 / unseen-input consistency 15 / self-check consistency 5。

## LIC-C1 — Cipher Program Recovery

入力: `message.txt`。問題文も同ファイルに含む。

未知変換の同定、意味のある平文の回復、平文中のプログラム抽出、そのプログラムの意味解析までを分離採点する。

採点配分: transform recovery 25 / plaintext recovery 30 / embedded program extraction 20 / program semantics 15 / self-check consistency 10。

## Track

### model_only【標準】
ネット検索・Web検索・別LLM・解析用ローカルコード実行なし。入力ファイルとモデル自身の推論だけで解く。

### tool_assisted【任意】
Python / shell等の解析補助を許可する。`model_only`とは別ランキング。

## 固定anchorとしての注意

この2問は公開・共有済み固定問題なので、将来のモデルが既知解を含む可能性を否定できない。したがって、過去モデルとの縦比較やruntime/quant/GPU変更時の回帰anchorには使うが、fresh未知問題性能の単独根拠にはしない。

公開パックにはcanonical algorithm / plaintext / decoder / hidden inputsを含めない。

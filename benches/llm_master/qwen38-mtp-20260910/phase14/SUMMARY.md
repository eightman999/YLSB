# Phase14 補正まとめ — qwen38-mtp-20260910

生成: 2026-09-10T10:24:00+09:00

## 目的

Phase3a の stock `probe.py` A/B が CSV バグ由来の **layer** 誤選択で走っていたため、**tensor 1,1** で正式再測定。長文 Phase5 を「サーバ ctx のみ・実入力≤2048」と再分類し、実長文を新規測定。

## 正式 probe（上流）

- OFF median-of-sessions: **19.3** tok/s ([19.3, 19.3, 19.3])
- ON n-max=2: **31.0** tok/s ([30.4, 31.4, 31.0])
- Speedup: **1.606x**
- Acceptance (last ON): **0.786** = 1700/2162 draft tokens

## MTP sweep winner

DAILY_RECOMMENDED = **n-max 2** (overall median 30.9; n3=28.5 n4=27.4 pmin060=29.4 pmin075=27.4)

## 真長文

| ctx | input actual | TTFT | decode (server) | 判定 |
|---:|---:|---:|---:|---|
| 8192 | 7168 | 38.64s | 33.72 | PASS |
| 16384 | 15360 | 83.10s | 32.55 | PASS |
| 32768 | 25841 (target 30720) | 143.57s | 31.14 | **32K operational 否** |

詳細は同ディレクトリの raw と `leaderboard.md`。

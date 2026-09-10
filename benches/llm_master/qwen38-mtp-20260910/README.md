# qwen38-mtp-20260910 (llm_master / 3060+P100)

Phase14 補正済み。詳細は `phase14/SUMMARY.md` と `leaderboard.md`。

- 上流公式: stock `probe.py` **tensor 1,1** 19.3 → 31.0 tok/s（1.606x）, acceptance 0.786
- 日常: DAILY_RECOMMENDED = MTP n-max 2 / tensor 1,1
- 旧 layer probe と Phase5「長文~32.8維持」は破棄/再分類

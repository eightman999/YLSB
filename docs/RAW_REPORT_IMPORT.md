# Raw report import

`v03-ume-report` adapts the historical YLSB UME report bundle into normalized
corpus records. It accepts a directory or ZIP containing
`complete_reports/<model>/summary.json`, `model_card.json`, `raw.jsonl`, and
the optional PP/TG remeasurement files. The summaries must identify
`course=ume` and `version=0.3`; a different or mixed layout fails with an
inventory diagnostic instead of guessing a format.

Inspect a bundle without writing output:

```bash
python tools/ylsb.py import-raw ./submission.zip \
  --adapter v03-ume-report --dry-run
```

The inventory reports detected models and runs, raw quality rows, performance
rows, missing files, ambiguous fields, unsupported files, and the detected
adapter. Import through the existing normalized importer with:

```bash
python tools/ylsb.py import-raw ./submission.zip \
  --adapter v03-ume-report \
  --destination results/v0.4-rc1/normalized/imported
```

The adapter keeps the source tree immutable and records SHA-256 plus relative
paths for every source file. Directory and ZIP imports use the same canonical
record fingerprint, so relocation and repeated import are detected as
duplicates. ZIP members are checked for path traversal. Input and output
directories may not overlap.

Raw quality rows become independent `task_result` observations. The original
`raw_content`, `gold`, score, format/non-empty flags, HTTP status, category,
and source line are preserved. The v0.3 `CORE-CONSTRAINT-003` row remains
marked `fixture_version: v0.3` and `FIXTURE_INVALID`; it is never replaced by
the corrected v0.4 fixture. Empty GPT-OSS responses remain `PROTOCOL` with
rerun evidence.

Performance observations retain their phase. Original `raw.jsonl` PP/TG,
depth, and cold-load rows use `measurement_phase: original_run`; the
`pp_tg_vram.jsonl` rows use
`measurement_phase: posthoc_vram_remeasurement`. Post-hoc VRAM is not merged
into the original measurement. Existing gates are emitted separately as
`verdict` records with `policy_version: YLSB-v0.3`.

Missing effective seed, effective Flash Attention, tensor split values, CPU
identity, vendor/canonical registry enrichment, and ambiguous template hashes
remain explicit unknowns with provenance. The adapter does not turn those
unknowns into formal v2 run values and does not use model knowledge to fill
them.

# YLSB run record v2

`schema/run-record-v0.2.schema.json` is the canonical v2 schema. The file
`common/run_record.schema.v2.json` is a generated mirror and must remain byte
identical to the canonical file. The v2 schema extends the v0.3 contract; it
does not make incomplete observations formal benchmark runs.

Every formal record contains a full 40 or 64 character runtime commit hash,
model quantization and SHA-256, artifact hashes, concrete seed, explicit
Flash Attention and tensor split state, KV cache K/V/offload settings, and all
CLI arguments. GPU groups, GPU count and VRAM, system RAM, and environment
provenance are recorded without null placeholders for formal hardware facts.
CPU enrichment fields may be null when the source cannot report them, with
the corresponding provenance.

Each PP/TG sample has a metric, point, depth, repeat number, cold/warm state,
tok/s, VRAM, `timings_cache_n`, and raw output path. Each summary has a mean,
standard deviation and its `sample`/`population` kind, repeat counts, and peak
VRAM. `ylsb_v04.schema.validate_run_record` checks the JSON Schema and then
checks that the values agree with the immutable course profile:

* UME uses PP 128/512/2048 and TG 32/128 at depth 0, plus PP512 and TG128
  at the profile long-context depth 8192, with 3 repeats.
* TAKE uses all profile PP/TG points at depth 0, plus PP512/TG128 at each
  non-zero profile depth, with 5 repeats.
* MATSU follows the same baseline and dedicated long-context points with 5
  repeats.

The semantic helpers are available as
`course_profile(course_id)`, `expected_performance_slots(course_id)`, and
`validate_run_record_semantics(record)`. The latter recomputes every summary
mean, standard deviation, and peak VRAM from its repeat samples. A record with
missing points, duplicate repeat numbers, missing VRAM/cache values, or an
incorrect aggregate is rejected.

Historical v0.3 observations can remain incomplete. Import them through the
normalized corpus migration; their provenance and reuse/compliance metadata
describe the missing formal fields. Do not turn those observations into a v2
formal run by filling values with `null`, `unknown`, or guessed defaults.

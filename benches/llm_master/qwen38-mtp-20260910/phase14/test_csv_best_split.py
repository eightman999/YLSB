#!/usr/bin/env python3
"""Tiny test: DictReader + Phase2 best-split must select tensor 1,1.
Documents old bug: unquoted tsplit=1,1 shifted columns so only layer_p100heavy
kept metric==output_tok_s aligned, causing mis-select.
"""
import csv, statistics, collections, pathlib, sys
root = pathlib.Path(__file__).resolve().parents[1]
rows = list(csv.DictReader(open(root / "summary.csv", newline="")))
by = collections.defaultdict(list)
meta = {}
for r in rows:
    if r.get("phase") == "2" and r.get("metric") == "output_tok_s" and r.get("value"):
        try:
            by[r["tag"]].append(float(r["value"]))
            meta[r["tag"]] = (r.get("split"), r.get("tsplit"))
        except ValueError:
            pass
assert by, "no phase2 rows"
best = max(by.items(), key=lambda kv: statistics.median(kv[1]))
tag = best[0]
med = statistics.median(best[1])
split, tsplit = meta[tag]
print("medians:", {k: round(statistics.median(v), 3) for k, v in by.items()})
print(f"best tag={tag} split={split} tsplit={tsplit} median={med:.3f}")
assert tag.startswith("tensor") and "11" in tag.replace("1125", ""), f"expected tensor_11, got {tag}"
assert split == "tensor" and tsplit.replace(" ", "") in ("1,1", "1.1"), f"bad tsplit {tsplit}"
# Explicit: must NOT be layer_p100heavy
assert tag != "layer_p100heavy"
print("PASS: Phase2 best-split -> tensor 1,1 (old unquoted-tsplit bug would pick layer_p100heavy)")

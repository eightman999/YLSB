#!/usr/bin/env python3
import argparse, json, random
from pathlib import Path

def build(case):
    rng=random.Random(case["filler_seed"])
    target=int(case["target_prompt_tokens"])
    # tokenizer間差があるため「token数」そのものはここでは保証しない。
    # 1レコードを短く保ち、目標token数に近い文字量を生成する。
    n=max(120, int(target*0.52))
    rows=[f"R{i:06d} value={rng.randrange(100000,999999)} tag=T{rng.randrange(10,99)}" for i in range(n)]
    needle=f'{case["needle_key"]}={case["needle_value"]}'
    pos=case["needle_position"]
    if pos=="begin": at=max(2,len(rows)//50)
    elif pos=="middle": at=len(rows)//2
    else: at=max(0,len(rows)-max(2,len(rows)//50))
    rows.insert(at,needle)
    return "\n".join(rows)+"\n\n"+case["prompt_suffix"]+"\n"

ap=argparse.ArgumentParser()
ap.add_argument("jsonl")
ap.add_argument("--out", default="generated_contexts")
args=ap.parse_args()
out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
for line in Path(args.jsonl).read_text(encoding="utf-8").splitlines():
    if not line.strip(): continue
    c=json.loads(line)
    (out/(c["id"]+".txt")).write_text(build(c),encoding="utf-8")
print(f"generated {len(list(out.glob('*.txt')))} contexts in {out}")
print("IMPORTANT: formal result must record actual prompt_tokens returned by the model/API tokenizer.")

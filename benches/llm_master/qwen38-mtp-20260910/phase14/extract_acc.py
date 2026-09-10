import re, pathlib, statistics
d=pathlib.Path("/home/eightman/llm_master/benches/qwen38-mtp-20260910/phase14/probe_tensor11")
accs=[]
for p in sorted(d.glob("metrics_probe_t11_ON_*.txt")):
  t=p.read_text()
  draft=re.search(r"llamacpp:spec_decode_num_draft_tokens_total\s+(\d+\.?\d*)", t)
  acc=re.search(r"llamacpp:spec_decode_num_accepted_tokens_total\s+(\d+\.?\d*)", t)
  drafts=re.search(r"llamacpp:spec_decode_num_drafts_total\s+(\d+\.?\d*)", t)
  if draft and acc:
    d_,a_=float(draft.group(1)), float(acc.group(1))
    r=a_/d_ if d_ else float("nan")
    nd=int(float(drafts.group(1))) if drafts else None
    accs.append((p.name,int(d_),int(a_),r, nd))
    print(p.name, "draft",int(d_),"accepted",int(a_),"ratio",round(r,4),"n_drafts", nd)
if accs:
  n,d_,a_,r,nd=accs[-1]
  ratios=[x[3] for x in accs]
  print("LAST",n,r)
  print("MEDIAN_RATIO", statistics.median(ratios))
  (d/"acceptance.env").write_text(f"DRAFT={d_}\nACCEPTED={a_}\nACCEPTANCE={r}\nN_DRAFTS={nd}\n")
  with open(d/"SUMMARY.txt","a") as f:
    f.write(f"\nacceptance_last={r:.6f} draft={d_} accepted={a_} file={n}\nacceptance_median_ratio={statistics.median(ratios):.6f}\n")
  print("WROTE acceptance.env")
else:
  print("NO_ACCS")

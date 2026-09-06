#!/usr/bin/env python3
import json, math, sys

def grade(case, output):
    g=case["grader"]
    gold=case["gold"]
    s=output.strip()
    if g=="numeric_exact":
        try: return float(s)==float(gold)
        except: return False
    if g in ("exact","choice"):
        return s==str(gold)
    if g=="json_exact":
        try: return json.loads(s)==gold
        except: return False
    raise NotImplementedError(g)

if __name__=="__main__":
    case=json.loads(sys.argv[1])
    print("PASS" if grade(case,sys.stdin.read()) else "FAIL")

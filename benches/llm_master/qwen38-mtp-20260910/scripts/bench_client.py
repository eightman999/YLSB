#!/usr/bin/env python3
"""OpenAI-compatible concurrent bench client for llama-server.
Tool label: custom-openai-compat. Supports --unique-prompts (Phase 2+).
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import string
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests

FILLER = (
    "The quick brown fox jumps over the lazy dog. "
    "Benchmarking language model serving throughput and latency. "
) * 80

FILLER_POOL = [
    "The quick brown fox jumps over the lazy dog. ",
    "Benchmarking language model serving throughput and latency. ",
    "Agent workloads require unique context windows without prefix cache reuse. ",
    "Multi-token prediction can accelerate decode under low concurrency. ",
    "Heterogeneous GPUs use tensor-split ratios to balance compute and memory. ",
    "Long context prefill dominates wall time compared to short prompts. ",
    "Speculative decoding verifies draft tokens against the target model. ",
    "Randomized filler suffixes reduce cross-request KV cache hit rates. ",
]


def percentile(xs: list[float], p: float) -> float:
    if not xs:
        return float("nan")
    ys = sorted(xs)
    if len(ys) == 1:
        return ys[0]
    k = (len(ys) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(ys) - 1)
    if f == c:
        return ys[f]
    return ys[f] + (ys[c] - ys[f]) * (k - f)


def _tokenize(base_url: str, content: str) -> list | None:
    for path in ("/tokenize", "/v1/tokenize"):
        try:
            r = requests.post(
                base_url.rstrip("/") + path,
                json={"content": content},
                timeout=180,
            )
            if r.status_code == 200:
                data = r.json()
                tokens = data.get("tokens") or data.get("token_ids")
                if isinstance(tokens, list) and tokens:
                    return tokens
        except Exception:
            pass
    return None


def _detokenize(base_url: str, ids: list) -> str | None:
    for dpath in ("/detokenize", "/v1/detokenize"):
        try:
            d = requests.post(
                base_url.rstrip("/") + dpath,
                json={"tokens": ids},
                timeout=180,
            )
            if d.status_code == 200:
                dj = d.json()
                text = dj.get("content") or dj.get("text")
                if text:
                    return text
        except Exception:
            pass
    return None


def make_base_prompt(base_url: str, target_tokens: int) -> str:
    """Exact-ish length base prompt via tokenize/detokenize once."""
    text = FILLER
    tokens = _tokenize(base_url, text)
    if tokens:
        grow = text
        for _ in range(16):
            if len(tokens) >= target_tokens:
                break
            grow = grow + FILLER
            tokens = _tokenize(base_url, grow) or tokens
        ids = tokens[:target_tokens]
        out = _detokenize(base_url, ids)
        if out:
            return out
        return grow[: max(16, target_tokens * 4)]
    return (FILLER * 40)[: max(16, target_tokens * 4)]


def uniquify_prompt(base: str, unique_id: int, seed: int, target_tokens: int) -> str:
    """Mutate base so cross-request LCP is near-zero; keep ~same char length."""
    rng = random.Random(seed * 1000003 + unique_id * 9176 + target_tokens)
    nonce = "".join(rng.choice(string.ascii_letters + string.digits) for _ in range(32))
    header = f"[REQ{unique_id}|S{seed}|N{nonce}] Agent task {unique_id}. "
    # shuffle a chunk of filler into the body
    mid = "".join(rng.choice(FILLER_POOL) for _ in range(4))
    body = base
    # replace a slice of body with unique content of similar length
    if len(body) > 200:
        start = 40 + (unique_id * 17) % max(1, len(body) // 4)
        end = min(len(body), start + len(header) + len(mid) + 80)
        repl = header + mid + "".join(rng.choice(string.ascii_lowercase + " ") for _ in range(max(0, end - start - len(header) - len(mid))))
        # keep overall length close
        new = body[:start] + repl[: end - start] + body[end:]
        # trim/pad to original length
        if len(new) > len(body):
            new = new[: len(body)]
        elif len(new) < len(body):
            new = new + body[:(len(body) - len(new))]
        return new
    return header + body


def one_request(
    session: requests.Session,
    url: str,
    model: str,
    prompt: str,
    max_tokens: int,
    stream: bool,
    timeout: float,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": 0.0,
        "stream": stream,
        "ignore_eos": True,
    }
    t0 = time.perf_counter()
    ttft = None
    text_parts: list[str] = []
    usage: dict = {}
    finish_reason = None
    err = None
    try:
        if stream:
            with session.post(url, json=payload, stream=True, timeout=timeout) as r:
                if r.status_code != 200:
                    err = f"HTTP {r.status_code}: {r.text[:300]}"
                else:
                    for line in r.iter_lines(decode_unicode=True):
                        if not line:
                            continue
                        if line.startswith("data: "):
                            data = line[6:].strip()
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                            except json.JSONDecodeError:
                                continue
                            if ttft is None:
                                ttft = time.perf_counter() - t0
                            choices = chunk.get("choices") or []
                            if choices:
                                delta = choices[0].get("text") or (
                                    (choices[0].get("delta") or {}).get("content") or ""
                                )
                                if delta:
                                    text_parts.append(delta)
                                fr = choices[0].get("finish_reason")
                                if fr:
                                    finish_reason = fr
                            if chunk.get("usage"):
                                usage = chunk["usage"]
                            if chunk.get("timings"):
                                usage["_timings"] = chunk["timings"]
        else:
            r = session.post(url, json=payload, timeout=timeout)
            if r.status_code != 200:
                err = f"HTTP {r.status_code}: {r.text[:300]}"
            else:
                body = r.json()
                ttft = None
                choices = body.get("choices") or []
                if choices:
                    text_parts.append(choices[0].get("text") or "")
                    finish_reason = choices[0].get("finish_reason")
                usage = body.get("usage") or {}
                if body.get("timings"):
                    usage["_timings"] = body["timings"]
    except Exception as e:
        err = str(e)
    t1 = time.perf_counter()
    latency = t1 - t0
    prompt_tokens = int(usage.get("prompt_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or 0)
    total_tokens = int(usage.get("total_tokens") or (prompt_tokens + completion_tokens))
    timings = usage.get("_timings") or {}
    tpot = None
    if stream and ttft is not None and completion_tokens > 1:
        tpot = (latency - ttft) / (completion_tokens - 1)
    elif timings.get("predicted_per_token_ms") is not None:
        tpot = float(timings["predicted_per_token_ms"]) / 1000.0
    elif completion_tokens > 0 and latency > 0:
        tpot = latency / completion_tokens
    return {
        "ok": err is None and completion_tokens > 0,
        "error": err,
        "latency_s": latency,
        "ttft_s": ttft,
        "tpot_s": tpot,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "finish_reason": finish_reason,
        "timings": timings,
        "chars": sum(len(x) for x in text_parts),
    }


def run_bench(args: argparse.Namespace) -> dict[str, Any]:
    base = args.base_url.rstrip("/")
    url = base + args.endpoint
    model = args.model

    base_prompt = make_base_prompt(base, args.input_tokens)
    actual_prompt_tokens = None
    try:
        toks = _tokenize(base, base_prompt)
        if toks is not None:
            actual_prompt_tokens = len(toks)
    except Exception:
        pass

    def prompt_for(i: int) -> str:
        if args.unique_prompts:
            return uniquify_prompt(base_prompt, i, args.prompt_seed, args.input_tokens)
        return base_prompt

    session_factory = lambda: requests.Session()
    results: list = []
    lock = threading.Lock()
    counter = {"n": 0}

    def next_prompt() -> str:
        with lock:
            i = counter["n"]
            counter["n"] += 1
            return prompt_for(i)

    def worker(_i: int):
        sess = session_factory()
        res = one_request(
            sess, url, model, next_prompt(), args.output_tokens,
            stream=not args.no_stream, timeout=args.timeout,
        )
        with lock:
            results.append(res)

    for _ in range(args.warmup):
        sess = session_factory()
        one_request(
            sess, url, model, next_prompt(), args.output_tokens,
            stream=not args.no_stream, timeout=args.timeout,
        )

    t_wall0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = [ex.submit(worker, i) for i in range(args.num_prompts)]
        for f in as_completed(futs):
            f.result()
    wall = time.perf_counter() - t_wall0

    ok = [r for r in results if r["ok"]]
    fail = [r for r in results if not r["ok"]]
    out_tokens = sum(r["completion_tokens"] for r in ok)
    tot_tokens = sum(r["total_tokens"] for r in ok)
    lat = [r["latency_s"] for r in ok]
    ttft = [r["ttft_s"] for r in ok if r["ttft_s"] is not None]
    tpot = [r["tpot_s"] for r in ok if r["tpot_s"] is not None]

    summary = {
        "tool": "custom-openai-compat",
        "base_url": base,
        "endpoint": args.endpoint,
        "model": model,
        "concurrency": args.concurrency,
        "num_prompts": args.num_prompts,
        "input_tokens_target": args.input_tokens,
        "input_tokens_actual": actual_prompt_tokens,
        "output_tokens_target": args.output_tokens,
        "warmup": args.warmup,
        "unique_prompts": bool(args.unique_prompts),
        "prompt_seed": args.prompt_seed,
        "wall_time_s": wall,
        "success": len(ok),
        "fail": len(fail),
        "errors": [r["error"] for r in fail[:10]],
        "request_throughput_rps": (len(ok) / wall) if wall > 0 else 0.0,
        "output_tok_s": (out_tokens / wall) if wall > 0 else 0.0,
        "total_tok_s": (tot_tokens / wall) if wall > 0 else 0.0,
        "mean_latency_s": statistics.mean(lat) if lat else None,
        "median_latency_s": statistics.median(lat) if lat else None,
        "p95_latency_s": percentile(lat, 95) if lat else None,
        "mean_ttft_s": statistics.mean(ttft) if ttft else None,
        "median_ttft_s": statistics.median(ttft) if ttft else None,
        "p95_ttft_s": percentile(ttft, 95) if ttft else None,
        "mean_tpot_s": statistics.mean(tpot) if tpot else None,
        "median_tpot_s": statistics.median(tpot) if tpot else None,
        "p95_tpot_s": percentile(tpot, 95) if tpot else None,
        "sum_output_tokens": out_tokens,
        "sum_total_tokens": tot_tokens,
    }
    return {"summary": summary, "per_request": results}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:11311")
    ap.add_argument("--endpoint", default="/v1/completions")
    ap.add_argument("--model", default="qwen3.8-27b-q4_K_M")
    ap.add_argument("--concurrency", type=int, default=1)
    ap.add_argument("--num-prompts", type=int, default=20)
    ap.add_argument("--input-tokens", type=int, default=128)
    ap.add_argument("--output-tokens", type=int, default=128)
    ap.add_argument("--warmup", type=int, default=0)
    ap.add_argument("--timeout", type=float, default=1800)
    ap.add_argument("--no-stream", action="store_true")
    ap.add_argument("--output", required=True)
    ap.add_argument("--meta", default="{}")
    ap.add_argument("--unique-prompts", action="store_true")
    ap.add_argument("--prompt-seed", type=int, default=0)
    args = ap.parse_args()
    out = run_bench(args)
    meta = json.loads(args.meta)
    out["meta"] = meta
    with open(args.output, "w") as f:
        json.dump(out, f, indent=2)
    s = out["summary"]
    print(json.dumps({
        "success": s["success"], "fail": s["fail"],
        "output_tok_s": s["output_tok_s"],
        "request_throughput_rps": s["request_throughput_rps"],
        "mean_ttft_s": s["mean_ttft_s"], "mean_tpot_s": s["mean_tpot_s"],
        "wall_time_s": s["wall_time_s"], "unique_prompts": s["unique_prompts"],
        "input_tokens_actual": s["input_tokens_actual"],
    }))


if __name__ == "__main__":
    main()

# YLSB Operational Positioning Field Note — 2026-09-09

## Distilled positioning

YLSB is strongest when described as a **reproducible standard for measuring how far local LLM workloads can be made practical on cheap, old, unusual, or otherwise constrained hardware**.

Avoid reducing it to “benchmarks on junk GPUs.” The public value is comparability: a new GPU, old accelerator, quantization, runtime, storage path, or unusual configuration can be placed against known reference configurations using a repeatable procedure.

## What the meetup reinforced

A recurring real-world constraint around agentic / local-AI workflows is not only model quality but the cost of keeping compute available: API credits, GPU time, power, storage, and operator time. This makes constrained-hardware measurement materially useful rather than merely nostalgic.

## Preserve a clean boundary

YLSB should remain a benchmark standard, not an autonomous-agent benchmark. Automation may run the suite, collect artifacts, or schedule candidates, but **agent intelligence must not become part of the measured score**.

```text
planner / automation   (optional, outside score)
        ↓
YLSB runner            (specified procedure)
        ↓
hardware + runtime + model
        ↓
raw record + normalized result
```

This keeps results comparable whether launched manually, from CI, or by an agent.

## Runner / artifact implications

For future remote execution, prefer machine-readable run contracts and artifacts:

- exact hardware identity and relevant limits
- runtime / driver / backend versions
- model and quantization identity
- command/config fingerprint
- wall-clock duration
- peak VRAM / RAM where available
- load time and inference metrics required by the relevant YLSB tier
- failure class: unsupported / OOM / timeout / runtime error / completed
- raw log and normalized result

A remote executor should be replaceable without changing the benchmark meaning.

## Resource efficiency is context, not a hidden score

Power, elapsed time, storage load time, and acquisition cost are valuable metadata for “limit hardware” decisions, but they should only become normative score components through an explicit standard revision. Do not silently mix them into an existing tier score.

## Public explanation

Recommended concise framing:

> YLSB (闇ネット Local LLM 標準試験) is a reproducible benchmark for comparing practical local-LLM configurations, including cheap, old, and unusual hardware that mainstream benchmarks often ignore.

A second useful sentence is:

> The point is not to prove obsolete hardware is fast; it is to measure exactly where it is still useful and where it stops being useful.

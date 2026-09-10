# YLSB Astra Commons Tokyo Field Note — 2026-09-10

> Status: non-normative field note. This document records adoption and positioning lessons from the Astra Commons Tokyo meetup. It does not change YLSB scoring, tier definitions, or conformance requirements.

## Distilled positioning

The meetup reinforced a simple explanation of YLSB:

> **YLSB is a reproducible practical test for deciding whether a local LLM configuration is actually usable on a given machine.**

The useful comparison target is not only flagship hardware. Cheap, old, asymmetric, multi-GPU, storage-constrained, or otherwise unusual systems are valuable precisely because mainstream benchmark tables often do not tell an operator what will happen there.

## What worked in the LT

The strongest narrative was:

```text
local LLM configurations are hard to compare
        ↓
model / quant / runtime / VRAM / storage / context all differ
        ↓
raw tok/s alone is not enough
        ↓
run one repeatable procedure
        ↓
record where the configuration is useful and where it fails
```

Explaining the benchmark through a concrete constrained configuration made the motivation easier to understand than leading with the standard itself.

The public value proposition should therefore remain **comparability and practical decision support**, not hardware novelty.

## YLSB is closer to a health check than a leaderboard

A leaderboard answers “which result is highest?”

YLSB should answer questions such as:

- Will this model start on my machine?
- How long does cold load take?
- Is interactive use tolerable?
- Does quality remain sufficient for the intended task?
- Which resource becomes the bottleneck?
- Does a new runtime, quantization, GPU, or storage path materially improve the configuration?
- Where does the configuration stop being practical?

This framing is especially useful for Ume as the fast screening tier.

## Community contribution is now a primary success condition

The LT produced direct interest in running the benchmark on other participants' hardware. That changes the nearest-term KPI.

For the next stage, prioritize:

1. first independent third-party run
2. first third-party pull request containing a normalized result
3. first result on hardware not owned by the maintainer
4. reproducibility of that contributed result

GitHub stars, impressions, or benchmark count are secondary until this loop works reliably.

## Contribution path should be agent-friendly

The intended workflow should remain understandable to a human but simple enough to hand to a coding agent:

```text
read repository instructions
  -> inspect local hardware
  -> select a compatible candidate
  -> run the specified YLSB tier
  -> preserve raw evidence
  -> generate normalized result
  -> validate schema / policy
  -> open a pull request
```

Automation is outside the score. The benchmark meaning must remain identical whether the operator launches it manually or delegates the mechanical work to an agent.

## Metadata matters because heterogeneous hardware is the point

Contributed results should preserve enough environment identity to explain unusual outcomes. At minimum, the relevant record should make it possible to distinguish:

- GPU / accelerator identity and VRAM
- multi-device topology where applicable
- CPU and system RAM where relevant to offload
- runtime / backend
- driver and major software versions
- model and quantization
- context and KV-cache-relevant settings
- storage path for load-time measurements
- command/config fingerprint
- completion or failure class

Do not silently convert new metadata into score components. Normative scoring changes still require a standard revision.

## Failure data is useful data

For constrained hardware, an unsupported or failed configuration is not necessarily a useless submission.

Useful failure classes include:

- unsupported backend / instruction set
- model load failure
- OOM / VRAM exhaustion
- host RAM exhaustion
- timeout / operationally impractical latency
- runtime crash
- completed but below a declared practical threshold

YLSB should make negative results easy to preserve without presenting them as successful conformance runs.

## Cross-project relationship

YLSB can serve as an intelligence-substrate catalog for systems such as Kamimusuhi, but should not become coupled to any one agent architecture.

```text
YLSB: measure the substrate
Kamimusuhi: decide when and how to use intelligence
OISINT: expose real-world product constraints
```

This boundary keeps the standard reusable.

## Immediate product actions suggested by the event

- Keep the “run Ume first” entry path extremely short.
- Make the contribution instructions copyable into an agent session.
- Ensure a contributor can identify exactly which files belong in a PR.
- Preserve raw logs/evidence alongside normalized records where policy allows.
- Make unusual hardware explicitly welcome rather than treating it as an edge case.
- Optimize for receiving one correct external PR before expanding community features.

## Non-goals from this note

- Do not redefine YLSB as an agent benchmark.
- Do not reward unusual hardware merely for being unusual.
- Do not make cost or power a hidden score.
- Do not remove raw evidence in favor of presentation-only leaderboard entries.
- Do not change v0.4 normative requirements through this field note.

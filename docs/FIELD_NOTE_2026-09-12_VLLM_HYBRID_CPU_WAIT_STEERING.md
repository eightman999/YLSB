# YLSB Field Note — vLLM busy-wait placement on heterogeneous CPUs — 2026-09-12

> Status: non-normative field note. This note records an optimization hypothesis and a proposed measurement extension. It does not change YLSB scoring, tier definitions, or conformance requirements.

## Summary

A DGX Spark / GB10 field report showed a useful class of inference optimization that is easy to miss in ordinary tok/s benchmarking:

- vLLM can keep CPU threads runnable while they wait for GPU-side progress.
- On a heterogeneous CPU, those runnable waiters may be scheduled onto high-performance cores.
- Moving or biasing those waiters toward efficiency cores can reduce CPU/SoC temperature without reducing GPU-limited inference throughput.
- The reported GB10 result reduced CPU-cluster temperature by roughly 10–14 °C while an 800-token generation workload showed no measurable slowdown in the limited sample.

The important idea is not “underclock the CPU.” It is **place low-value waiting work on the cheapest suitable cores**.

## Why this matters to YLSB

YLSB is intended to capture practical usability on real, heterogeneous hardware. Two configurations with the same pp/tg throughput can differ materially in:

- CPU package power,
- CPU / SoC temperature,
- fan noise,
- sustained thermal headroom,
- power available to a shared CPU/GPU power domain,
- and long-run stability.

Therefore, CPU-side wait behavior is worth preserving as diagnostic evidence even when it does not change the primary score.

This should remain **metadata / evidence**, not a hidden score component.

## GB10 mechanism observed in the field

DGX Spark uses a 20-core Arm CPU with 10 Cortex-X925 performance cores and 10 Cortex-A725 efficiency cores.

In the observed environment, lowering `scaling_max_freq` on the X925 cores to the A725 maximum did not behave as a simple hardware clock cap. Instead, the useful effect was scheduler steering: Linux treated the capped X925 cores as lower-capacity scheduling targets, and CPU-heavy waiting shifted toward the A725 cores.

The reported scheduler-capacity values were consistent with that explanation: after the requested cap, most X925 cores ranked at or below the A725 cores, and the busy-wait samples moved away from those X925 cores.

This is environment-specific. Do not generalize the statement “`scaling_max_freq` does not cap the hardware clock” to Linux in general. CPUFreq normally defines `scaling_max_freq` as the maximum allowed policy frequency; the GB10 observation should be treated as a platform/driver result that requires direct measurement.

## Why vLLM can burn CPU while GPU-bound

The relevant class of behavior is short-latency polling / spin-waiting around inter-process and device synchronization.

A recent upstream vLLM change proposal, PR #52917, explicitly targets fixed-grace busy loops in `shm_broadcast` and adds:

- adaptive spin grace,
- bounded Arm `WFET` waits,
- bounded Intel `WAITPKG` / `UMONITOR` / `UMWAIT` waits,
- and a writer-side transition from indefinite yielding toward bounded parking.

The PR description specifically discusses GB10 validation and the cost of burning CPU cores in idle or idle-adjacent distributed inference.

This strongly supports treating CPU wait placement as a real serving-runtime concern rather than an incidental thermal anomaly.

## Proposed YLSB experiment: heterogeneous-CPU wait steering

For a GPU-limited inference configuration on a hybrid CPU host, compare three states where available:

1. **Baseline** — default scheduler/runtime behavior.
2. **Affinity steering** — pin only the identified busy-waiting vLLM threads/processes to efficiency cores.
3. **Runtime wait improvement** — test a vLLM build containing the adaptive/bounded wait behavior from upstream work such as #52917.

Do not move all vLLM CPU work to efficiency cores blindly. Tokenization, scheduling, memcpy, networking, preprocessing, and other real CPU work may become the bottleneck.

### Minimum measurements

Keep the normal YLSB inference metrics and add diagnostic evidence:

- prefill throughput (`pp`),
- generation throughput (`tg`),
- end-to-end wall time,
- GPU utilization,
- CPU package / SoC power if available,
- CPU / SoC temperature,
- per-core CPU utilization,
- CPU IDs used by the hottest/runnable vLLM threads,
- relevant affinity / cpufreq settings,
- runtime commit/version and kernel version.

For hybrid x86 systems, also record whether the CPU exposes `WAITPKG`:

```bash
grep -wo waitpkg /proc/cpuinfo | head
```

A simple first-pass view of hot threads is:

```bash
ps -eLo pid,tid,psr,pcpu,comm,args --sort=-pcpu | head -30
```

Affinity experiments can then target only the identified wait-heavy TIDs/processes with `taskset` or an equivalent mechanism.

## Acceptance signal

The interesting result is not necessarily a throughput increase.

A successful steering result can be:

```text
pp / tg unchanged within run-to-run noise
+ GPU utilization unchanged
+ waiting work moves to efficiency cores
+ CPU/SoC power or temperature falls materially
```

That result means the system reached the same inference service level with less CPU-side waste.

Conversely, if throughput or latency regresses, the workload was not purely GPU-limited or the affinity rule captured useful CPU work along with the waiters.

## Controls

To avoid false conclusions:

- take an idle/negative-control sample before each inference run,
- do not use only requested/current cpufreq sysfs values as proof of effective hardware frequency,
- measure the actually busy cores,
- preserve exact CPU masks and runtime configuration,
- repeat runs because thermal state and scheduler placement are noisy,
- and separate “scheduler steering” from “true hardware frequency limiting.”

On GB10 specifically, the field report warns that `cppc_cpufreq` sysfs values may not be sufficient evidence of the real clock reached under load. Prefer an independently supported effective-frequency signal where the platform exposes one.

## Scope and non-goals

- This does not add temperature or power to the YLSB score.
- This does not assume every vLLM build has the same wait behavior.
- This does not claim that all x86 systems benefit; homogeneous CPUs have no equivalent cheap core class to steer toward.
- Hybrid x86 systems such as Intel P-core/E-core designs are candidates, but should prefer targeted affinity or runtime wait fixes over broad frequency caps.
- Results are runtime-, kernel-, topology-, and workload-dependent.

## Sources / follow-up

- Field report / Claude Artifact: https://claude.ai/code/artifact/2a3c9abb-8e0e-4741-a483-3d046f72c677
- vLLM PR #52917 — adaptive spin grace + bounded Arm/x86 waits: https://github.com/vllm-project/vllm/pull/52917
- Linux capacity-aware scheduling documentation: https://docs.kernel.org/6.7/scheduler/sched-capacity.html
- Linux CPUFreq documentation: https://docs.kernel.org/6.17/admin-guide/pm/cpufreq.html
- NVIDIA DGX Spark hardware overview: https://docs.nvidia.com/dgx/dgx-spark/hardware.html

## Recommended next YLSB action

Run a controlled A/B/C test on an available hybrid x86 inference host:

```text
A: default scheduling
B: wait-heavy vLLM thread/process affinity -> E-cores
C: vLLM adaptive/bounded-wait implementation, if buildable
```

Preserve `pp512`, `tg128`, wall time, GPU utilization, CPU package power, temperatures, and per-core placement. If B or C reduces CPU-side thermals/power without harming inference performance, promote the experiment into a reusable optional YLSB diagnostic recipe.

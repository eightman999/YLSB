# hardware_snapshot — llm-machine (master) 2026-09-10

- Host: master
- User: eightman
- OS: Ubuntu 26.04 LTS
- Kernel: 7.0.0-31-generic
- Driver: 580.173.02
- nvidia-smi CUDA reported: 13.0
- nvcc: Build cuda_12.4.r12.4/compiler.34097967_0
- Python: Python 3.14.4
- CPU: 13th Gen Intel(R) Core(TM) i7-13700F
- nproc: 24
- RAM: 30Gi
- GPUs:
index, name, memory.total [MiB]
0, NVIDIA GeForce RTX 3060, 12288 MiB
1, Tesla P100-PCIE-16GB, 16384 MiB
- Topology: PCIe only (PHB between GPU0/GPU1; no NVLink) — see nvidia-smi topo -m
	[4mGPU0	GPU1	CPU Affinity	NUMA Affinity	GPU NUMA ID[0m
GPU0	 X 	PHB	0-23	0		N/A
GPU1	PHB	 X 	0-23	0		N/A

Legend:

  X    = Self
  SYS  = Connection traversing PCIe as well as the SMP interconnect between NUMA nodes (e.g., QPI/UPI)
  NODE = Connection traversing PCIe as well as the interconnect between PCIe Host Bridges within a NUMA node
  PHB  = Connection traversing PCIe as well as a PCIe Host Bridge (typically the CPU)

## llama.cpp
- Path: /home/eightman/dev/tools/llama.cpp
- Commit: 5ea1b124e7dfcdb80d7291be188efc7d0b485d66
- Version string: version: 0.3.0-dev (build 1, commit 5ea1b12) built with GNU 13.4.0 for Linux x86_64 
- Build: Release; CMAKE_CUDA_ARCHITECTURES=60;86 (P100+3060); host g++-13
- Binaries: llama-server, llama-cli present; llama-bench NOT present → server+client

## Model
- Path: /home/eightman/gguf-nvme/qwen3.8-27b-q4_K_M/qwen3.8-27b-q4_K_M.gguf
- Quant: Q4_K_M
- SHA256: f5f1dd8920d417aac2718b0bda3403da274301efdd6760b4f0f4b864ff2ad57d  /home/eightman/gguf-nvme/qwen3.8-27b-q4_K_M/qwen3.8-27b-q4_K_M.gguf
- Size: 16G
- models.ini defaults ctx-size=65536 (bench uses ≤32768; no 64K+ per hard rule)

## Other runtimes
- vLLM: not installed
- 1Cat-vLLM: not installed
- Bench port: 18080 (leave llama-master :8080 alone)
- Date: 2026-09-10T07:28:50+09:00

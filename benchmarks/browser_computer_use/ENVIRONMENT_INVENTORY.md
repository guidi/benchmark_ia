# Environment Inventory

Last updated: 2026-08-09

## Scope

This document records the actual hardware and software environment of
the machine that will run the benchmark.

It is the Phase 1 artifact referenced by the benchmark plan.

## Machine

- Manufacturer: Avell
- Model: A65 ION
- Operating system: Windows 11 Pro
- OS version: 10.0.26200
- Build number: 26200
- Architecture: 64-bit
- Last boot time: 2026-07-30 08:16:23

## CPU

- Model: 12th Gen Intel(R) Core(TM) i9-12900HX
- Physical cores: 16
- Logical processors: 24
- Max clock reported by WMI: 2300 MHz

## Memory

- Total RAM: 68,441,645,056 bytes
- Total RAM: 63.74 GiB

## GPU

- Discrete GPU: NVIDIA GeForce RTX 4060 Laptop GPU
- Integrated GPU: Intel(R) UHD Graphics
- NVIDIA driver version from `nvidia-smi`: 572.83
- NVIDIA WMI driver version: 32.0.15.7283
- Reported CUDA version from `nvidia-smi`: 12.8
- NVIDIA power limit: 115 W

Sample captured from `nvidia-smi` on 2026-08-09 17:07:40:

- GPU temperature: 64 C
- Performance state: P5
- GPU utilization: 19%
- VRAM in use: 1246 MiB
- VRAM total: 8188 MiB
- VRAM free at sample: 6712 MiB

Notes:

- `Win32_VideoController.AdapterRAM` under-reported the NVIDIA adapter
  and should not be used as the source of truth for VRAM capacity.
- `nvidia-smi` is the authoritative source here for practical GPU
  memory capacity.

## CUDA toolkit

- `nvcc`: not found in `PATH`
- `C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA`: not found

Interpretation:

- The NVIDIA driver exposes CUDA 12.8 capability.
- A local CUDA toolkit does not appear to be installed in the standard
  path at the time of inspection.

## Storage

Relevant volumes at the time of inspection:

- `C:` used 808.29 GiB, free 122.22 GiB
- `D:` used 192.26 GiB, free 784.30 GiB
- `E:` used 164.53 GiB, free 766.63 GiB
- `F:` used 93.16 GiB, free 26.15 GiB
- `G:` used 97.41 GiB, free 104.59 GiB

Workspace location:

- Workspace subdirectory at inspection: `benchmarks/browser_computer_use`
- Workspace drive free space at inspection: 784.30 GiB

## Toolchain

- Git: 2.43.0.windows.1
- Python: 3.13.13
- Node.js: v24.11.1
- npm: 11.6.2
- Playwright via `npx`: 1.62.1

Python packages checked in the active environment:

- `playwright`: not installed
- `torch`: not installed
- `transformers`: not installed
- `pynvml`: not installed

Interpretation:

- Playwright is available through `npx`, but the Python environment is
  not yet provisioned for benchmark execution.
- No local ML inference stack was detected in the active Python
  environment.

## Browsers

- Chrome: 150.0.7871.187
- Brave: 151.1.93.134
- Edge: 150.0.4078.105

Interpretation:

- There are multiple Chromium-based browser options available for the
  benchmark.
- This is useful for Suite C because certificate-backed flows often work
  best in a browser already integrated with the Windows certificate
  environment.

## Preliminary viability assessment

This section is an engineering inference from the measurements above.

- The machine has strong CPU and RAM headroom.
- The main constraint is GPU VRAM: 8 GiB effective total on the RTX 4060
  Laptop GPU.
- Small vision-capable models around 7B with efficient quantization are
  plausible first candidates.
- 14B-class models are likely to be difficult to compare fairly on this
  GPU without significant offload or aggressive quantization.
- For the first integration pass, the safest target class is likely a
  7B model in a Q4/Q5-style configuration, assuming the selected runtime
  supports the model architecture.
- Any model requiring a large vision encoder plus a large KV cache may
  be tight on this hardware and should be validated carefully before a
  full benchmark campaign.

## Immediate implications for the benchmark

- Prefer one 7B-class model first for end-to-end validation.
- Treat 14B-class candidates as conditional until runtime and memory
  requirements are confirmed.
- Plan for explicit monitoring of VRAM peaks and any RAM offload.
- Keep screenshot resolution conservative during early validation.
- Prefer Chromium-based automation initially because the machine already
  has Chrome, Brave and Edge available.

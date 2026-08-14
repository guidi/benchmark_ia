# Model Research

Last updated: 2026-08-09

## Scope

This document records the Phase 2 research for the initial priority
models:

- Microsoft Fara-7B
- OpenCUA-7B
- UI-TARS-1.5-7B

The goal is to decide which model should be integrated first on this
machine, using the constraints recorded in
[ENVIRONMENT_INVENTORY.md](ENVIRONMENT_INVENTORY.md).

## Hardware constraint that matters most

The current machine has:

- RTX 4060 Laptop GPU
- 8188 MiB VRAM reported by `nvidia-smi`

This is the primary constraint for local model selection.

## Summary table

| Model | Official runtime path found | License | Local-fit assessment on 8 GiB VRAM | Initial recommendation |
| --- | --- | --- | --- | --- |
| Fara-7B | Transformers, vLLM, SGLang | MIT | Possible only with a careful local path; official docs do not claim 8 GiB fit | Best first candidate |
| OpenCUA-7B | Transformers, vLLM with `--trust-remote-code` | MIT | More complex than Fara; likely needs careful memory handling and possibly quantization | Second candidate |
| UI-TARS-1.5-7B | Transformers, vLLM, HF endpoint deployment | Apache-2.0 | Official deployment guidance points to much larger GPU memory | Defer for later |

## 1. Microsoft Fara-7B

## What the official sources say

- Microsoft describes Fara-7B as a 7B multimodal decoder-only model for
  computer use that takes screenshot plus text context and predicts
  grounded actions.
- The Hugging Face model card exposes standard usage through
  `Transformers`, and the Hub also shows `vLLM` and `SGLang` usage.
- The Hugging Face page states the model is released under the MIT
  license.
- The current `microsoft/fara` GitHub repository is now centered on the
  newer Fara1.5 family. In that repo, Microsoft explicitly recommends
  WSL2 for Windows usage.

## Engineering interpretation

- Fara-7B appears to have the lowest integration friction of the three
  models because its official interfaces are relatively standard.
- It still does not have an official statement saying it fits in 8 GiB
  VRAM in full precision.
- For this machine, the realistic local path is likely a constrained or
  quantized deployment strategy, even though the official model card
  demonstrates standard `Transformers` and `vLLM` loading.
- The Windows recommendation toward WSL2 is a practical warning: native
  Windows should not be treated as the best-supported path by default.

## Decision

- Keep Fara-7B as the first integration candidate.

## 2. OpenCUA-7B

## What the official sources say

- The OpenCUA project page and model card position OpenCUA-7B as a
  strong 7B-scale computer-use model.
- The official GitHub repository says the project modified the
  Qwen-based model internals and explicitly warns not to use the default
  `transformers` and `vllm` classes naively.
- The repository recommends Python 3.10 in its installation steps.
- The repository recommends `vLLM` for production and says support for
  OpenCUA models is available with `vllm>=0.12.0` plus
  `--trust-remote-code`.
- The same repository announced an `OpenCUA-7B-exl2` quantized variant
  on 2025-10-12, but that quantized artifact is not presented as the
  primary official model release.
- The Hugging Face model card states MIT licensing for research,
  educational and commercial use.

## Engineering interpretation

- OpenCUA-7B is viable as a benchmark target, but the integration risk
  is higher than Fara-7B.
- The custom loading requirements and remote code path make the first
  integration more fragile.
- The official repo's Python 3.10 recommendation conflicts with the
  current local Python 3.13 environment for direct model-serving work.
- Because VRAM is only 8 GiB, a full official-path local serve is risky.
  A quantized path may be needed, but that moves us away from the
  simplest official setup.

## Decision

- Keep OpenCUA-7B as the second candidate, not the first.

## 3. UI-TARS-1.5-7B

## What the official sources say

- The Hugging Face model card exposes standard `Transformers` and
  `vLLM` usage.
- The same model card lists Apache-2.0 licensing.
- The UI-TARS GitHub repository states that UI-TARS-1.5-7B was
  open-sourced on 2025-04-16.
- The official deployment guide in the repository recommends, for the 7B
  model, a Hugging Face endpoint hardware class of `GPU L40S 1GPU 48G`,
  with Nvidia L4 or A100 mentioned as recommended hardware.
- The Hugging Face page also exposes community quantizations, but those
  are not the main official deployment recommendation.

## Engineering interpretation

- The official deployment guidance is materially out of range for an 8
  GiB RTX 4060 Laptop GPU.
- This does not prove UI-TARS-1.5-7B cannot run locally at all, but it
  does mean the official path is not aligned with the current machine.
- A local run here would likely depend on non-primary deployment paths,
  such as community quantization formats, and therefore should not be
  the first benchmark integration.

## Decision

- Defer UI-TARS-1.5-7B until after the benchmark harness works with a
  more realistic first model on this hardware.

## Initial shortlist

Order for the first implementation pass:

1. Fara-7B
2. OpenCUA-7B
3. UI-TARS-1.5-7B

## Why Fara-7B is first

- Lowest apparent integration complexity from official sources.
- Standard official paths through `Transformers`, `vLLM`, and `SGLang`.
- Cleaner first target for validating the benchmark harness.
- Less evidence of oversized official hardware assumptions than
  UI-TARS-1.5-7B.

## Additional note on Microsoft Fara1.5

This is an inference based on Microsoft's current public repository.

- The current `microsoft/fara` repository prominently foregrounds the
  newer Fara1.5 family, with a release dated 2026-07-22.
- After the first benchmark path is working, Fara1.5-9B is a plausible
  follow-on candidate in the "other 7B-14B models" bucket, but it should
  not replace the current initial priority list unless we explicitly
  choose to do so.

## Recommended next step

Proceed with the first implementation pass using this order:

1. keep the benchmark harness model-agnostic;
2. prepare for a Fara-7B-first integration path;
3. if direct official loading is too heavy on 8 GiB VRAM, document the
   failure clearly and only then move to the next most defensible local
   path.

## Sources

- [Microsoft Fara-7B model card](https://huggingface.co/microsoft/Fara-7B)
- [Microsoft Fara GitHub repository](https://github.com/microsoft/fara)
- [OpenCUA project page](https://opencua.xlang.ai/)
- [OpenCUA GitHub repository](https://github.com/xlang-ai/OpenCUA)
- [OpenCUA-7B model card](https://huggingface.co/xlangai/OpenCUA-7B)
- [UI-TARS-1.5-7B model card](https://huggingface.co/ByteDance-Seed/UI-TARS-1.5-7B)
- [UI-TARS GitHub repository](https://github.com/bytedance/UI-TARS-desktop)
- [UI-TARS deployment guide](https://github.com/bytedance/UI-TARS-desktop/blob/main/docs/deploy.md)

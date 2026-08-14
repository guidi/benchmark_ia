from __future__ import annotations

import argparse
import traceback

from vllm import LLM


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe a vLLM model load with explicit parameters.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--dtype", default="auto")
    parser.add_argument("--max-model-len", type=int, default=2048)
    parser.add_argument("--max-num-seqs", type=int, default=1)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.9)
    args = parser.parse_args()

    print("probe_start", flush=True)
    print(
        {
            "model": args.model,
            "dtype": args.dtype,
            "max_model_len": args.max_model_len,
            "max_num_seqs": args.max_num_seqs,
            "gpu_memory_utilization": args.gpu_memory_utilization,
        },
        flush=True,
    )

    try:
        llm = LLM(
            model=args.model,
            dtype=args.dtype,
            max_model_len=args.max_model_len,
            max_num_seqs=args.max_num_seqs,
            gpu_memory_utilization=args.gpu_memory_utilization,
        )
    except Exception as exc:  # pragma: no cover - diagnostic script
        print(f"llm_load_failed: {type(exc).__name__}: {exc}", flush=True)
        traceback.print_exc()
        return 1

    print(f"llm_load_ok: {llm.__class__.__name__}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

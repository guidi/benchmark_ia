from __future__ import annotations

import argparse
import traceback
from pathlib import Path

import torch
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor, BitsAndBytesConfig


def build_system_prompt(width: int, height: int) -> str:
    return (
        "You are Fara, a browser computer-use agent operating only through visible UI.\n"
        f"The screen resolution is {width}x{height}. Coordinates must be returned in viewport pixels.\n"
        "Return exactly two parts: plain reasoning text, then a single <tool_call>...</tool_call> block.\n"
        'Inside <tool_call>, emit strict JSON like {"name":"computer_use","arguments":{...}}.\n'
        "Supported actions are: key, type, mouse_move, left_click, double_click, right_click, triple_click, left_click_drag, scroll, hscroll, visit_url, history_back, web_search, read_page_answer_question, pause_and_memorize_fact, ask_user_question, wait, terminate.\n"
        "For left_click, double_click, right_click, triple_click, left_click_drag, and mouse_move, include coordinate as [x, y].\n"
        "For type, include text. Click first if an input must receive focus.\n"
        "For scroll, positive pixels mean scroll up and negative pixels mean scroll down.\n"
        "For terminate, include the final answer in arguments.answer.\n"
        "Do not mention hidden selectors, internal APIs, private state, or inaccessible information.\n"
        "Choose the single best next action from the visible screenshot."
    )


def build_user_prompt(objective: str, current_url: str, title: str, step_index: int) -> str:
    return (
        f"Objective: {objective}\n"
        f"Current URL: {current_url}\n"
        f"Page title: {title}\n"
        f"Step: {step_index}\n"
        "Here is the next screenshot. Think about what to do next."
    )


def build_quantization_config(bits: int | None) -> BitsAndBytesConfig | None:
    if bits is None:
        return None
    if bits == 4:
        return BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_quant_type="nf4",
        )
    if bits == 8:
        return BitsAndBytesConfig(load_in_8bit=True)
    raise ValueError(f"Unsupported bits value: {bits}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe local transformers generation for a Fara-style action.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--screenshot", type=Path, required=True)
    parser.add_argument("--objective", required=True)
    parser.add_argument("--current-url", required=True)
    parser.add_argument("--title", default="")
    parser.add_argument("--step-index", type=int, default=1)
    parser.add_argument("--bits", type=int, choices=[4, 8], default=None)
    parser.add_argument("--max-new-tokens", type=int, default=200)
    args = parser.parse_args()

    image = Image.open(args.screenshot).convert("RGB")
    system_prompt = build_system_prompt(image.width, image.height)
    user_prompt = build_user_prompt(args.objective, args.current_url, args.title, args.step_index)

    quantization_config = build_quantization_config(args.bits)
    model_kwargs: dict[str, object] = {
        "device_map": "auto",
        "trust_remote_code": False,
    }
    if quantization_config is not None:
        model_kwargs["quantization_config"] = quantization_config
    else:
        model_kwargs["dtype"] = torch.bfloat16

    print(
        {
            "model": args.model,
            "bits": args.bits,
            "screenshot": str(args.screenshot),
            "width": image.width,
            "height": image.height,
        },
        flush=True,
    )

    try:
        processor = AutoProcessor.from_pretrained(args.model, trust_remote_code=False)
        model = AutoModelForImageTextToText.from_pretrained(args.model, **model_kwargs)

        messages = [
            {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": user_prompt},
                ],
            },
        ]
        prompt = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = processor(text=[prompt], images=[image], return_tensors="pt")
        target_device = getattr(model, "device", torch.device("cuda" if torch.cuda.is_available() else "cpu"))
        inputs = {
            key: value.to(target_device) if hasattr(value, "to") else value
            for key, value in inputs.items()
        }

        with torch.inference_mode():
            generated = model.generate(
                **inputs,
                do_sample=False,
                max_new_tokens=args.max_new_tokens,
            )

        input_len = inputs["input_ids"].shape[1]
        continuation = generated[:, input_len:]
        output_text = processor.batch_decode(continuation, skip_special_tokens=True)[0]
        print("generation_ok", flush=True)
        print(output_text, flush=True)
        if torch.cuda.is_available():
            print(
                {
                    "cuda_max_allocated_mb": round(torch.cuda.max_memory_allocated() / 1024 / 1024, 2),
                    "cuda_max_reserved_mb": round(torch.cuda.max_memory_reserved() / 1024 / 1024, 2),
                },
                flush=True,
            )
        return 0
    except Exception as exc:  # pragma: no cover - diagnostic script
        print(f"generation_failed: {type(exc).__name__}: {exc}", flush=True)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import base64
import io
import os
import time
from typing import Any

import torch
from fastapi import FastAPI
from pydantic import BaseModel, Field
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor, BitsAndBytesConfig
import uvicorn


class ChatMessage(BaseModel):
    role: str
    content: str | list[dict[str, Any]]


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    temperature: float | None = 0.0
    max_tokens: int | None = 160


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


def decode_image_url(image_url: str) -> Image.Image:
    prefix = "data:image/png;base64,"
    if image_url.startswith(prefix):
        raw = base64.b64decode(image_url[len(prefix) :])
        return Image.open(io.BytesIO(raw)).convert("RGB")
    raise ValueError("Only data:image/png;base64 URLs are supported")


def convert_messages(messages: list[ChatMessage]) -> tuple[list[dict[str, Any]], list[Image.Image]]:
    converted: list[dict[str, Any]] = []
    images: list[Image.Image] = []
    for message in messages:
        if isinstance(message.content, str):
            converted.append({"role": message.role, "content": [{"type": "text", "text": message.content}]})
            continue

        content_items: list[dict[str, Any]] = []
        for item in message.content:
            item_type = item.get("type")
            if item_type == "text":
                content_items.append({"type": "text", "text": str(item.get("text", ""))})
            elif item_type == "image_url":
                image_payload = item.get("image_url") or {}
                image = decode_image_url(str(image_payload.get("url", "")))
                images.append(image)
                content_items.append({"type": "image", "image": image})
            else:
                raise ValueError(f"Unsupported content item type: {item_type}")
        converted.append({"role": message.role, "content": content_items})
    return converted, images


def build_app(model_name: str, bits: int | None) -> FastAPI:
    quantization_config = build_quantization_config(bits)
    model_kwargs: dict[str, Any] = {
        "device_map": "auto",
        "trust_remote_code": False,
    }
    if quantization_config is not None:
        model_kwargs["quantization_config"] = quantization_config
    else:
        model_kwargs["dtype"] = torch.bfloat16

    processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=False)
    model = AutoModelForImageTextToText.from_pretrained(model_name, **model_kwargs)
    model.eval()

    app = FastAPI(title="Transformers OpenAI-Compatible Server")

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"ok": True, "model": model_name, "bits": bits}

    @app.get("/v1/models")
    def models() -> dict[str, Any]:
        return {"data": [{"id": model_name, "object": "model"}]}

    @app.post("/v1/chat/completions")
    def chat_completions(request: ChatCompletionRequest) -> dict[str, Any]:
        converted_messages, images = convert_messages(request.messages)
        prompt = processor.apply_chat_template(converted_messages, tokenize=False, add_generation_prompt=True)
        inputs = processor(text=[prompt], images=images or None, return_tensors="pt")
        target_device = getattr(model, "device", torch.device("cuda" if torch.cuda.is_available() else "cpu"))
        inputs = {
            key: value.to(target_device) if hasattr(value, "to") else value
            for key, value in inputs.items()
        }

        with torch.inference_mode():
            generated = model.generate(
                **inputs,
                do_sample=(request.temperature or 0.0) > 0,
                temperature=max(request.temperature or 0.0, 0.0),
                max_new_tokens=request.max_tokens or 160,
            )

        input_len = inputs["input_ids"].shape[1]
        continuation = generated[:, input_len:]
        output_text = processor.batch_decode(continuation, skip_special_tokens=True)[0]
        return {
            "id": f"chatcmpl-local-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model_name,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": output_text},
                    "finish_reason": "stop",
                }
            ],
            "usage": None,
        }

    return app


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve a local transformers model behind a minimal OpenAI-compatible API.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--bits", type=int, choices=[4, 8], default=None)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()

    os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
    app = build_app(args.model, args.bits)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

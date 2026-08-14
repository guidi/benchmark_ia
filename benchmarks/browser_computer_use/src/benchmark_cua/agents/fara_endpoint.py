from __future__ import annotations

import ast
import base64
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import requests

from benchmark_cua.agents.base import ComputerUseAgent
from benchmark_cua.schemas import ActionType, AgentAction, AgentTaskContext

TOOL_CALL_PATTERN = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)
FUNCTION_TOOL_CALL_PATTERN = re.compile(r"<function=([^>]+)>\s*(.*?)\s*</function>", re.DOTALL)
PARAMETER_PATTERN = re.compile(r"<parameter=([^>]+)>\s*(.*?)\s*</parameter>", re.DOTALL)
BARE_KEY_PATTERN = re.compile(r'([{\s,])([A-Za-z_][A-Za-z0-9_]*)(\s*:)')
MISSING_LEADING_QUOTE_PATTERN = re.compile(r'([{\s,])([A-Za-z_][A-Za-z0-9_]*)\"(\s*:)')


class FaraEndpointAgent(ComputerUseAgent):
    """Computer-use adapter for Fara/OpenAI-compatible multimodal endpoints."""

    def __init__(
        self,
        model_id: str,
        base_url: str,
        api_key: str = "local-dev-token",
        temperature: float = 0.0,
        request_timeout_seconds: float = 240.0,
        max_history_messages: int = 8,
        max_completion_tokens: int = 384,
    ) -> None:
        self._model_id = model_id
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._temperature = temperature
        self._request_timeout_seconds = request_timeout_seconds
        self._max_history_messages = max_history_messages
        self._max_completion_tokens = max_completion_tokens
        self._history: list[dict[str, Any]] = []
        self._session = requests.Session()
        self._coordinate_space_size = 1000 if "fara1.5" in model_id.lower() else None

    @property
    def model_id(self) -> str:
        return self._model_id

    def warm_up(self) -> None:
        self._history = []

    def decide_next_action(
        self,
        task: AgentTaskContext,
        screenshot_path: str,
        step_index: int,
        state: dict[str, Any],
    ) -> AgentAction:
        image_path = Path(screenshot_path)
        width, height = _read_png_size(image_path)
        current_observation = {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": _image_path_to_data_url(image_path),
                    },
                },
                {
                    "type": "text",
                    "text": self._build_user_prompt(
                        task=task,
                        step_index=step_index,
                        state=state,
                        screenshot_width=width,
                        screenshot_height=height,
                    ),
                },
            ],
        }
        messages = [{"role": "system", "content": self._build_system_prompt(width, height)}]
        if self._max_history_messages > 0:
            messages.extend(self._history[-self._max_history_messages :])
        messages.append(current_observation)

        response = self._session.post(
            f"{self._base_url}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self._model_id,
                "messages": messages,
                "temperature": self._temperature,
                "max_tokens": self._max_completion_tokens,
            },
            timeout=self._request_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        message = ((payload.get("choices") or [{}])[0].get("message") or {})
        content = _extract_message_content(message)
        try:
            thoughts, action_payload = _extract_response_action(message)
        except Exception as exc:
            self._history.append(current_observation)
            self._history.append({"role": "assistant", "content": content})
            return AgentAction(
                action_type=ActionType.WAIT,
                metadata={
                    "milliseconds": 750,
                    "parse_error": str(exc),
                    "protocol_error": "response_parse_failed",
                    "raw_response": content,
                },
            )

        self._history.append(current_observation)
        self._history.append({"role": "assistant", "content": content or json.dumps(action_payload, ensure_ascii=False)})
        return self._translate_action(thoughts=thoughts, action_payload=action_payload, state=state)

    def _build_system_prompt(self, width: int, height: int) -> str:
        display_width = self._coordinate_space_size or width
        display_height = self._coordinate_space_size or height
        return (
            "You are Fara, a browser computer-use agent operating only through visible UI.\n"
            f"The screen resolution is {display_width}x{display_height}.\n"
            "Return exactly two parts: plain reasoning text, then a single <tool_call>...</tool_call> block.\n"
            'Inside <tool_call>, emit strict JSON like {"name":"computer_use","arguments":{...}}.\n'
            "Supported actions are: key, type, mouse_move, left_click, double_click, right_click, triple_click, left_click_drag, scroll, hscroll, visit_url, history_back, web_search, read_page_answer_question, pause_and_memorize_fact, ask_user_question, wait, terminate.\n"
            "For left_click, double_click, right_click, triple_click, left_click_drag, and mouse_move, include coordinate as [x, y].\n"
            "For type, include text. Click first if an input must receive focus.\n"
            "For scroll, positive pixels mean scroll up and negative pixels mean scroll down.\n"
            "For terminate, include the final answer in arguments.answer.\n"
            "Keep reasoning brief, ideally one short sentence.\n"
            "Emit compact JSON on a single line inside <tool_call>.\n"
            "Do not mention hidden selectors, internal APIs, private state, or inaccessible information.\n"
            "If the task requires a textual answer, place only the exact final answer in arguments.answer, with no explanation."
        )

    def _build_user_prompt(
        self,
        task: AgentTaskContext,
        step_index: int,
        state: dict[str, Any],
        screenshot_width: int,
        screenshot_height: int,
    ) -> str:
        current_url = state.get("current_url") or task.start_url
        title = state.get("title") or ""
        return (
            f"Task title: {task.title}\n"
            f"Objective: {task.objective}\n"
            f"Start URL: {task.start_url}\n"
            f"Current URL: {current_url}\n"
            f"Page title: {title}\n"
            f"Step: {step_index + 1} of {task.max_steps}\n"
            f"Timeout budget (seconds): {task.timeout_seconds}\n"
            f"Requires textual answer: {'yes' if task.requires_answer else 'no'}\n"
            f"Visible screenshot size: {screenshot_width}x{screenshot_height}\n"
            "Choose the single best next action."
        )

    def _translate_action(self, thoughts: str, action_payload: dict[str, Any], state: dict[str, Any]) -> AgentAction:
        arguments = action_payload.get("arguments", {})
        action_name = str(arguments.get("action", arguments.get("name", ""))).strip().lower()
        coordinate = arguments.get("coordinate")
        viewport = state.get("viewport") or {}
        viewport_width = int(viewport.get("width", 1280))
        viewport_height = int(viewport.get("height", 720))
        mapped_x, mapped_y = _map_coordinate(
            coordinate=coordinate,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            coordinate_space_size=self._coordinate_space_size,
        )
        if action_name in {"click", "left_click"}:
            return AgentAction(action_type=ActionType.CLICK, x=mapped_x, y=mapped_y, metadata={"raw_action": action_payload})
        if action_name in {"mouse_move", "hover"}:
            return AgentAction(action_type=ActionType.MOUSE_MOVE, x=mapped_x, y=mapped_y, metadata={"raw_action": action_payload})
        if action_name in {"input_text", "type"}:
            return AgentAction(
                action_type=ActionType.TYPE,
                x=mapped_x,
                y=mapped_y,
                text=str(arguments.get("text", arguments.get("text_value", ""))),
                metadata={
                    "press_enter": bool(arguments.get("press_enter", False)),
                    "delete_existing_text": bool(arguments.get("delete_existing_text", False)),
                    "raw_action": action_payload,
                },
            )
        if action_name == "double_click":
            return AgentAction(action_type=ActionType.CLICK, x=mapped_x, y=mapped_y, metadata={"click_count": 2, "raw_action": action_payload})
        if action_name == "right_click":
            return AgentAction(action_type=ActionType.CLICK, x=mapped_x, y=mapped_y, metadata={"button": "right", "raw_action": action_payload})
        if action_name == "triple_click":
            return AgentAction(action_type=ActionType.CLICK, x=mapped_x, y=mapped_y, metadata={"click_count": 3, "raw_action": action_payload})
        if action_name == "left_click_drag":
            return AgentAction(action_type=ActionType.MOUSE_MOVE, x=mapped_x, y=mapped_y, metadata={"drag": True, "raw_action": action_payload})
        if action_name in {"keypress", "key"}:
            keys = arguments.get("keys", arguments.get("key", []))
            key_sequence: list[str] = []
            if isinstance(keys, list) and keys:
                key_sequence = [str(item).strip() for item in keys if str(item).strip()]
            elif isinstance(keys, str) and keys.strip():
                key_sequence = [keys.strip()]
            elif arguments.get("text"):
                key_sequence = [part.strip() for part in str(arguments.get("text", "")).split() if part.strip()]
            key = "+".join(key_sequence) if len(key_sequence) > 1 else (key_sequence[0] if key_sequence else "")
            return AgentAction(
                action_type=ActionType.KEYPRESS,
                key=key,
                metadata={"key_sequence": key_sequence, "raw_action": action_payload},
            )
        if action_name in {"scroll", "hscroll"}:
            pixels = float(arguments.get("pixels", -600))
            delta_y = _map_scroll_pixels(
                pixels=pixels,
                axis=action_name,
                viewport_width=viewport_width,
                viewport_height=viewport_height,
                coordinate_space_size=self._coordinate_space_size,
            )
            return AgentAction(action_type=ActionType.SCROLL, delta_y=delta_y, metadata={"axis": action_name, "raw_action": action_payload})
        if action_name == "visit_url":
            return AgentAction(action_type=ActionType.NAVIGATE, text=str(arguments.get("url", "")), metadata={"raw_action": action_payload})
        if action_name == "web_search":
            query = str(arguments.get("query", ""))
            return AgentAction(
                action_type=ActionType.NAVIGATE,
                text=f"https://www.bing.com/search?q={quote_plus(query)}",
                metadata={"raw_action": action_payload},
            )
        if action_name == "history_back":
            return AgentAction(action_type=ActionType.BACK, metadata={"raw_action": action_payload})
        if action_name == "read_page_answer_question":
            return AgentAction(action_type=ActionType.ANSWER, text=str(arguments.get("question", "")), metadata={"raw_action": action_payload, "mode": "read_page_answer_question"})
        if action_name == "ask_user_question":
            return AgentAction(action_type=ActionType.WAIT, metadata={"milliseconds": 1000, "mode": "ask_user_question", "question": str(arguments.get("question", "")), "raw_action": action_payload})
        if action_name == "pause_and_memorize_fact":
            return AgentAction(
                action_type=ActionType.WAIT,
                metadata={
                    "milliseconds": 50,
                    "mode": "pause_and_memorize_fact",
                    "fact": str(arguments.get("fact", "")),
                    "raw_action": action_payload,
                },
            )
        if action_name in {"sleep", "wait"}:
            milliseconds = int(float(arguments.get("time", arguments.get("duration", 1.0))) * 1000)
            return AgentAction(action_type=ActionType.WAIT, metadata={"milliseconds": milliseconds, "raw_action": action_payload})
        if action_name in {"stop", "terminate"}:
            final_answer = arguments.get("answer")
            if final_answer is None or not str(final_answer).strip():
                return AgentAction(
                    action_type=ActionType.WAIT,
                    metadata={
                        "milliseconds": 500,
                        "protocol_error": "terminate_missing_answer",
                        "raw_action": action_payload,
                    },
                )
            return AgentAction(
                action_type=ActionType.ANSWER,
                text=str(final_answer).strip(),
                metadata={"status": str(arguments.get("status", "success")), "raw_action": action_payload},
            )
        return AgentAction(
            action_type=ActionType.WAIT,
            metadata={
                "milliseconds": 500,
                "unsupported_action": action_name,
                "protocol_error": "unsupported_action_schema",
                "raw_action": action_payload,
            },
        )


def _extract_message_content(message: dict[str, Any]) -> str:
    content = message.get("content")
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "\n".join(parts).strip()
    raise ValueError("Endpoint response did not include textual content")


def _extract_response_action(message: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    thoughts = _extract_message_content(message)
    tool_calls = message.get("tool_calls") or []
    if tool_calls:
        return thoughts, _parse_structured_tool_call(tool_calls[0])
    return _parse_tool_call(thoughts)


def _parse_tool_call(content: str) -> tuple[str, dict[str, Any]]:
    match = TOOL_CALL_PATTERN.search(content)
    if match is None and "<tool_call>" in content:
        prefix, suffix = content.split("<tool_call>", 1)
        thoughts = prefix.strip()
        action_text = _sanitize_tool_call_text(suffix.strip())
        return thoughts, _parse_tool_call_payload(action_text)
    if match is None:
        raise ValueError(f"Model response did not contain a <tool_call> block: {content}")
    thoughts = content[: match.start()].strip()
    action_text = _sanitize_tool_call_text(match.group(1).strip())
    return thoughts, _parse_tool_call_payload(action_text)


def _parse_tool_call_payload(action_text: str) -> dict[str, Any]:
    if "<function=" in action_text:
        return _parse_function_tool_call(action_text)
    try:
        action_payload = json.loads(action_text)
    except json.JSONDecodeError:
        repaired_text = _repair_json_like_tool_call(action_text)
        try:
            action_payload = json.loads(repaired_text)
        except json.JSONDecodeError:
            action_payload = ast.literal_eval(repaired_text)
    if not isinstance(action_payload, dict):
        raise ValueError(f"Model tool call was not a JSON object: {action_text}")
    return _normalize_action_payload(action_payload)


def _sanitize_tool_call_text(action_text: str) -> str:
    sanitized = action_text.strip()
    if sanitized.startswith("```"):
        sanitized = sanitized.strip("`")
        if sanitized.startswith("json"):
            sanitized = sanitized[4:]
    if "<tool_call>" in sanitized:
        sanitized = sanitized.split("<tool_call>", 1)[0]
    return sanitized.strip()


def _repair_json_like_tool_call(action_text: str) -> str:
    repaired = action_text.replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'")
    repaired = MISSING_LEADING_QUOTE_PATTERN.sub(r'\1"\2"\3', repaired)
    repaired = BARE_KEY_PATTERN.sub(r'\1"\2"\3', repaired)
    repaired = repaired.replace(',}', '}').replace(',]', ']')
    return repaired


def _parse_structured_tool_call(tool_call: dict[str, Any]) -> dict[str, Any]:
    function = tool_call.get("function") or {}
    function_name = function.get("name") or tool_call.get("name")
    if not function_name:
        raise ValueError(f"Structured tool_call missing function name: {tool_call}")
    raw_arguments = function.get("arguments", {})
    if isinstance(raw_arguments, str):
        arguments = _parse_structured_arguments(raw_arguments)
    elif isinstance(raw_arguments, dict):
        arguments = raw_arguments
    else:
        raise ValueError(f"Structured tool_call arguments must be string or object: {tool_call}")
    return _normalize_action_payload({"name": str(function_name), "arguments": arguments})


def _parse_structured_arguments(raw_arguments: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw_arguments)
    except json.JSONDecodeError:
        repaired_text = _repair_json_like_tool_call(raw_arguments)
        try:
            parsed = json.loads(repaired_text)
        except json.JSONDecodeError:
            parsed = ast.literal_eval(repaired_text)
    if not isinstance(parsed, dict):
        raise ValueError(f"Structured tool_call arguments were not a JSON object: {raw_arguments}")
    return parsed


def _parse_function_tool_call(action_text: str) -> dict[str, Any]:
    match = FUNCTION_TOOL_CALL_PATTERN.search(action_text.strip())
    if match is None:
        raise ValueError(f"Malformed function tool_call payload: {action_text}")
    function_name = match.group(1).strip()
    body = match.group(2)
    arguments: dict[str, Any] = {}
    for parameter_name, raw_value in PARAMETER_PATTERN.findall(body):
        arguments[parameter_name.strip()] = _parse_parameter_value(raw_value)
    return _normalize_action_payload({"name": function_name, "arguments": arguments})


def _parse_parameter_value(raw_value: str) -> Any:
    value = raw_value.strip()
    if not value:
        return ""
    for parser in (json.loads, ast.literal_eval):
        try:
            return parser(value)
        except (json.JSONDecodeError, SyntaxError, ValueError):
            continue
    return value


def _normalize_action_payload(action_payload: dict[str, Any]) -> dict[str, Any]:
    current = action_payload
    while True:
        arguments = current.get("arguments")
        outer_name = str(current.get("name", "")).strip().lower()
        if not isinstance(arguments, dict):
            raise ValueError(f"Model tool call arguments must be an object: {action_payload}")
        inner_name = str(arguments.get("name", "")).strip().lower()
        inner_arguments = arguments.get("arguments")
        if outer_name in {"", "computer_use"} and inner_name == "computer_use" and isinstance(inner_arguments, dict):
            current = {"name": "computer_use", "arguments": inner_arguments}
            continue
        return current


def _image_path_to_data_url(image_path: Path) -> str:
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _read_png_size(image_path: Path) -> tuple[int, int]:
    with image_path.open("rb") as handle:
        header = handle.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Unsupported screenshot format for {image_path}")
    width = int.from_bytes(header[16:20], "big")
    height = int.from_bytes(header[20:24], "big")
    return width, height


def _coord_x(coordinate: Any) -> float | None:
    if isinstance(coordinate, list) and len(coordinate) >= 2:
        return float(coordinate[0])
    return None


def _coord_y(coordinate: Any) -> float | None:
    if isinstance(coordinate, list) and len(coordinate) >= 2:
        return float(coordinate[1])
    return None


def _map_coordinate(
    coordinate: Any,
    viewport_width: int,
    viewport_height: int,
    coordinate_space_size: int | None,
) -> tuple[float | None, float | None]:
    raw_x = _coord_x(coordinate)
    raw_y = _coord_y(coordinate)
    if raw_x is None or raw_y is None:
        return raw_x, raw_y
    if coordinate_space_size is None:
        return raw_x, raw_y
    return (
        round(raw_x * viewport_width / coordinate_space_size, 2),
        round(raw_y * viewport_height / coordinate_space_size, 2),
    )


def _map_scroll_pixels(
    pixels: float,
    axis: str,
    viewport_width: int,
    viewport_height: int,
    coordinate_space_size: int | None,
) -> float:
    scale_base = viewport_width if axis == "hscroll" else viewport_height
    mapped = pixels
    if coordinate_space_size is not None:
        mapped = pixels * scale_base / coordinate_space_size
    return abs(mapped) if mapped < 0 else -abs(mapped)

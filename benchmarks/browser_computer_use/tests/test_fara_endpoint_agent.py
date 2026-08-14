from __future__ import annotations

from pathlib import Path

from benchmark_cua.agents.fara_endpoint import _extract_response_action
from benchmark_cua.agents.fara_endpoint import _parse_tool_call
from benchmark_cua.agents.fara_endpoint import FaraEndpointAgent
from benchmark_cua.schemas import ActionType, AgentTaskContext


def test_parse_tool_call_block() -> None:
    thoughts, action = _parse_tool_call(
        'I should click the button.\n<tool_call>\n{"name":"computer_use","arguments":{"action":"left_click","coordinate":[320,180]}}\n</tool_call>'
    )
    assert thoughts == "I should click the button."
    assert action["arguments"]["action"] == "left_click"


def test_parse_tool_call_with_repairable_json() -> None:
    thoughts, action = _parse_tool_call(
        'Clicking now.\n<tool_call>\n{"name":"computer_use",arguments: {"action":"left_click","coordinate":[90,120]}}\n</tool_call>'
    )
    assert thoughts == "Clicking now."
    assert action["arguments"]["coordinate"] == [90, 120]


def test_parse_tool_call_with_missing_leading_quote() -> None:
    thoughts, action = _parse_tool_call(
        'Clicking now.\n<tool_call>\n{"name":"computer_use",arguments": {"action":"left_click","coordinate":[90,120]}}\n</tool_call>'
    )
    assert thoughts == "Clicking now."
    assert action["arguments"]["coordinate"] == [90, 120]


def test_parse_tool_call_without_closing_tag() -> None:
    thoughts, action = _parse_tool_call(
        'Clicking now.\n<tool_call>\n{"name":"computer_use","arguments":{"action":"left_click","coordinate":[90,120]}}'
    )
    assert thoughts == "Clicking now."
    assert action["arguments"]["coordinate"] == [90, 120]


def test_parse_tool_call_trims_duplicate_trailing_open_tag() -> None:
    thoughts, action = _parse_tool_call(
        'Clicking now.\n<tool_call>\n{"name":"computer_use","arguments":{"action":"left_click","coordinate":[90,120]}}<tool_call>'
    )
    assert thoughts == "Clicking now."
    assert action["arguments"]["coordinate"] == [90, 120]


def test_parse_official_function_tool_call_format() -> None:
    thoughts, action = _parse_tool_call(
        "Open the filter.\n"
        "<tool_call>\n"
        "<function=computer_use>\n"
        "<parameter=action>\nleft_click\n</parameter>\n"
        "<parameter=coordinate>\n[500, 500]\n</parameter>\n"
        "</function>\n"
        "</tool_call>"
    )
    assert thoughts == "Open the filter."
    assert action == {"name": "computer_use", "arguments": {"action": "left_click", "coordinate": [500, 500]}}


def test_parse_official_function_tool_call_terminate_format() -> None:
    thoughts, action = _parse_tool_call(
        "Finish the task.\n"
        "<tool_call>\n"
        "<function=computer_use>\n"
        "<parameter=action>\nterminate\n</parameter>\n"
        "<parameter=answer>\n10491\n</parameter>\n"
        "</function>\n"
        "</tool_call>"
    )
    assert thoughts == "Finish the task."
    assert action == {"name": "computer_use", "arguments": {"action": "terminate", "answer": 10491}}


def test_parse_nested_computer_use_wrapper() -> None:
    thoughts, action = _parse_tool_call(
        'Going back.\n<tool_call>\n{"name":"computer_use","arguments":{"name":"computer_use","arguments":{"name":"history_back"}}}\n</tool_call>'
    )
    assert thoughts == "Going back."
    assert action == {"name": "computer_use", "arguments": {"name": "history_back"}}


def test_extract_response_action_supports_structured_tool_calls() -> None:
    thoughts, action = _extract_response_action(
        {
            "content": "Apply the next action.",
            "tool_calls": [
                {
                    "function": {
                        "name": "computer_use",
                        "arguments": '{"action":"left_click","coordinate":[500,500]}',
                    }
                }
            ],
        }
    )
    assert thoughts == "Apply the next action."
    assert action == {"name": "computer_use", "arguments": {"action": "left_click", "coordinate": [500, 500]}}


def test_translate_click_action() -> None:
    agent = FaraEndpointAgent(model_id="microsoft/Fara-7B", base_url="http://localhost:5000")
    action = agent._translate_action(
        thoughts="Clicking now.",
        action_payload={"name": "computer_use", "arguments": {"action": "left_click", "coordinate": [320, 180]}},
        state={"viewport": {"width": 1280, "height": 720}},
    )
    assert action.action_type == ActionType.CLICK
    assert action.x == 320
    assert action.y == 180


def test_translate_scroll_and_terminate_actions() -> None:
    agent = FaraEndpointAgent(model_id="microsoft/Fara-7B", base_url="http://localhost:5000")
    scroll = agent._translate_action(
        thoughts="Need to move downward.",
        action_payload={"name": "computer_use", "arguments": {"action": "scroll", "pixels": -850}},
        state={"viewport": {"width": 1280, "height": 720}},
    )
    terminate = agent._translate_action(
        thoughts="internal reasoning",
        action_payload={"name": "computer_use", "arguments": {"action": "terminate", "status": "success", "answer": "12345"}},
        state={"viewport": {"width": 1280, "height": 720}},
    )
    assert scroll.action_type == ActionType.SCROLL
    assert scroll.delta_y == 850
    assert terminate.action_type == ActionType.ANSWER
    assert terminate.text == "12345"


def test_translate_pause_and_memorize_fact_is_supported_without_protocol_error() -> None:
    agent = FaraEndpointAgent(model_id="microsoft/Fara1.5-4B", base_url="http://localhost:5000")
    action = agent._translate_action(
        thoughts="Memorize and continue.",
        action_payload={"name": "computer_use", "arguments": {"action": "pause_and_memorize_fact", "fact": "pedido correto = 10489"}},
        state={"viewport": {"width": 1280, "height": 720}},
    )
    assert action.action_type == ActionType.WAIT
    assert action.metadata["mode"] == "pause_and_memorize_fact"
    assert action.metadata["fact"] == "pedido correto = 10489"
    assert "protocol_error" not in action.metadata


def test_translate_type_without_coordinates() -> None:
    agent = FaraEndpointAgent(model_id="microsoft/Fara1.5-4B", base_url="http://localhost:5000")
    action = agent._translate_action(
        thoughts="Typing the search.",
        action_payload={"name": "computer_use", "arguments": {"action": "type", "text": "teclado mecanico"}},
        state={"viewport": {"width": 1280, "height": 720}},
    )
    assert action.action_type == ActionType.TYPE
    assert action.text == "teclado mecanico"
    assert action.x is None
    assert action.y is None


def test_translate_fara15_coordinates_are_rescaled() -> None:
    agent = FaraEndpointAgent(model_id="microsoft/Fara1.5-4B", base_url="http://localhost:5000")
    action = agent._translate_action(
        thoughts="Clicking now.",
        action_payload={"name": "computer_use", "arguments": {"action": "left_click", "coordinate": [500, 500]}},
        state={"viewport": {"width": 1280, "height": 720}},
    )
    assert action.action_type == ActionType.CLICK
    assert action.x == 640
    assert action.y == 360


def test_translate_action_name_fallback() -> None:
    agent = FaraEndpointAgent(model_id="microsoft/Fara1.5-4B", base_url="http://localhost:5000")
    action = agent._translate_action(
        thoughts="Clicking now.",
        action_payload={"name": "computer_use", "arguments": {"name": "left_click", "coordinate": [500, 500]}},
        state={"viewport": {"width": 1280, "height": 720}},
    )
    assert action.action_type == ActionType.CLICK
    assert action.x == 640
    assert action.y == 360


def test_translate_key_action_with_text_sequence() -> None:
    agent = FaraEndpointAgent(model_id="microsoft/Fara1.5-4B", base_url="http://localhost:5000")
    action = agent._translate_action(
        thoughts="Move in the dropdown.",
        action_payload={"name": "computer_use", "arguments": {"name": "key", "text": "ArrowDown Enter"}},
        state={"viewport": {"width": 1280, "height": 720}},
    )
    assert action.action_type == ActionType.KEYPRESS
    assert action.key == "ArrowDown+Enter"
    assert action.metadata["key_sequence"] == ["ArrowDown", "Enter"]


def test_translate_invalid_answer_only_schema_remains_protocol_error() -> None:
    agent = FaraEndpointAgent(model_id="microsoft/Fara1.5-4B", base_url="http://localhost:5000")
    action = agent._translate_action(
        thoughts="10489",
        action_payload={"name": "computer_use", "arguments": {"answer": "10489"}},
        state={"viewport": {"width": 1280, "height": 720}},
    )
    assert action.action_type == ActionType.WAIT
    assert action.metadata["unsupported_action"] == ""
    assert action.metadata["protocol_error"] == "unsupported_action_schema"


def test_translate_terminate_without_answer_remains_protocol_error() -> None:
    agent = FaraEndpointAgent(model_id="microsoft/Fara1.5-4B", base_url="http://localhost:5000")
    action = agent._translate_action(
        thoughts="10491",
        action_payload={"name": "computer_use", "arguments": {"action": "terminate"}},
        state={"viewport": {"width": 1280, "height": 720}},
    )
    assert action.action_type == ActionType.WAIT
    assert action.metadata["protocol_error"] == "terminate_missing_answer"


def test_translate_terminate_boolean_without_answer_remains_protocol_error() -> None:
    agent = FaraEndpointAgent(model_id="microsoft/Fara1.5-4B", base_url="http://localhost:5000")
    action = agent._translate_action(
        thoughts="10491",
        action_payload={"name": "computer_use", "arguments": {"terminate": True}},
        state={"viewport": {"width": 1280, "height": 720}},
    )
    assert action.action_type == ActionType.WAIT
    assert action.metadata["protocol_error"] == "unsupported_action_schema"


def test_build_user_prompt_includes_task_shape() -> None:
    agent = FaraEndpointAgent(model_id="microsoft/Fara-7B", base_url="http://localhost:5000")
    task = AgentTaskContext(
        title="Open order details",
        objective="Find the requested order and open its detail page.",
        start_url="/orders",
        requires_answer=False,
        max_steps=12,
        timeout_seconds=180,
    )
    prompt = agent._build_user_prompt(
        task=task,
        step_index=2,
        state={"current_url": "http://example.test/orders", "title": "Orders"},
        screenshot_width=1280,
        screenshot_height=720,
    )
    assert "Open order details" in prompt
    assert "Step: 3 of 12" in prompt
    assert "Visible screenshot size: 1280x720" in prompt


def test_zero_history_messages_sends_only_current_observation(tmp_path: Path) -> None:
    screenshot = tmp_path / "shot.png"
    screenshot.write_bytes(
        bytes.fromhex(
            "89504E470D0A1A0A"
            "0000000D4948445200000001000000010802000000907753DE"
            "0000000C49444154789C63F8FFFF3F0005FE02FE0D8D38E5"
            "0000000049454E44AE426082"
        )
    )

    captured: list[dict] = []

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "choices": [
                    {
                        "message": {
                            "content": 'Ready.\n<tool_call>{"name":"computer_use","arguments":{"action":"wait","time":0.5}}</tool_call>'
                        }
                    }
                ]
            }

    agent = FaraEndpointAgent(model_id="microsoft/Fara-7B", base_url="http://localhost:5000", max_history_messages=0)

    def _fake_post(*args, **kwargs):  # type: ignore[no-untyped-def]
        captured.append(kwargs["json"])
        return _Response()

    agent._session.post = _fake_post  # type: ignore[method-assign]
    task = AgentTaskContext(
        title="Open order details",
        objective="Find the requested order and open its detail page.",
        start_url="/orders",
        requires_answer=False,
        max_steps=12,
        timeout_seconds=180,
    )
    state = {"current_url": "http://example.test/orders", "title": "Orders", "viewport": {"width": 1280, "height": 720}}

    agent.decide_next_action(task=task, screenshot_path=str(screenshot), step_index=0, state=state)
    agent.decide_next_action(task=task, screenshot_path=str(screenshot), step_index=1, state=state)

    assert len(captured) == 2
    assert len(captured[0]["messages"]) == 2
    assert len(captured[1]["messages"]) == 2


def test_decide_next_action_marks_parse_failures_as_protocol_errors(tmp_path: Path) -> None:
    screenshot = tmp_path / "shot.png"
    screenshot.write_bytes(
        bytes.fromhex(
            "89504E470D0A1A0A"
            "0000000D4948445200000001000000010802000000907753DE"
            "0000000C49444154789C63F8FFFF3F0005FE02FE0D8D38E5"
            "0000000049454E44AE426082"
        )
    )

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"choices": [{"message": {"content": "No tool call here."}}]}

    agent = FaraEndpointAgent(model_id="microsoft/Fara1.5-4B", base_url="http://localhost:5000")
    agent._session.post = lambda *args, **kwargs: _Response()  # type: ignore[method-assign]
    task = AgentTaskContext(
        title="Open order details",
        objective="Find the requested order and open its detail page.",
        start_url="/orders",
        requires_answer=False,
        max_steps=12,
        timeout_seconds=180,
    )
    action = agent.decide_next_action(
        task=task,
        screenshot_path=str(screenshot),
        step_index=0,
        state={"current_url": "http://example.test/orders", "title": "Orders", "viewport": {"width": 1280, "height": 720}},
    )
    assert action.action_type == ActionType.WAIT
    assert action.metadata["protocol_error"] == "response_parse_failed"

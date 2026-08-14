from __future__ import annotations

from typing import Any

from benchmark_cua.agents.base import ComputerUseAgent
from benchmark_cua.schemas import AgentAction, AgentTaskContext


class ScriptedAgent(ComputerUseAgent):
    """Deterministic agent used to smoke-test the harness itself."""

    def __init__(self, model_id: str, actions: list[AgentAction]) -> None:
        self._model_id = model_id
        self._actions = actions
        self._cursor = 0

    @property
    def model_id(self) -> str:
        return self._model_id

    def warm_up(self) -> None:
        self._cursor = 0

    def decide_next_action(
        self,
        task: AgentTaskContext,
        screenshot_path: str,
        step_index: int,
        state: dict[str, Any],
    ) -> AgentAction:
        if self._cursor >= len(self._actions):
            return AgentAction(action_type="wait", metadata={"reason": "script_exhausted"})
        action = self._actions[self._cursor]
        self._cursor += 1
        return action

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from benchmark_cua.schemas import AgentAction, AgentTaskContext


class ComputerUseAgent(ABC):
    """Common contract for browser/computer-use model adapters."""

    @property
    @abstractmethod
    def model_id(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def warm_up(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def decide_next_action(
        self,
        task: AgentTaskContext,
        screenshot_path: str,
        step_index: int,
        state: dict[str, Any],
    ) -> AgentAction:
        raise NotImplementedError

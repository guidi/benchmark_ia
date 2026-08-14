from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    CLICK = "click"
    MOUSE_MOVE = "mouse_move"
    TYPE = "type"
    SELECT = "select"
    SCROLL = "scroll"
    KEYPRESS = "keypress"
    WAIT = "wait"
    NAVIGATE = "navigate"
    BACK = "back"
    ANSWER = "answer"


class AgentAction(BaseModel):
    action_type: ActionType
    target: str | None = None
    text: str | None = None
    x: float | None = None
    y: float | None = None
    delta_y: float | None = None
    key: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskDefinition(BaseModel):
    task_id: str
    suite: str
    title: str
    objective: str
    start_url: str
    requires_answer: bool = False
    max_steps: int = 25
    timeout_seconds: int = 180
    private_context: dict[str, Any] = Field(default_factory=dict)


class AgentTaskContext(BaseModel):
    title: str
    objective: str
    start_url: str
    requires_answer: bool = False
    max_steps: int = 25
    timeout_seconds: int = 180

    @classmethod
    def from_task_definition(cls, task: TaskDefinition) -> "AgentTaskContext":
        return cls(
            title=task.title,
            objective=task.objective,
            start_url=task.start_url,
            requires_answer=task.requires_answer,
            max_steps=task.max_steps,
            timeout_seconds=task.timeout_seconds,
        )


class RunMetadata(BaseModel):
    run_id: str
    task_id: str
    model: str
    suite: str | None = None
    suite_version: str | None = None
    campaign_id: str | None = None
    model_checkpoint: str | None = None
    execution_class: str | None = None
    quantization: str | None = None
    runtime: str | None = None
    runtime_version: str | None = None
    offload_policy: str | None = None
    endpoint_base_url: str | None = None
    endpoint_contract: str | None = None
    benchmark_git_sha: str | None = None
    benchmark_git_dirty: bool | None = None
    benchmark_git_diff_hash: str | None = None
    task_snapshot_hash: str | None = None
    seed_data_hash: str | None = None
    environment_inventory_path: str | None = None
    environment_inventory_hash: str | None = None
    notes: str | None = None


class StepTiming(BaseModel):
    screenshot_ms: float = 0.0
    decision_ms: float = 0.0
    action_ms: float = 0.0
    validation_ms: float = 0.0
    step_total_ms: float = 0.0


class ValidationRequest(BaseModel):
    current_path: str | None = None
    answer: str | None = None


class ValidationResult(BaseModel):
    success: bool
    expected: str
    observed: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class RunResult(BaseModel):
    success: bool
    task_success: bool
    semantic_success: bool
    protocol_error: bool = False
    executor_error: bool = False
    model_error: bool = False
    task_id: str
    run_id: str
    requested_run_id: str
    artifact_dir: str
    final_url: str
    steps_executed: int
    answer: str | None = None
    invalid_actions: int = 0
    recovery_actions: int = 0
    protocol_errors: int = 0
    executor_errors: int = 0
    failure_reason: str | None = None
    action_errors: list[str] = Field(default_factory=list)
    average_action_latency_ms: float | None = None
    duration_seconds: float | None = None
    peak_ram_mb: float | None = None
    peak_vram_mb: float | None = None
    gpu_utilization_average: float | None = None
    gpu_utilization_peak: float | None = None
    validation: ValidationResult

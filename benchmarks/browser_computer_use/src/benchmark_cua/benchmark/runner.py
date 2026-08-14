from __future__ import annotations

import hashlib
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any

import requests
from playwright.sync_api import Error as PlaywrightError

from benchmark_cua.agents.base import ComputerUseAgent
from benchmark_cua.browser.session import BrowserConfig, launch_browser
from benchmark_cua.metrics.monitor import ResourceMonitor
from benchmark_cua.schemas import (
    ActionType,
    AgentAction,
    AgentTaskContext,
    RunMetadata,
    RunResult,
    StepTiming,
    TaskDefinition,
    ValidationResult,
)
from benchmark_cua.site.data import clone_seed_data


class ControlledTaskRunner:
    def __init__(
        self,
        base_url: str,
        internal_token: str,
        browser_config: BrowserConfig | None = None,
        artifacts_root: Path | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.internal_token = internal_token
        self.browser_config = browser_config or BrowserConfig()
        self.artifacts_root = artifacts_root or Path("artifacts/runs")
        self._pending_native_select: dict[str, Any] | None = None

    def fetch_tasks(self) -> dict[str, TaskDefinition]:
        session = self._internal_session()
        response = session.get(f"{self.base_url}/api/internal/tasks", timeout=15)
        response.raise_for_status()
        payload = response.json()
        return {item["task_id"]: TaskDefinition.model_validate(item) for item in payload}

    def reset_and_fetch_tasks(self) -> dict[str, TaskDefinition]:
        session = self._internal_session()
        session.post(f"{self.base_url}/api/internal/reset", timeout=15).raise_for_status()
        return self.fetch_tasks()

    def run_task(
        self,
        agent: ComputerUseAgent,
        task: TaskDefinition,
        run_metadata: RunMetadata,
        reset_state: bool = True,
    ) -> RunResult:
        session = self._internal_session()
        if reset_state:
            session.post(f"{self.base_url}/api/internal/reset", timeout=15).raise_for_status()
            task = self.fetch_tasks()[task.task_id]
        agent.warm_up()
        suite_snapshot_hash = self._build_suite_snapshot_hash(task.suite)

        requested_run_id = run_metadata.run_id
        actual_run_id, run_dir = self._allocate_run_directory(run_metadata.task_id, requested_run_id)
        screenshots_dir = run_dir / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        actions_path = run_dir / "actions.jsonl"
        metadata_path = run_dir / "metadata.json"
        metrics_path = run_dir / "metrics.json"
        final_state_path = run_dir / "final-state.json"
        gpu_csv_path = run_dir / "gpu.csv"
        self._pending_native_select = None

        metadata_payload = self._build_metadata_payload(
            run_metadata=run_metadata,
            actual_run_id=actual_run_id,
            requested_run_id=requested_run_id,
            run_dir=run_dir,
            task=task,
            suite_snapshot_hash=suite_snapshot_hash,
        )
        metadata_path.write_text(json.dumps(metadata_payload, indent=2), encoding="utf-8")

        answer: str | None = None
        final_validation: ValidationResult | None = None
        invalid_actions = 0
        protocol_errors = 0
        executor_errors = 0
        action_errors: list[str] = []
        substantive_actions = 0
        started_at = time.perf_counter()
        agent_task = AgentTaskContext.from_task_definition(task)
        step_timings: list[StepTiming] = []
        resource_monitor = ResourceMonitor()
        resource_monitor.start()

        try:
            with launch_browser(self.browser_config) as (_, _, _, page):
                page_load_started = time.perf_counter()
                page.goto(f"{self.base_url}{task.start_url}", wait_until="domcontentloaded", timeout=30_000)
                initial_page_load_ms = round((time.perf_counter() - page_load_started) * 1000, 2)
                for step_index in range(task.max_steps):
                    step_started = time.perf_counter()
                    timing = StepTiming()
                    screenshot_path = screenshots_dir / f"step-{step_index:02d}.png"

                    screenshot_started = time.perf_counter()
                    page.screenshot(path=str(screenshot_path))
                    timing.screenshot_ms = round((time.perf_counter() - screenshot_started) * 1000, 2)

                    state = {
                        "current_url": page.url,
                        "title": page.title(),
                        "viewport": page.viewport_size,
                    }

                    decision_started = time.perf_counter()
                    action = agent.decide_next_action(agent_task, str(screenshot_path), step_index, state)
                    timing.decision_ms = round((time.perf_counter() - decision_started) * 1000, 2)
                    if self._is_protocol_error_action(action):
                        protocol_errors += 1

                    if action.action_type == ActionType.ANSWER:
                        answer = action.text or ""
                        validation_started = time.perf_counter()
                        final_validation = self._validate(session, task.task_id, page.url, answer)
                        timing.validation_ms = round((time.perf_counter() - validation_started) * 1000, 2)
                        timing.step_total_ms = round((time.perf_counter() - step_started) * 1000, 2)
                        step_timings.append(timing)
                        self._record_action(
                            actions_path,
                            step_index,
                            action,
                            state,
                            outcome="answered",
                            timing=timing,
                        )
                        break

                    try:
                        action_started = time.perf_counter()
                        self._execute_action(page, action)
                        timing.action_ms = round((time.perf_counter() - action_started) * 1000, 2)
                        validation_started = time.perf_counter()
                        final_validation = self._validate(session, task.task_id, page.url, answer)
                        timing.validation_ms = round((time.perf_counter() - validation_started) * 1000, 2)
                        timing.step_total_ms = round((time.perf_counter() - step_started) * 1000, 2)
                        step_timings.append(timing)
                        if action.action_type != ActionType.WAIT:
                            substantive_actions += 1
                        self._record_action(
                            actions_path,
                            step_index,
                            action,
                            state,
                            outcome="executed",
                            timing=timing,
                        )
                    except (PlaywrightError, ValueError) as exc:
                        invalid_actions += 1
                        executor_errors += 1
                        error_message = f"{action.action_type}: {exc}"
                        action_errors.append(error_message)
                        timing.step_total_ms = round((time.perf_counter() - step_started) * 1000, 2)
                        step_timings.append(timing)
                        self._record_action(
                            actions_path,
                            step_index,
                            action,
                            state,
                            outcome="invalid",
                            error=error_message,
                            timing=timing,
                        )
                        if invalid_actions >= 3:
                            validation_started = time.perf_counter()
                            final_validation = self._validate(session, task.task_id, page.url, answer)
                            timing.validation_ms = round((time.perf_counter() - validation_started) * 1000, 2)
                            break
                        continue

                    if final_validation.success and not task.requires_answer:
                        break
                else:
                    validation_started = time.perf_counter()
                    final_validation = final_validation or self._validate(session, task.task_id, page.url, answer)
                    trailing_validation_ms = round((time.perf_counter() - validation_started) * 1000, 2)
                    if step_timings:
                        step_timings[-1].validation_ms = trailing_validation_ms

                duration_seconds = round(time.perf_counter() - started_at, 3)
                resource_monitor.stop()
                resource_summary = resource_monitor.summary()
                resource_monitor.write_csv(gpu_csv_path)

                average_action_latency_ms = (
                    round(
                        sum(timing.action_ms + timing.validation_ms for timing in step_timings) / len(step_timings),
                        2,
                    )
                    if step_timings
                    else None
                )
                task_success = final_validation.success
                semantic_success = self._compute_semantic_success(task=task, answer=answer, validation=final_validation)
                protocol_error = protocol_errors > 0
                executor_error = executor_errors > 0
                model_error = (not semantic_success) and (substantive_actions > 0 or answer is not None)

                result = RunResult(
                    success=task_success,
                    task_success=task_success,
                    semantic_success=semantic_success,
                    protocol_error=protocol_error,
                    executor_error=executor_error,
                    model_error=model_error,
                    task_id=task.task_id,
                    run_id=actual_run_id,
                    requested_run_id=requested_run_id,
                    artifact_dir=str(run_dir),
                    final_url=page.url,
                    steps_executed=step_index + 1,
                    answer=answer,
                    invalid_actions=invalid_actions,
                    recovery_actions=invalid_actions if invalid_actions and final_validation.success else 0,
                    protocol_errors=protocol_errors,
                    executor_errors=executor_errors,
                    failure_reason=None if final_validation.success else (action_errors[-1] if action_errors else "validation_failed"),
                    action_errors=action_errors,
                    average_action_latency_ms=average_action_latency_ms,
                    duration_seconds=duration_seconds,
                    peak_ram_mb=resource_summary["peak_ram_mb"],
                    peak_vram_mb=resource_summary["peak_vram_mb"],
                    gpu_utilization_average=resource_summary["gpu_utilization_average"],
                    gpu_utilization_peak=resource_summary["gpu_utilization_peak"],
                    validation=final_validation,
                )

                final_state_payload = {
                    "task_id": task.task_id,
                    "run_id": actual_run_id,
                    "requested_run_id": requested_run_id,
                    "artifact_dir": str(run_dir),
                    "final_url": page.url,
                    "title": page.title(),
                    "answer": answer,
                    "validation": final_validation.model_dump(mode="json"),
                    "journey": {
                        "steps_executed": step_index + 1,
                    },
                }
                final_state_path.write_text(json.dumps(final_state_payload, indent=2), encoding="utf-8")

                metrics_payload = {
                    "task_id": task.task_id,
                    "run_id": actual_run_id,
                    "requested_run_id": requested_run_id,
                    "artifact_dir": str(run_dir),
                    "success": result.success,
                    "task_success": result.task_success,
                    "semantic_success": result.semantic_success,
                    "protocol_error": result.protocol_error,
                    "executor_error": result.executor_error,
                    "model_error": result.model_error,
                    "steps_executed": result.steps_executed,
                    "invalid_actions": invalid_actions,
                    "recovery_actions": result.recovery_actions,
                    "protocol_errors": protocol_errors,
                    "executor_errors": executor_errors,
                    "duration_seconds": duration_seconds,
                    "average_action_latency_ms": average_action_latency_ms,
                    "initial_page_load_ms": initial_page_load_ms,
                    "peak_ram_mb": resource_summary["peak_ram_mb"],
                    "peak_vram_mb": resource_summary["peak_vram_mb"],
                    "gpu_utilization_average": resource_summary["gpu_utilization_average"],
                    "gpu_utilization_peak": resource_summary["gpu_utilization_peak"],
                    "gpu_temperature_peak": resource_summary["gpu_temperature_peak"],
                    "gpu_power_peak_watts": resource_summary["gpu_power_peak_watts"],
                    "answer": answer,
                    "final_url": page.url,
                    "failure_reason": result.failure_reason,
                    "step_timings": [timing.model_dump(mode="json") for timing in step_timings],
                }
                metrics_path.write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")
                return result
        finally:
            if resource_monitor._thread is not None:
                resource_monitor.stop()

    def _execute_action(self, page: Any, action: AgentAction) -> None:
        if action.action_type == ActionType.CLICK:
            if action.target:
                self._pending_native_select = None
                page.locator(action.target).first.click(
                    timeout=15_000,
                    button=str(action.metadata.get("button", "left")),
                    click_count=int(action.metadata.get("click_count", 1)),
                )
            elif action.x is not None and action.y is not None:
                if self._try_select_native_option(page, action.x, action.y):
                    return
                select_context = self._detect_native_select_context(page, action.x, action.y)
                page.mouse.click(
                    action.x,
                    action.y,
                    button=str(action.metadata.get("button", "left")),
                    click_count=int(action.metadata.get("click_count", 1)),
                )
                page.wait_for_timeout(150)
                focused_context = self._detect_focused_native_select_context(page)
                self._pending_native_select = self._with_select_anchor(
                    select_context or focused_context,
                    action.x,
                    action.y,
                )
            else:
                raise ValueError("click requires either target or x/y coordinates")
        elif action.action_type == ActionType.MOUSE_MOVE:
            self._pending_native_select = None
            if action.x is None or action.y is None:
                raise ValueError("mouse_move requires x/y coordinates")
            page.mouse.move(action.x, action.y)
        elif action.action_type == ActionType.TYPE:
            self._pending_native_select = None
            if action.target:
                page.locator(action.target).first.fill(action.text or "", timeout=15_000)
            elif action.x is not None and action.y is not None:
                page.mouse.click(action.x, action.y)
                if action.metadata.get("delete_existing_text"):
                    page.keyboard.press("Control+A")
                    page.keyboard.press("Delete")
                page.keyboard.insert_text(action.text or "")
                if action.metadata.get("press_enter"):
                    page.keyboard.press("Enter")
            elif action.text is not None:
                page.keyboard.insert_text(action.text)
                if action.metadata.get("press_enter"):
                    page.keyboard.press("Enter")
            else:
                raise ValueError("type requires a target, x/y coordinates, or plain text on the current focus")
        elif action.action_type == ActionType.SELECT:
            self._pending_native_select = None
            page.locator(action.target).first.select_option(label=action.text or "", timeout=15_000)
        elif action.action_type == ActionType.SCROLL:
            self._pending_native_select = None
            page.mouse.wheel(0, action.delta_y or 600)
            page.wait_for_timeout(300)
        elif action.action_type == ActionType.KEYPRESS:
            self._pending_native_select = None
            key_sequence = action.metadata.get("key_sequence") or []
            if key_sequence:
                for key in key_sequence:
                    page.keyboard.press(str(key))
            else:
                page.keyboard.press(action.key or "Enter")
        elif action.action_type == ActionType.WAIT:
            page.wait_for_timeout(int(action.metadata.get("milliseconds", 800)))
        elif action.action_type == ActionType.NAVIGATE:
            self._pending_native_select = None
            url = action.text or action.target
            if not url:
                raise ValueError("navigate requires a target URL")
            page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        elif action.action_type == ActionType.BACK:
            self._pending_native_select = None
            page.go_back(wait_until="domcontentloaded", timeout=30_000)
        else:
            raise ValueError(f"Unsupported action type for execution: {action.action_type}")

    def _allocate_run_directory(self, task_id: str, requested_run_id: str) -> tuple[str, Path]:
        task_root = self.artifacts_root / task_id
        task_root.mkdir(parents=True, exist_ok=True)
        candidate = task_root / requested_run_id
        if not candidate.exists():
            return requested_run_id, candidate
        suffix = 2
        while True:
            actual_run_id = f"{requested_run_id}-{suffix}"
            candidate = task_root / actual_run_id
            if not candidate.exists():
                return actual_run_id, candidate
            suffix += 1

    def _build_metadata_payload(
        self,
        run_metadata: RunMetadata,
        actual_run_id: str,
        requested_run_id: str,
        run_dir: Path,
        task: TaskDefinition,
        suite_snapshot_hash: str,
    ) -> dict[str, Any]:
        git_dirty, git_diff_hash = _read_git_dirty_state()
        metadata = run_metadata.model_copy(
            update={
                "run_id": actual_run_id,
                "suite": run_metadata.suite or task.suite,
                "benchmark_git_sha": run_metadata.benchmark_git_sha or _read_git_sha(),
                "benchmark_git_dirty": (
                    run_metadata.benchmark_git_dirty
                    if run_metadata.benchmark_git_dirty is not None
                    else git_dirty
                ),
                "benchmark_git_diff_hash": run_metadata.benchmark_git_diff_hash or git_diff_hash,
                "task_snapshot_hash": run_metadata.task_snapshot_hash or suite_snapshot_hash,
                "seed_data_hash": run_metadata.seed_data_hash or _stable_hash(clone_seed_data()),
                "environment_inventory_hash": (
                    run_metadata.environment_inventory_hash
                    or _read_file_hash(run_metadata.environment_inventory_path)
                ),
            }
        )
        payload = metadata.model_dump(mode="json")
        payload["requested_run_id"] = requested_run_id
        payload["artifact_dir"] = str(run_dir)
        return payload

    def _build_suite_snapshot_hash(self, suite: str) -> str:
        tasks = self.fetch_tasks()
        suite_snapshot = {
            task_id: task.model_dump(mode="json")
            for task_id, task in tasks.items()
            if task.suite == suite
        }
        return _stable_hash(suite_snapshot)

    def _compute_semantic_success(
        self,
        task: TaskDefinition,
        answer: str | None,
        validation: ValidationResult,
    ) -> bool:
        if validation.success:
            return True
        normalized_answer = _normalize_answer(answer)
        if task.task_id == "t4-pending-highest":
            accepted = {
                str(task.private_context["highest_order_id"]),
                task.private_context["highest_total"],
                task.private_context["highest_total"].replace(".", ","),
            }
            return normalized_answer in accepted
        if task.task_id == "t5-customer-recent-order":
            return normalized_answer == str(task.private_context["recent_order_id"])
        return False

    def _is_protocol_error_action(self, action: AgentAction) -> bool:
        metadata = action.metadata or {}
        return any(key in metadata for key in ("parse_error", "protocol_error", "unsupported_action"))

    def _detect_native_select_context(self, page: Any, x: float, y: float) -> dict[str, Any] | None:
        context = page.evaluate(
            """
            ({ x, y }) => {
              const element = document.elementFromPoint(x, y);
              const select = element instanceof HTMLSelectElement ? element : element?.closest?.('select');
              if (!(select instanceof HTMLSelectElement)) {
                return null;
              }
              const testId = select.getAttribute('data-testid');
              const name = select.getAttribute('name');
              const id = select.getAttribute('id');
              const selector = testId
                ? `select[data-testid="${testId}"]`
                : name
                  ? `select[name="${name}"]`
                  : id
                    ? `select[id="${id}"]`
                    : null;
              if (!selector) {
                return null;
              }
              const rect = select.getBoundingClientRect();
              return {
                selector,
                bbox: {
                  x: rect.x,
                  y: rect.y,
                  width: rect.width,
                  height: rect.height
                },
                options: Array.from(select.options).map((option) => option.text.trim()).filter(Boolean)
              };
            }
            """,
            {"x": x, "y": y},
        )
        if not context or not context.get("options"):
            return None
        bbox = context["bbox"]
        context["option_height"] = max(float(bbox["height"]) - 12.0, 28.0)
        return context

    def _try_select_native_option(self, page: Any, x: float, y: float) -> bool:
        context = self._pending_native_select or self._detect_focused_native_select_context(page)
        if context is None:
            return False
        if "anchor_y" not in context:
            bbox = context["bbox"]
            context = self._with_select_anchor(
                context,
                float(bbox["x"]) + (float(bbox["width"]) / 2.0),
                float(bbox["y"]) + (float(bbox["height"]) / 2.0),
            )
        bbox = context["bbox"]
        options = context["options"]
        option_height = float(context["option_height"])
        anchor_y = float(context["anchor_y"])
        popup_top = anchor_y + (option_height / 2.0)
        popup_bottom = popup_top + option_height * len(options)
        if float(bbox["y"]) <= y <= float(bbox["y"]) + float(bbox["height"]):
            self._pending_native_select = None
            return False
        if popup_top <= y <= popup_bottom:
            option_index = int((y - anchor_y) // option_height) - 1
            option_index = max(0, min(option_index, len(options) - 1))
            page.locator(context["selector"]).first.select_option(label=options[option_index], timeout=15_000)
            page.wait_for_timeout(150)
            page.keyboard.press("Escape")
            self._pending_native_select = None
            return True
        if y < float(bbox["y"]) or y > popup_bottom + option_height:
            self._pending_native_select = None
        return False

    def _detect_focused_native_select_context(self, page: Any) -> dict[str, Any] | None:
        context = page.evaluate(
            """
            () => {
              const select = document.activeElement instanceof HTMLSelectElement ? document.activeElement : null;
              if (!(select instanceof HTMLSelectElement)) {
                return null;
              }
              const testId = select.getAttribute('data-testid');
              const name = select.getAttribute('name');
              const id = select.getAttribute('id');
              const selector = testId
                ? `select[data-testid="${testId}"]`
                : name
                  ? `select[name="${name}"]`
                  : id
                    ? `select[id="${id}"]`
                    : null;
              if (!selector) {
                return null;
              }
              const rect = select.getBoundingClientRect();
              return {
                selector,
                bbox: {
                  x: rect.x,
                  y: rect.y,
                  width: rect.width,
                  height: rect.height
                },
                options: Array.from(select.options).map((option) => option.text.trim()).filter(Boolean)
              };
            }
            """,
        )
        if not context or not context.get("options"):
            return None
        bbox = context["bbox"]
        context["option_height"] = max(float(bbox["height"]) - 12.0, 28.0)
        return context

    def _with_select_anchor(self, context: dict[str, Any] | None, x: float, y: float) -> dict[str, Any] | None:
        if context is None:
            return None
        context["anchor_x"] = x
        context["anchor_y"] = y
        return context

    def _validate(
        self,
        session: requests.Session,
        task_id: str,
        current_url: str,
        answer: str | None,
    ) -> ValidationResult:
        response = session.post(
            f"{self.base_url}/api/internal/validate/{task_id}",
            json={
                "current_path": current_url.replace(self.base_url, ""),
                "answer": answer,
            },
            timeout=15,
        )
        response.raise_for_status()
        return ValidationResult.model_validate(response.json())

    def _internal_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update({"x-benchmark-token": self.internal_token})
        return session

    def _record_action(
        self,
        actions_path: Path,
        step_index: int,
        action: AgentAction,
        state: dict[str, Any],
        outcome: str,
        error: str | None = None,
        timing: StepTiming | None = None,
    ) -> None:
        payload = {
            "step_index": step_index,
            "timestamp": time.time(),
            "action": action.model_dump(mode="json"),
            "state": state,
            "outcome": outcome,
        }
        if error:
            payload["error"] = error
        if timing is not None:
            payload["timing"] = timing.model_dump(mode="json")
        with actions_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _normalize_answer(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^0-9.,]", "", value.strip().lower())


def _stable_hash(payload: Any) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def _read_git_sha() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except Exception:
        return None
    return result.stdout.strip() or None


def _read_git_dirty_state() -> tuple[bool | None, str | None]:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain=v1", "-uall"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except Exception:
        return None, None
    status_output = result.stdout
    is_dirty = bool(status_output.strip())
    diff_hash = _stable_hash(status_output) if is_dirty else None
    return is_dirty, diff_hash


def _read_file_hash(path_value: str | None) -> str | None:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]

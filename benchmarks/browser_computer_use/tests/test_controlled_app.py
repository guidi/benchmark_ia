import json
from pathlib import Path

from fastapi.testclient import TestClient

from benchmark_cua.agents.scripted import ScriptedAgent
from benchmark_cua.benchmark.runner import ControlledTaskRunner
from benchmark_cua.browser.session import BrowserConfig, launch_browser
from benchmark_cua.schemas import AgentAction, RunMetadata
from benchmark_cua.site.app import create_app
from benchmark_cua.site.server import managed_server


INTERNAL_TOKEN = "test-token"
client = TestClient(create_app(internal_token=INTERNAL_TOKEN))


def _internal_headers() -> dict[str, str]:
    return {"x-benchmark-token": INTERNAL_TOKEN}


def test_health_and_internal_api_requires_token() -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    unauthorized = client.get("/api/internal/tasks")
    assert unauthorized.status_code == 401

    authorized = client.get("/api/internal/tasks", headers=_internal_headers())
    assert authorized.status_code == 200
    payload = authorized.json()
    assert len(payload) == 10
    assert all("objective" in task for task in payload)


def test_customer_creation_and_validation_use_dynamic_task_context() -> None:
    reset = client.post("/api/internal/reset", headers=_internal_headers())
    assert reset.status_code == 200

    tasks = client.get("/api/internal/tasks", headers=_internal_headers()).json()
    task = next(item for item in tasks if item["task_id"] == "t2-create-customer")

    created = client.post(
        "/customers/create",
        data={
            "name": task["private_context"]["name"],
            "email": task["private_context"]["email"],
            "city": task["private_context"]["city"],
        },
        follow_redirects=True,
    )
    assert created.status_code == 200

    validation = client.post(
        "/api/internal/validate/t2-create-customer",
        json={"current_path": "/customers?created=1"},
        headers=_internal_headers(),
    )
    assert validation.status_code == 200
    assert validation.json()["success"] is True


def test_runner_recovers_from_invalid_action_and_persists_metrics(tmp_path: Path) -> None:
    artifacts_root = tmp_path / "artifacts"
    with managed_server() as handle:
        runner = ControlledTaskRunner(
            base_url=handle.base_url,
            internal_token=handle.internal_token,
            artifacts_root=artifacts_root,
        )
        task = runner.reset_and_fetch_tasks()["t1-product-navigation"]
        product_slug = task.private_context["product_slug"]
        agent = ScriptedAgent(
            model_id="scripted-invalid-then-valid",
            actions=[
                AgentAction(action_type="click", target='a[data-testid="does-not-exist"]'),
                AgentAction(action_type="click", target='a[data-testid="nav-products"]'),
                AgentAction(action_type="click", target=f'a[data-testid="product-link-{product_slug}"]'),
            ],
        )
        result = runner.run_task(
            agent=agent,
            task=task,
            run_metadata=RunMetadata(
                run_id="invalid-then-valid",
                task_id=task.task_id,
                model=agent.model_id,
            ),
            reset_state=False,
        )

    assert result.success is True
    assert result.task_success is True
    assert result.semantic_success is True
    assert result.protocol_error is False
    assert result.executor_error is True
    assert result.model_error is False
    assert result.invalid_actions == 1
    assert result.recovery_actions == 1
    assert result.executor_errors == 1
    assert result.failure_reason is None
    run_dir = artifacts_root / task.task_id / result.run_id
    assert result.requested_run_id == "invalid-then-valid"
    assert Path(result.artifact_dir) == run_dir
    assert (run_dir / "actions.jsonl").exists()
    assert (run_dir / "metadata.json").exists()
    assert (run_dir / "metrics.json").exists()
    assert (run_dir / "final-state.json").exists()
    assert (run_dir / "gpu.csv").exists()
    metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["suite"] == task.suite
    assert metadata["benchmark_git_sha"]
    assert metadata["task_snapshot_hash"]
    assert metadata["seed_data_hash"]


def test_runner_uses_suite_wide_task_snapshot_hash(tmp_path: Path) -> None:
    artifacts_root = tmp_path / "artifacts"
    with managed_server() as handle:
        runner = ControlledTaskRunner(
            base_url=handle.base_url,
            internal_token=handle.internal_token,
            artifacts_root=artifacts_root,
        )
        tasks = runner.reset_and_fetch_tasks()
        t1 = tasks["t1-product-navigation"]
        t2 = tasks["t2-create-customer"]
        t1_agent = ScriptedAgent(
            model_id="scripted-t1",
            actions=[
                AgentAction(action_type="click", target='a[data-testid="nav-products"]'),
                AgentAction(action_type="click", target=f'a[data-testid="product-link-{t1.private_context["product_slug"]}"]'),
            ],
        )
        t2_agent = ScriptedAgent(
            model_id="scripted-t2",
            actions=[
                AgentAction(action_type="click", target='button[data-testid="open-customer-modal"]'),
                AgentAction(action_type="type", target='input[data-testid="customer-name-input"]', text=t2.private_context["name"]),
                AgentAction(action_type="type", target='input[data-testid="customer-email-input"]', text=t2.private_context["email"]),
                AgentAction(action_type="type", target='input[data-testid="customer-city-input"]', text=t2.private_context["city"]),
                AgentAction(action_type="click", target='button[data-testid="submit-customer-form"]'),
            ],
        )
        result_t1 = runner.run_task(
            agent=t1_agent,
            task=t1,
            run_metadata=RunMetadata(run_id="suite-hash-t1", task_id=t1.task_id, model=t1_agent.model_id),
            reset_state=False,
        )
        result_t2 = runner.run_task(
            agent=t2_agent,
            task=t2,
            run_metadata=RunMetadata(run_id="suite-hash-t2", task_id=t2.task_id, model=t2_agent.model_id),
            reset_state=True,
        )

    metadata_t1 = json.loads((Path(result_t1.artifact_dir) / "metadata.json").read_text(encoding="utf-8"))
    metadata_t2 = json.loads((Path(result_t2.artifact_dir) / "metadata.json").read_text(encoding="utf-8"))
    assert metadata_t1["task_snapshot_hash"] == metadata_t2["task_snapshot_hash"]


def test_runner_allocates_unique_run_directory_when_requested_run_id_repeats(tmp_path: Path) -> None:
    artifacts_root = tmp_path / "artifacts"
    with managed_server() as handle:
        runner = ControlledTaskRunner(
            base_url=handle.base_url,
            internal_token=handle.internal_token,
            artifacts_root=artifacts_root,
        )
        task = runner.reset_and_fetch_tasks()["t1-product-navigation"]
        product_slug = task.private_context["product_slug"]
        agent = ScriptedAgent(
            model_id="scripted-unique-runs",
            actions=[
                AgentAction(action_type="click", target='a[data-testid="nav-products"]'),
                AgentAction(action_type="click", target=f'a[data-testid="product-link-{product_slug}"]'),
            ],
        )
        first = runner.run_task(
            agent=agent,
            task=task,
            run_metadata=RunMetadata(run_id="repeated-run", task_id=task.task_id, model=agent.model_id),
            reset_state=False,
        )
        second = runner.run_task(
            agent=agent,
            task=task,
            run_metadata=RunMetadata(run_id="repeated-run", task_id=task.task_id, model=agent.model_id),
            reset_state=True,
        )

    assert first.run_id == "repeated-run"
    assert second.run_id == "repeated-run-2"
    assert first.requested_run_id == second.requested_run_id == "repeated-run"
    assert (artifacts_root / task.task_id / "repeated-run" / "screenshots" / "step-00.png").exists()
    assert (artifacts_root / task.task_id / "repeated-run-2" / "screenshots" / "step-00.png").exists()


def test_runner_marks_protocol_errors_even_when_task_recovers(tmp_path: Path) -> None:
    artifacts_root = tmp_path / "artifacts"
    with managed_server() as handle:
        runner = ControlledTaskRunner(
            base_url=handle.base_url,
            internal_token=handle.internal_token,
            artifacts_root=artifacts_root,
        )
        task = runner.reset_and_fetch_tasks()["t1-product-navigation"]
        product_slug = task.private_context["product_slug"]
        agent = ScriptedAgent(
            model_id="scripted-protocol-recovery",
            actions=[
                AgentAction(action_type="wait", metadata={"milliseconds": 1, "parse_error": "malformed tool call", "protocol_error": "response_parse_failed"}),
                AgentAction(action_type="click", target='a[data-testid="nav-products"]'),
                AgentAction(action_type="click", target=f'a[data-testid="product-link-{product_slug}"]'),
            ],
        )
        result = runner.run_task(
            agent=agent,
            task=task,
            run_metadata=RunMetadata(run_id="protocol-then-success", task_id=task.task_id, model=agent.model_id),
            reset_state=False,
        )

    assert result.success is True
    assert result.protocol_error is True
    assert result.protocol_errors == 1
    assert result.executor_error is False
    assert result.model_error is False


def test_native_select_coordinate_clicks_change_filter_state(tmp_path: Path) -> None:
    artifacts_root = tmp_path / "artifacts"
    browser_config = BrowserConfig()
    with managed_server() as handle:
        runner = ControlledTaskRunner(
            base_url=handle.base_url,
            internal_token=handle.internal_token,
            artifacts_root=artifacts_root,
            browser_config=browser_config,
        )
        task = runner.reset_and_fetch_tasks()["t4-pending-highest"]
        with launch_browser(browser_config) as (_, _, _, page):
            page.goto(f"{handle.base_url}{task.start_url}", wait_until="domcontentloaded", timeout=30_000)
            select_box = page.locator('select[data-testid="orders-status-filter"]').bounding_box()
        assert select_box is not None
        options = ["Todos", "Pendente", "Concluido", "Cancelado"]
        option_index = options.index(task.private_context["status"])
        option_height = max(select_box["height"] - 12.0, 28.0)
        open_x = select_box["x"] + (select_box["width"] / 2.0)
        open_y = select_box["y"] + (select_box["height"] / 2.0)
        option_x = open_x
        option_y = open_y + (option_height * (option_index + 1))
        agent = ScriptedAgent(
            model_id="scripted-native-select",
            actions=[
                AgentAction(action_type="click", x=open_x, y=open_y),
                AgentAction(action_type="click", x=option_x, y=option_y),
                AgentAction(action_type="click", target='button[type="submit"]'),
                AgentAction(action_type="answer", text=str(task.private_context["highest_order_id"])),
            ],
        )
        result = runner.run_task(
            agent=agent,
            task=task,
            run_metadata=RunMetadata(run_id="native-select", task_id=task.task_id, model=agent.model_id),
            reset_state=False,
        )

    assert result.success is True
    assert f'status={task.private_context["status"]}' in result.final_url


def test_answer_validation_requires_correct_filtered_context() -> None:
    client.post("/api/internal/reset", headers=_internal_headers())
    tasks = client.get("/api/internal/tasks", headers=_internal_headers()).json()
    task = next(item for item in tasks if item["task_id"] == "t4-pending-highest")

    good = client.post(
        "/api/internal/validate/t4-pending-highest",
        json={
            "current_path": f'/orders?status={task["private_context"]["status"]}&q=',
            "answer": str(task["private_context"]["highest_order_id"]),
        },
        headers=_internal_headers(),
    )
    assert good.status_code == 200
    assert good.json()["success"] is True

    bad = client.post(
        "/api/internal/validate/t4-pending-highest",
        json={
            "current_path": "/orders?status=Todos&q=",
            "answer": str(task["private_context"]["highest_order_id"]),
        },
        headers=_internal_headers(),
    )
    assert bad.status_code == 200
    assert bad.json()["success"] is False


def test_recovery_flow_requires_error_then_success() -> None:
    client.post("/api/internal/reset", headers=_internal_headers())
    tasks = client.get("/api/internal/tasks", headers=_internal_headers()).json()
    task = next(item for item in tasks if item["task_id"] == "t8-recovery-error")

    early_success = client.post(
        "/recovery-lab/submit",
        data={"code": task["private_context"]["recovery_code"]},
        follow_redirects=False,
    )
    assert early_success.status_code == 303

    premature_validation = client.post(
        "/api/internal/validate/t8-recovery-error",
        json={"current_path": "/recovery-lab?success=1"},
        headers=_internal_headers(),
    )
    assert premature_validation.status_code == 200
    assert premature_validation.json()["success"] is False

    client.post("/recovery-lab/quick", follow_redirects=False)
    final_success = client.post(
        "/recovery-lab/submit",
        data={"code": task["private_context"]["recovery_code"]},
        follow_redirects=False,
    )
    assert final_success.status_code == 303

    final_validation = client.post(
        "/api/internal/validate/t8-recovery-error",
        json={"current_path": "/recovery-lab?success=1"},
        headers=_internal_headers(),
    )
    assert final_validation.status_code == 200
    assert final_validation.json()["success"] is True

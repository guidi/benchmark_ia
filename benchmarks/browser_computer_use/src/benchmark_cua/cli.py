from __future__ import annotations

import json
from pathlib import Path

import typer
import uvicorn

from benchmark_cua.agents.fara_endpoint import FaraEndpointAgent
from benchmark_cua.agents.scripted import ScriptedAgent
from benchmark_cua.benchmark.runner import ControlledTaskRunner

from benchmark_cua.browser.session import browser_smoke_test
from benchmark_cua.metrics.inventory import write_environment_inventory
from benchmark_cua.reporting import consolidate_campaign
from benchmark_cua.schemas import AgentAction, RunMetadata, TaskDefinition
from benchmark_cua.site.app import create_app
from benchmark_cua.site.server import managed_server

app = typer.Typer(no_args_is_help=True, help="Local browser/computer-use benchmark utilities.")


@app.command("inventory")
def inventory_command(
    output: Path = typer.Option(
        Path("artifacts/environment-inventory.json"),
        help="Path to write the collected environment inventory JSON.",
    ),
) -> None:
    written = write_environment_inventory(output)
    typer.echo(f"environment inventory written to {written}")


@app.command("browser-smoke")
def browser_smoke_command(
    channel: str = typer.Option("chrome", help="Browser channel to launch."),
    url: str = typer.Option("https://example.com", help="URL to open in the smoke test."),
) -> None:
    title = browser_smoke_test(channel=channel, url=url)
    typer.echo(f"browser smoke test ok: title={title}")


@app.command("serve-controlled-app")
def serve_controlled_app_command(
    host: str = typer.Option("127.0.0.1", help="Host to bind the controlled benchmark app."),
    port: int = typer.Option(8000, help="Port to bind the controlled benchmark app."),
    internal_token: str = typer.Option("local-dev-token", help="Token required for internal benchmark endpoints."),
) -> None:
    uvicorn.run(create_app(internal_token=internal_token), host=host, port=port)


@app.command("controlled-smoke")
def controlled_smoke_command(
    task_id: str = typer.Option("t1-product-navigation", help="Controlled task id to smoke test."),
    run_id: str = typer.Option("smoke-run", help="Requested artifact run id. A numeric suffix is added automatically if it already exists."),
) -> None:
    with managed_server() as handle:
        runner = ControlledTaskRunner(base_url=handle.base_url, internal_token=handle.internal_token)
        tasks = runner.reset_and_fetch_tasks()
        task = tasks.get(task_id)
        if task is None:
            raise typer.BadParameter(f"Unknown task: {task_id}")
        actions = _build_smoke_actions(task)
        agent = ScriptedAgent(model_id="scripted-smoke", actions=actions)
        result = runner.run_task(
            agent=agent,
            task=task,
            run_metadata=RunMetadata(run_id=run_id, task_id=task.task_id, model=agent.model_id),
            reset_state=False,
        )
    typer.echo(json.dumps(result.model_dump(mode="json"), indent=2))


@app.command("controlled-endpoint-run")
def controlled_endpoint_run_command(
    task_id: str = typer.Option("t1-product-navigation", help="Controlled task id to execute."),
    endpoint_url: str = typer.Option(..., help="OpenAI-compatible multimodal endpoint base URL."),
    model: str = typer.Option(..., help="Remote model identifier to send in chat completions."),
    api_key: str = typer.Option("local-dev-token", help="API key for the remote endpoint."),
    campaign_id: str | None = typer.Option(None, help="Campaign identifier used to group comparable runs."),
    suite_version: str | None = typer.Option(None, help="Explicit suite version label, such as suite-a-controlled-v1."),
    model_checkpoint: str | None = typer.Option(None, help="Exact checkpoint identifier under test."),
    execution_class: str | None = typer.Option(None, help="Execution class, such as official/native, quantized, offload or inviavel."),
    quantization: str | None = typer.Option(None, help="Quantization label, when applicable."),
    runtime_label: str = typer.Option("openai-compatible-endpoint", help="Runtime label recorded in metadata."),
    runtime_version: str | None = typer.Option(None, help="Runtime version recorded in metadata."),
    offload_policy: str | None = typer.Option(None, help="Offload policy recorded in metadata."),
    endpoint_contract: str = typer.Option(
        "openai-chat-completions-multimodal-computer-use",
        help="Protocol contract expected from the endpoint.",
    ),
    environment_inventory: Path = typer.Option(
        Path("artifacts/environment-inventory.json"),
        help="Environment inventory JSON path associated with this campaign run.",
    ),
    notes: str | None = typer.Option(None, help="Free-form notes recorded in metadata."),
    max_history_messages: int = typer.Option(
        8,
        min=0,
        help="Number of prior user/assistant messages to keep. Low-context GGUF servers may require 0 or 2.",
    ),
    request_timeout_seconds: float = typer.Option(
        240.0,
        help="Per-request timeout for the model endpoint. Offload runs may require more than the default native/Q4 budget.",
    ),
    run_id: str = typer.Option(
        "endpoint-run",
        help="Requested artifact run id. A numeric suffix is added automatically if it already exists.",
    ),
) -> None:
    with managed_server() as handle:
        runner = ControlledTaskRunner(base_url=handle.base_url, internal_token=handle.internal_token)
        tasks = runner.reset_and_fetch_tasks()
        task = tasks.get(task_id)
        if task is None:
            raise typer.BadParameter(f"Unknown task: {task_id}")
        agent = FaraEndpointAgent(
            model_id=model,
            base_url=endpoint_url,
            api_key=api_key,
            max_history_messages=max_history_messages,
            request_timeout_seconds=request_timeout_seconds,
        )
        result = runner.run_task(
            agent=agent,
            task=task,
            run_metadata=RunMetadata(
                run_id=run_id,
                task_id=task.task_id,
                model=agent.model_id,
                suite_version=suite_version,
                campaign_id=campaign_id,
                model_checkpoint=model_checkpoint,
                execution_class=execution_class,
                quantization=quantization,
                runtime=runtime_label,
                runtime_version=runtime_version,
                offload_policy=offload_policy,
                endpoint_base_url=endpoint_url,
                endpoint_contract=endpoint_contract,
                environment_inventory_path=str(environment_inventory.resolve()),
                notes=notes,
            ),
            reset_state=False,
        )
    typer.echo(json.dumps(result.model_dump(mode="json"), indent=2))


@app.command("consolidate-campaign")
def consolidate_campaign_command(
    manifest: Path = typer.Option(..., help="Path to the campaign manifest YAML."),
    output_dir: Path = typer.Option(..., help="Directory where summary.json, results.csv and summary.md will be written."),
) -> None:
    written = consolidate_campaign(manifest_path=manifest, output_dir=output_dir)
    typer.echo(json.dumps({key: str(value) for key, value in written.items()}, indent=2))


def _build_smoke_actions(task: TaskDefinition) -> list[AgentAction]:
    if task.task_id == "t1-product-navigation":
        return [
            AgentAction(action_type="click", target='a[data-testid="nav-products"]'),
            AgentAction(action_type="click", target=f'a[data-testid="product-link-{task.private_context["product_slug"]}"]'),
        ]
    if task.task_id == "t2-create-customer":
        return [
            AgentAction(action_type="click", target='button[data-testid="open-customer-modal"]'),
            AgentAction(action_type="type", target='input[data-testid="customer-name-input"]', text=task.private_context["name"]),
            AgentAction(action_type="type", target='input[data-testid="customer-email-input"]', text=task.private_context["email"]),
            AgentAction(action_type="type", target='input[data-testid="customer-city-input"]', text=task.private_context["city"]),
            AgentAction(action_type="click", target='button[data-testid="submit-customer-form"]'),
        ]
    if task.task_id == "t3-open-order":
        target_order = str(task.private_context["order_id"])
        return [
            AgentAction(action_type="type", target='input[data-testid="orders-search-input"]', text=target_order),
            AgentAction(action_type="click", target='button[type="submit"]'),
            AgentAction(action_type="click", target=f'a[data-testid="order-link-{target_order}"]'),
        ]
    if task.task_id == "t4-pending-highest":
        return [
            AgentAction(action_type="select", target='select[data-testid="orders-status-filter"]', text=task.private_context["status"]),
            AgentAction(action_type="click", target='button[type="submit"]'),
            AgentAction(action_type="answer", text=str(task.private_context["highest_order_id"])),
        ]
    if task.task_id == "t5-customer-recent-order":
        return [
            AgentAction(action_type="click", target=f'a[data-testid="customer-orders-{task.private_context["customer_slug"]}"]'),
            AgentAction(action_type="answer", text=str(task.private_context["recent_order_id"])),
        ]
    if task.task_id == "t6-scroll-checkpoint":
        return [
            AgentAction(action_type="scroll", delta_y=1800),
            AgentAction(action_type="click", target='a[data-testid="scroll-final-link"]'),
        ]
    if task.task_id == "t7-modal-confirmation":
        return [
            AgentAction(action_type="click", target='button[data-testid="open-approval-modal"]'),
            AgentAction(action_type="select", target='select[data-testid="approval-choice-select"]', text=task.private_context["modal_choice"]),
            AgentAction(action_type="click", target='button[data-testid="confirm-approval-modal"]'),
        ]
    if task.task_id == "t8-recovery-error":
        return [
            AgentAction(action_type="click", target='button[data-testid="recovery-quick-submit"]'),
            AgentAction(action_type="type", target='input[data-testid="recovery-code-input"]', text=task.private_context["recovery_code"]),
            AgentAction(action_type="click", target='button[data-testid="recovery-submit"]'),
        ]
    if task.task_id == "t9-visual-ambiguity":
        return [
            AgentAction(action_type="click", target=f'a[data-testid="ambiguity-open-{task.private_context["report_slug"]}"]'),
        ]
    if task.task_id == "t10-long-journey":
        density_target = f'input[data-testid="journey-density-{task.private_context["density"]}"]'
        return [
            AgentAction(action_type="click", target='a[data-testid="journey-start-link"]'),
            AgentAction(action_type="select", target='select[data-testid="journey-team-select"]', text=task.private_context["team"]),
            AgentAction(action_type="click", target='button[data-testid="journey-profile-submit"]'),
            AgentAction(action_type="click", target='input[data-testid="journey-alerts-checkbox"]'),
            AgentAction(action_type="click", target=density_target),
            AgentAction(action_type="click", target='button[data-testid="journey-preferences-submit"]'),
            AgentAction(action_type="type", target='input[data-testid="journey-review-code-input"]', text=task.private_context["review_code"]),
            AgentAction(action_type="click", target='button[data-testid="journey-review-submit"]'),
            AgentAction(action_type="click", target='button[data-testid="journey-open-modal"]'),
            AgentAction(action_type="select", target='select[data-testid="journey-launch-window-select"]', text=task.private_context["launch_window"]),
            AgentAction(action_type="click", target='button[data-testid="journey-confirm-modal"]'),
            AgentAction(action_type="click", target='button[data-testid="journey-finish-submit"]'),
        ]
    raise typer.BadParameter(f"No scripted smoke is defined for task: {task.task_id}")


if __name__ == "__main__":
    app()

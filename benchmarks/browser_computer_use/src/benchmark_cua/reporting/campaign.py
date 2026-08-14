from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class CampaignRunSpec(BaseModel):
    task_id: str
    artifact_dir: str


class CampaignRouteSpec(BaseModel):
    route_id: str
    label: str
    model: str | None = None
    model_checkpoint: str | None = None
    execution_class: str | None = None
    runtime: str | None = None
    runtime_version: str | None = None
    quantization: str | None = None
    offload_policy: str | None = None
    endpoint_contract: str | None = None
    endpoint_base_url: str | None = None
    runs: list[CampaignRunSpec] = Field(default_factory=list)


class CampaignManifest(BaseModel):
    campaign_id: str
    benchmark: str = "browser_computer_use"
    suite_version: str
    task_ids: list[str]
    repetitions_per_task: int
    require_clean_worktree: bool = True
    routes: list[CampaignRouteSpec]
    notes: str | None = None


def consolidate_campaign(manifest_path: Path, output_dir: Path) -> dict[str, Path]:
    manifest = _load_manifest(manifest_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    route_summaries: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []

    for route in manifest.routes:
        _require_route_contract(route)
        expected_runs = len(manifest.task_ids) * manifest.repetitions_per_task
        if len(route.runs) != expected_runs:
            raise ValueError(
                f"Route {route.route_id} expected {expected_runs} runs, found {len(route.runs)}"
            )

        task_counts = {task_id: 0 for task_id in manifest.task_ids}
        route_rows: list[dict[str, Any]] = []
        for run in route.runs:
            if run.task_id not in task_counts:
                raise ValueError(f"Unexpected task_id in manifest: {run.task_id}")
            task_counts[run.task_id] += 1
            row = _load_run_row(manifest_path.parent, manifest, route, run)
            route_rows.append(row)
            rows.append(row)

        for task_id, count in task_counts.items():
            if count != manifest.repetitions_per_task:
                raise ValueError(
                    f"Route {route.route_id} expected {manifest.repetitions_per_task} runs for {task_id}, found {count}"
                )

        route_summaries.append(_summarize_route(manifest, route, route_rows))

    shared_audit = _validate_shared_audit_contract(manifest, rows)
    summary = {
        "campaign_id": manifest.campaign_id,
        "benchmark": manifest.benchmark,
        "suite_version": manifest.suite_version,
        "task_ids": manifest.task_ids,
        "repetitions_per_task": manifest.repetitions_per_task,
        "require_clean_worktree": manifest.require_clean_worktree,
        "shared_audit": shared_audit,
        "routes": route_summaries,
        "rows": rows,
    }

    summary_json = output_dir / "summary.json"
    results_csv = output_dir / "results.csv"
    summary_md = output_dir / "summary.md"

    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_rows_csv(results_csv, rows)
    summary_md.write_text(_render_markdown_summary(summary), encoding="utf-8")

    return {
        "summary_json": summary_json,
        "results_csv": results_csv,
        "summary_md": summary_md,
    }


def _load_manifest(path: Path) -> CampaignManifest:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return CampaignManifest.model_validate(payload)


def _load_run_row(
    manifest_root: Path,
    manifest: CampaignManifest,
    route: CampaignRouteSpec,
    run: CampaignRunSpec,
) -> dict[str, Any]:
    run_dir = _resolve_artifact_dir(manifest_root, Path(run.artifact_dir))
    metadata = _read_json(run_dir / "metadata.json")
    metrics = _read_json(run_dir / "metrics.json")
    final_state = _read_json(run_dir / "final-state.json")

    _require_audit_fields(metadata, run_dir)
    _validate_route_against_metadata(manifest, route, run, metadata)

    row = {
        "campaign_id": metadata["campaign_id"],
        "suite_version": metadata["suite_version"],
        "route_id": route.route_id,
        "route_label": route.label,
        "task_id": run.task_id,
        "run_id": metrics["run_id"],
        "artifact_dir": str(run_dir),
        "model": metadata["model"],
        "model_checkpoint": metadata["model_checkpoint"],
        "execution_class": metadata["execution_class"],
        "quantization": metadata.get("quantization"),
        "runtime": metadata["runtime"],
        "runtime_version": metadata["runtime_version"],
        "offload_policy": metadata.get("offload_policy"),
        "endpoint_contract": metadata["endpoint_contract"],
        "endpoint_base_url": metadata["endpoint_base_url"],
        "benchmark_git_sha": metadata["benchmark_git_sha"],
        "benchmark_git_dirty": bool(metadata["benchmark_git_dirty"]),
        "benchmark_git_diff_hash": metadata.get("benchmark_git_diff_hash"),
        "task_snapshot_hash": metadata["task_snapshot_hash"],
        "seed_data_hash": metadata["seed_data_hash"],
        "environment_inventory_path": metadata["environment_inventory_path"],
        "environment_inventory_hash": metadata["environment_inventory_hash"],
        "task_success": bool(metrics["task_success"]),
        "semantic_success": bool(metrics["semantic_success"]),
        "protocol_error": bool(metrics["protocol_error"]),
        "executor_error": bool(metrics["executor_error"]),
        "model_error": bool(metrics["model_error"]),
        "steps_executed": int(metrics["steps_executed"]),
        "duration_seconds": _optional_float(metrics.get("duration_seconds")),
        "peak_vram_mb": _optional_float(metrics.get("peak_vram_mb")),
        "failure_reason": metrics.get("failure_reason"),
        "final_url": final_state["final_url"],
    }
    return row


def _require_audit_fields(metadata: dict[str, Any], run_dir: Path) -> None:
    required = [
        "suite",
        "suite_version",
        "campaign_id",
        "model_checkpoint",
        "execution_class",
        "runtime",
        "runtime_version",
        "endpoint_base_url",
        "endpoint_contract",
        "benchmark_git_sha",
        "benchmark_git_dirty",
        "task_snapshot_hash",
        "seed_data_hash",
        "environment_inventory_path",
        "environment_inventory_hash",
    ]
    missing = [field for field in required if field not in metadata or metadata.get(field) in (None, "")]
    if missing:
        raise ValueError(f"Run {run_dir} is missing audit fields: {', '.join(missing)}")
    if bool(metadata.get("benchmark_git_dirty")) and not metadata.get("benchmark_git_diff_hash"):
        raise ValueError(f"Run {run_dir} is dirty but missing benchmark_git_diff_hash")


def _require_route_contract(route: CampaignRouteSpec) -> None:
    required_fields = [
        "model_checkpoint",
        "execution_class",
        "runtime",
        "runtime_version",
        "quantization",
        "offload_policy",
        "endpoint_contract",
        "endpoint_base_url",
    ]
    missing = [
        field
        for field in required_fields
        if _is_missing_contract_value(getattr(route, field, None))
    ]
    if missing:
        raise ValueError(
            f"Route {route.route_id} is missing required contract fields: {', '.join(missing)}"
        )


def _validate_route_against_metadata(
    manifest: CampaignManifest,
    route: CampaignRouteSpec,
    run: CampaignRunSpec,
    metadata: dict[str, Any],
) -> None:
    if metadata.get("task_id") != run.task_id:
        raise ValueError(f"Run task mismatch for {run.artifact_dir}: expected {run.task_id}, found {metadata.get('task_id')}")
    if metadata.get("campaign_id") != manifest.campaign_id:
        raise ValueError(
            f"Run campaign_id mismatch for {run.artifact_dir}: expected {manifest.campaign_id}, found {metadata.get('campaign_id')}"
        )
    if metadata.get("suite_version") != manifest.suite_version:
        raise ValueError(
            f"Run suite_version mismatch for {run.artifact_dir}: expected {manifest.suite_version}, found {metadata.get('suite_version')}"
        )
    if manifest.require_clean_worktree and bool(metadata.get("benchmark_git_dirty")):
        raise ValueError(f"Run {run.artifact_dir} was produced from a dirty worktree")
    if route.model is not None and _normalize_contract_value(metadata.get("model")) != _normalize_contract_value(route.model):
        raise ValueError(f"Run model mismatch for {run.artifact_dir}: expected {route.model}, found {metadata.get('model')}")
    if route.model_checkpoint is not None and _normalize_contract_value(metadata.get("model_checkpoint")) != _normalize_contract_value(route.model_checkpoint):
        raise ValueError(
            f"Run checkpoint mismatch for {run.artifact_dir}: expected {route.model_checkpoint}, found {metadata.get('model_checkpoint')}"
        )
    if route.execution_class is not None and _normalize_contract_value(metadata.get("execution_class")) != _normalize_contract_value(route.execution_class):
        raise ValueError(
            f"Run execution_class mismatch for {run.artifact_dir}: expected {route.execution_class}, found {metadata.get('execution_class')}"
        )
    if route.runtime is not None and _normalize_contract_value(metadata.get("runtime")) != _normalize_contract_value(route.runtime):
        raise ValueError(f"Run runtime mismatch for {run.artifact_dir}: expected {route.runtime}, found {metadata.get('runtime')}")
    if route.runtime_version is not None and _normalize_contract_value(metadata.get("runtime_version")) != _normalize_contract_value(route.runtime_version):
        raise ValueError(
            f"Run runtime_version mismatch for {run.artifact_dir}: expected {route.runtime_version}, found {metadata.get('runtime_version')}"
        )
    if route.quantization is not None and _normalize_contract_value(metadata.get("quantization")) != _normalize_contract_value(route.quantization):
        raise ValueError(
            f"Run quantization mismatch for {run.artifact_dir}: expected {route.quantization}, found {metadata.get('quantization')}"
        )
    if route.offload_policy is not None and _normalize_contract_value(metadata.get("offload_policy")) != _normalize_contract_value(route.offload_policy):
        raise ValueError(
            f"Run offload_policy mismatch for {run.artifact_dir}: expected {route.offload_policy}, found {metadata.get('offload_policy')}"
        )
    if route.endpoint_contract is not None and _normalize_contract_value(metadata.get("endpoint_contract")) != _normalize_contract_value(route.endpoint_contract):
        raise ValueError(
            f"Run endpoint_contract mismatch for {run.artifact_dir}: expected {route.endpoint_contract}, found {metadata.get('endpoint_contract')}"
        )
    if route.endpoint_base_url is not None and _normalize_contract_value(metadata.get("endpoint_base_url")) != _normalize_contract_value(route.endpoint_base_url):
        raise ValueError(
            f"Run endpoint_base_url mismatch for {run.artifact_dir}: expected {route.endpoint_base_url}, found {metadata.get('endpoint_base_url')}"
        )


def _validate_shared_audit_contract(manifest: CampaignManifest, rows: list[dict[str, Any]]) -> dict[str, Any]:
    shared_fields = [
        "benchmark_git_sha",
        "benchmark_git_dirty",
        "benchmark_git_diff_hash",
        "task_snapshot_hash",
        "seed_data_hash",
        "environment_inventory_hash",
        "environment_inventory_path",
    ]
    shared: dict[str, Any] = {}
    for field in shared_fields:
        values = sorted({row[field] for row in rows})
        if len(values) != 1:
            raise ValueError(
                f"Campaign {manifest.campaign_id} mixes multiple values for {field}: {values}"
            )
        shared[field] = values[0]
    if shared["benchmark_git_dirty"] and not shared["benchmark_git_diff_hash"]:
        raise ValueError(
            f"Campaign {manifest.campaign_id} allows dirty worktree but does not preserve a shared benchmark_git_diff_hash"
        )
    shared["environment_inventory"] = _load_environment_inventory(
        shared["environment_inventory_path"],
        shared["environment_inventory_hash"],
    )
    return shared


def _summarize_route(
    manifest: CampaignManifest,
    route: CampaignRouteSpec,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    total = len(rows)
    task_success = sum(1 for row in rows if row["task_success"])
    semantic_success = sum(1 for row in rows if row["semantic_success"])
    protocol_error = sum(1 for row in rows if row["protocol_error"])
    executor_error = sum(1 for row in rows if row["executor_error"])
    model_error = sum(1 for row in rows if row["model_error"])
    return {
        "route_id": route.route_id,
        "label": route.label,
        "model": route.model,
        "model_checkpoint": route.model_checkpoint,
        "execution_class": route.execution_class,
        "runtime": route.runtime,
        "runtime_version": route.runtime_version,
        "quantization": route.quantization,
        "offload_policy": route.offload_policy,
        "endpoint_contract": route.endpoint_contract,
        "endpoint_base_url": route.endpoint_base_url,
        "tasks_expected": manifest.task_ids,
        "runs_total": total,
        "task_success_count": task_success,
        "semantic_success_count": semantic_success,
        "protocol_error_runs": protocol_error,
        "executor_error_runs": executor_error,
        "model_error_runs": model_error,
        "task_success_rate": round(task_success / total, 4) if total else 0.0,
        "semantic_success_rate": round(semantic_success / total, 4) if total else 0.0,
        "average_duration_seconds": _average(row["duration_seconds"] for row in rows),
        "average_peak_vram_mb": _average(row["peak_vram_mb"] for row in rows),
    }


def _write_rows_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _render_markdown_summary(summary: dict[str, Any]) -> str:
    shared = summary["shared_audit"]
    inventory = shared["environment_inventory"]
    hardware_lines = _render_hardware_lines(inventory)
    route_rows = _render_route_config_rows(summary["routes"])
    task_rows = _render_task_result_rows(summary["rows"])
    lines = [
        "# Campaign Summary",
        "",
        f"- campaign_id: `{summary['campaign_id']}`",
        f"- suite_version: `{summary['suite_version']}`",
        f"- task_ids: `{', '.join(summary['task_ids'])}`",
        f"- repetitions_per_task: `{summary['repetitions_per_task']}`",
        f"- benchmark_git_sha: `{shared['benchmark_git_sha']}`",
        f"- benchmark_git_dirty: `{shared['benchmark_git_dirty']}`",
        f"- benchmark_git_diff_hash: `{shared['benchmark_git_diff_hash']}`",
        f"- task_snapshot_hash: `{shared['task_snapshot_hash']}`",
        f"- seed_data_hash: `{shared['seed_data_hash']}`",
        f"- environment_inventory_hash: `{shared['environment_inventory_hash']}`",
        "",
        "## Hardware Detectado",
        "",
        *hardware_lines,
        "",
        "## Configuracao por Rota",
        "",
        "| Route | Model | Checkpoint | Class | Runtime | Runtime version | Quantization | Offload | Endpoint |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        *route_rows,
        "",
        "## Resumo por Rota",
        "",
        "| Route | Class | Task success | Semantic success | Avg duration (s) | Avg peak VRAM (MB) |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for route in summary["routes"]:
        lines.append(
            "| "
            f"`{route['label']}` | `{route.get('execution_class') or ''}` | "
            f"{route['task_success_count']}/{route['runs_total']} | "
            f"{route['semantic_success_count']}/{route['runs_total']} | "
            f"{route['average_duration_seconds']} | "
            f"{route['average_peak_vram_mb']} |"
        )
    lines.extend(
        [
            "",
            "## Resultado por Tarefa",
            "",
            "| Route | Task | Task success | Semantic success | Protocol | Executor | Model | Duration (s) | Peak VRAM (MB) | Failure reason |",
            "| --- | --- | --- | --- | --- | --- | --- | ---: | ---: | --- |",
            *task_rows,
            "",
        ]
    )
    return "\n".join(lines)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _average(values: Any) -> float | None:
    numeric_values = [float(value) for value in values if value is not None]
    if not numeric_values:
        return None
    return round(sum(numeric_values) / len(numeric_values), 3)


def _resolve_artifact_dir(manifest_root: Path, artifact_dir: Path) -> Path:
    candidates = [
        (manifest_root / artifact_dir).resolve(),
        (manifest_root.parent / artifact_dir).resolve(),
    ]
    for candidate in candidates:
        if (candidate / "metadata.json").exists():
            return candidate
    return candidates[0]


def _load_environment_inventory(path_value: str, expected_hash: str) -> dict[str, Any]:
    path = Path(path_value)
    if not path.exists():
        raise ValueError(f"Environment inventory not found: {path}")
    current_hash = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    if current_hash != expected_hash:
        raise ValueError(
            f"Environment inventory hash mismatch for {path}: expected {expected_hash}, found {current_hash}"
        )
    return _read_json(path)


def _render_hardware_lines(inventory: dict[str, Any]) -> list[str]:
    if not inventory:
        return ["- inventario de ambiente nao encontrado no caminho registrado."]
    platform_info = inventory.get("platform") or {}
    gpu_query = ((inventory.get("nvidia_smi") or {}).get("query")) or "nao disponivel"
    return [
        f"- sistema: `{platform_info.get('system', 'desconhecido')}`",
        f"- release: `{platform_info.get('release', 'desconhecido')}`",
        f"- arquitetura: `{platform_info.get('architecture', 'desconhecido')}`",
        f"- gpu query: `{gpu_query}`",
    ]


def _render_route_config_rows(routes: list[dict[str, Any]]) -> list[str]:
    rows: list[str] = []
    for route in routes:
        rows.append(
            "| "
            f"`{route['label']}` | `{route.get('model') or ''}` | `{route.get('model_checkpoint') or ''}` | "
            f"`{route.get('execution_class') or ''}` | `{route.get('runtime') or ''}` | "
            f"`{route.get('runtime_version') or ''}` | `{route.get('quantization') or ''}` | "
            f"`{route.get('offload_policy') or ''}` | `{route.get('endpoint_contract') or ''}` |"
        )
    return rows


def _render_task_result_rows(rows: list[dict[str, Any]]) -> list[str]:
    rendered: list[str] = []
    for row in rows:
        rendered.append(
            "| "
            f"`{row['route_label']}` | `{row['task_id']}` | `{row['task_success']}` | "
            f"`{row['semantic_success']}` | `{row['protocol_error']}` | `{row['executor_error']}` | "
            f"`{row['model_error']}` | {row['duration_seconds']} | {row['peak_vram_mb']} | "
            f"`{row.get('failure_reason') or ''}` |"
        )
    return rendered


def _normalize_contract_value(value: Any) -> str:
    if value is None:
        return ""
    normalized = str(value).strip().lower()
    if normalized in {"", "none", "null", "n/a"}:
        return ""
    return normalized


def _is_missing_contract_value(value: Any) -> bool:
    if value is None:
        return True
    return str(value).strip() == ""

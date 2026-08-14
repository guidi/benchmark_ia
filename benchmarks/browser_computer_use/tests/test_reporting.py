from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from benchmark_cua.reporting.campaign import consolidate_campaign


def test_consolidate_campaign_writes_deterministic_outputs(tmp_path: Path) -> None:
    run_dir = tmp_path / "artifacts" / "runs" / "t1-product-navigation" / "route-a-r1"
    run_dir.mkdir(parents=True)
    inventory_path = tmp_path / "artifacts" / "environment-inventory.json"
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(
        json.dumps(
            {
                "platform": {"system": "Windows", "release": "11", "architecture": "AMD64"},
                "nvidia_smi": {"query": "RTX 4060, 8188, 7900, 580.0, P0, 72, 140"},
            }
        ),
        encoding="utf-8",
    )
    inventory_hash = hashlib.sha256(inventory_path.read_bytes()).hexdigest()[:16]
    metadata = {
        "run_id": "route-a-r1",
        "task_id": "t1-product-navigation",
        "model": "microsoft/Fara1.5-4B",
        "suite": "suite-a-controlled",
        "suite_version": "suite-a-controlled-v1",
        "campaign_id": "suite-a-sample",
        "model_checkpoint": "microsoft/Fara1.5-4B",
        "execution_class": "quantized",
        "quantization": "bitsandbytes-4bit",
        "runtime": "openai-compatible-endpoint",
        "runtime_version": "transformers-1",
        "offload_policy": None,
        "endpoint_base_url": "http://127.0.0.1:8001",
        "endpoint_contract": "openai-chat-completions-multimodal-computer-use",
        "benchmark_git_sha": "abc123",
        "benchmark_git_dirty": False,
        "benchmark_git_diff_hash": None,
        "task_snapshot_hash": "taskhash123",
        "seed_data_hash": "seedhash123",
        "environment_inventory_path": str(inventory_path),
        "environment_inventory_hash": inventory_hash,
    }
    metrics = {
        "run_id": "route-a-r1",
        "task_success": True,
        "semantic_success": True,
        "protocol_error": False,
        "executor_error": False,
        "model_error": False,
        "steps_executed": 3,
        "duration_seconds": 12.5,
        "peak_vram_mb": 7000.0,
    }
    final_state = {
        "final_url": "http://127.0.0.1:8000/products/teclado-mecanico",
    }
    (run_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    (run_dir / "metrics.json").write_text(json.dumps(metrics), encoding="utf-8")
    (run_dir / "final-state.json").write_text(json.dumps(final_state), encoding="utf-8")

    manifest = tmp_path / "campaign.yaml"
    manifest.write_text(
        "\n".join(
            [
                "campaign_id: suite-a-sample",
                "benchmark: browser_computer_use",
                "suite_version: suite-a-controlled-v1",
                "task_ids:",
                "  - t1-product-navigation",
                "repetitions_per_task: 1",
                "require_clean_worktree: true",
                "routes:",
                "  - route_id: route-a",
                "    label: Route A",
                "    model: microsoft/Fara1.5-4B",
                "    model_checkpoint: microsoft/Fara1.5-4B",
                "    execution_class: quantized",
                "    runtime: openai-compatible-endpoint",
                "    runtime_version: transformers-1",
                "    quantization: bitsandbytes-4bit",
                "    offload_policy: none",
                "    endpoint_contract: openai-chat-completions-multimodal-computer-use",
                "    endpoint_base_url: http://127.0.0.1:8001",
                "    runs:",
                "      - task_id: t1-product-navigation",
                "        artifact_dir: artifacts/runs/t1-product-navigation/route-a-r1",
            ]
        ),
        encoding="utf-8",
    )

    written = consolidate_campaign(manifest_path=manifest, output_dir=tmp_path / "results")

    summary = json.loads(written["summary_json"].read_text(encoding="utf-8"))
    assert summary["campaign_id"] == "suite-a-sample"
    assert summary["routes"][0]["task_success_count"] == 1
    assert summary["shared_audit"]["environment_inventory_hash"] == inventory_hash
    assert written["results_csv"].exists()
    assert "Route A" in written["summary_md"].read_text(encoding="utf-8")


def test_consolidate_campaign_rejects_missing_audit_fields(tmp_path: Path) -> None:
    run_dir = tmp_path / "artifacts" / "runs" / "t1-product-navigation" / "route-a-r1"
    run_dir.mkdir(parents=True)
    (run_dir / "metadata.json").write_text(
        json.dumps(
            {
                "run_id": "route-a-r1",
                "task_id": "t1-product-navigation",
                "model": "microsoft/Fara1.5-4B",
                "suite": "suite-a-controlled",
                "runtime": "openai-compatible-endpoint",
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "metrics.json").write_text(
        json.dumps(
            {
                "run_id": "route-a-r1",
                "task_success": True,
                "semantic_success": True,
                "protocol_error": False,
                "executor_error": False,
                "model_error": False,
                "steps_executed": 3,
                "duration_seconds": 12.5,
                "peak_vram_mb": 7000.0,
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "final-state.json").write_text(
        json.dumps({"final_url": "http://127.0.0.1:8000/products/teclado-mecanico"}),
        encoding="utf-8",
    )
    manifest = tmp_path / "campaign.yaml"
    manifest.write_text(
        "\n".join(
            [
                "campaign_id: suite-a-sample",
                "benchmark: browser_computer_use",
                "suite_version: suite-a-controlled-v1",
                "task_ids:",
                "  - t1-product-navigation",
                "repetitions_per_task: 1",
                "require_clean_worktree: true",
                "routes:",
                "  - route_id: route-a",
                "    label: Route A",
                "    runs:",
                "      - task_id: t1-product-navigation",
                "        artifact_dir: artifacts/runs/t1-product-navigation/route-a-r1",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing required contract fields"):
        consolidate_campaign(manifest_path=manifest, output_dir=tmp_path / "results")


def test_consolidate_campaign_allows_null_telemetry(tmp_path: Path) -> None:
    run_dir = tmp_path / "artifacts" / "runs" / "t1-product-navigation" / "route-a-r1"
    run_dir.mkdir(parents=True)
    inventory_path = tmp_path / "artifacts" / "environment-inventory.json"
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(
        json.dumps(
            {
                "platform": {"system": "Windows", "release": "11", "architecture": "AMD64"},
                "nvidia_smi": {"query": "RTX 4060, 8188, 7900, 580.0, P0, 72, 140"},
            }
        ),
        encoding="utf-8",
    )
    inventory_hash = hashlib.sha256(inventory_path.read_bytes()).hexdigest()[:16]
    (run_dir / "metadata.json").write_text(
        json.dumps(
            {
                "run_id": "route-a-r1",
                "task_id": "t1-product-navigation",
                "model": "microsoft/Fara1.5-4B",
                "suite": "suite-a-controlled",
                "suite_version": "suite-a-controlled-v1",
                "campaign_id": "suite-a-sample",
                "model_checkpoint": "microsoft/Fara1.5-4B",
                "execution_class": "quantized",
                "runtime": "openai-compatible-endpoint",
                "runtime_version": "transformers-1",
                "quantization": "bitsandbytes-4bit",
                "offload_policy": None,
                "endpoint_base_url": "http://127.0.0.1:8001",
                "endpoint_contract": "openai-chat-completions-multimodal-computer-use",
                "benchmark_git_sha": "abc123",
                "benchmark_git_dirty": False,
                "benchmark_git_diff_hash": None,
                "task_snapshot_hash": "taskhash123",
                "seed_data_hash": "seedhash123",
                "environment_inventory_path": str(inventory_path),
                "environment_inventory_hash": inventory_hash,
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "metrics.json").write_text(
        json.dumps(
            {
                "run_id": "route-a-r1",
                "task_success": True,
                "semantic_success": True,
                "protocol_error": False,
                "executor_error": False,
                "model_error": False,
                "steps_executed": 3,
                "duration_seconds": 12.5,
                "peak_vram_mb": None,
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "final-state.json").write_text(
        json.dumps({"final_url": "http://127.0.0.1:8000/products/teclado-mecanico"}),
        encoding="utf-8",
    )
    manifest = tmp_path / "campaign.yaml"
    manifest.write_text(
        "\n".join(
            [
                "campaign_id: suite-a-sample",
                "benchmark: browser_computer_use",
                "suite_version: suite-a-controlled-v1",
                "require_clean_worktree: true",
                "task_ids:",
                "  - t1-product-navigation",
                "repetitions_per_task: 1",
                "routes:",
                "  - route_id: route-a",
                "    label: Route A",
                "    model: microsoft/Fara1.5-4B",
                "    model_checkpoint: microsoft/Fara1.5-4B",
                "    execution_class: quantized",
                "    runtime: openai-compatible-endpoint",
                "    runtime_version: transformers-1",
                "    quantization: bitsandbytes-4bit",
                "    offload_policy: none",
                "    endpoint_contract: openai-chat-completions-multimodal-computer-use",
                "    endpoint_base_url: http://127.0.0.1:8001",
                "    runs:",
                "      - task_id: t1-product-navigation",
                "        artifact_dir: artifacts/runs/t1-product-navigation/route-a-r1",
            ]
        ),
        encoding="utf-8",
    )

    written = consolidate_campaign(manifest_path=manifest, output_dir=tmp_path / "results")
    summary = json.loads(written["summary_json"].read_text(encoding="utf-8"))
    assert summary["routes"][0]["average_peak_vram_mb"] is None


def test_consolidate_campaign_resolves_artifacts_from_benchmark_root(tmp_path: Path) -> None:
    benchmark_root = tmp_path / "benchmark"
    campaigns_dir = benchmark_root / "campaigns"
    run_dir = benchmark_root / "artifacts" / "runs" / "t1-product-navigation" / "route-a-r1"
    run_dir.mkdir(parents=True)
    campaigns_dir.mkdir(parents=True)
    inventory_path = benchmark_root / "artifacts" / "environment-inventory.json"
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(
        json.dumps(
            {
                "platform": {"system": "Windows", "release": "11", "architecture": "AMD64"},
                "nvidia_smi": {"query": "RTX 4060, 8188, 7900, 580.0, P0, 72, 140"},
            }
        ),
        encoding="utf-8",
    )
    inventory_hash = hashlib.sha256(inventory_path.read_bytes()).hexdigest()[:16]
    (run_dir / "metadata.json").write_text(
        json.dumps(
            {
                "run_id": "route-a-r1",
                "task_id": "t1-product-navigation",
                "model": "microsoft/Fara1.5-4B",
                "suite": "suite-a-controlled",
                "suite_version": "suite-a-controlled-v1",
                "campaign_id": "suite-a-sample",
                "model_checkpoint": "microsoft/Fara1.5-4B",
                "execution_class": "quantized",
                "runtime": "openai-compatible-endpoint",
                "runtime_version": "transformers-1",
                "quantization": "bitsandbytes-4bit",
                "offload_policy": None,
                "endpoint_base_url": "http://127.0.0.1:8001",
                "endpoint_contract": "openai-chat-completions-multimodal-computer-use",
                "benchmark_git_sha": "abc123",
                "benchmark_git_dirty": False,
                "benchmark_git_diff_hash": None,
                "task_snapshot_hash": "suitehash123",
                "seed_data_hash": "seedhash123",
                "environment_inventory_path": str(inventory_path),
                "environment_inventory_hash": inventory_hash,
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "metrics.json").write_text(
        json.dumps(
            {
                "run_id": "route-a-r1",
                "task_success": True,
                "semantic_success": True,
                "protocol_error": False,
                "executor_error": False,
                "model_error": False,
                "steps_executed": 3,
                "duration_seconds": 12.5,
                "peak_vram_mb": 7000.0,
                "failure_reason": None,
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "final-state.json").write_text(
        json.dumps({"final_url": "http://127.0.0.1:8000/products/teclado-mecanico"}),
        encoding="utf-8",
    )
    manifest = campaigns_dir / "campaign.yaml"
    manifest.write_text(
        "\n".join(
            [
                "campaign_id: suite-a-sample",
                "benchmark: browser_computer_use",
                "suite_version: suite-a-controlled-v1",
                "require_clean_worktree: true",
                "task_ids:",
                "  - t1-product-navigation",
                "repetitions_per_task: 1",
                "routes:",
                "  - route_id: route-a",
                "    label: Route A",
                "    model: microsoft/Fara1.5-4B",
                "    model_checkpoint: microsoft/Fara1.5-4B",
                "    execution_class: quantized",
                "    runtime: openai-compatible-endpoint",
                "    runtime_version: transformers-1",
                "    quantization: bitsandbytes-4bit",
                "    offload_policy: none",
                "    endpoint_contract: openai-chat-completions-multimodal-computer-use",
                "    endpoint_base_url: http://127.0.0.1:8001",
                "    runs:",
                "      - task_id: t1-product-navigation",
                "        artifact_dir: artifacts/runs/t1-product-navigation/route-a-r1",
            ]
        ),
        encoding="utf-8",
    )

    written = consolidate_campaign(manifest_path=manifest, output_dir=benchmark_root / "results")
    assert written["summary_json"].exists()


def test_consolidate_campaign_rejects_mutated_environment_inventory(tmp_path: Path) -> None:
    run_dir = tmp_path / "artifacts" / "runs" / "t1-product-navigation" / "route-a-r1"
    run_dir.mkdir(parents=True)
    inventory_path = tmp_path / "artifacts" / "environment-inventory.json"
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    original_inventory = {
        "platform": {"system": "Windows", "release": "11", "architecture": "AMD64"},
        "nvidia_smi": {"query": "RTX 4060, 8188, 7900, 580.0, P0, 72, 140"},
    }
    inventory_path.write_text(json.dumps(original_inventory), encoding="utf-8")
    inventory_hash = hashlib.sha256(inventory_path.read_bytes()).hexdigest()[:16]
    (run_dir / "metadata.json").write_text(
        json.dumps(
            {
                "run_id": "route-a-r1",
                "task_id": "t1-product-navigation",
                "model": "microsoft/Fara1.5-4B",
                "suite": "suite-a-controlled",
                "suite_version": "suite-a-controlled-v1",
                "campaign_id": "suite-a-sample",
                "model_checkpoint": "microsoft/Fara1.5-4B",
                "execution_class": "quantized",
                "runtime": "openai-compatible-endpoint",
                "runtime_version": "transformers-1",
                "quantization": "bitsandbytes-4bit",
                "offload_policy": None,
                "endpoint_base_url": "http://127.0.0.1:8001",
                "endpoint_contract": "openai-chat-completions-multimodal-computer-use",
                "benchmark_git_sha": "abc123",
                "benchmark_git_dirty": False,
                "benchmark_git_diff_hash": None,
                "task_snapshot_hash": "suitehash123",
                "seed_data_hash": "seedhash123",
                "environment_inventory_path": str(inventory_path),
                "environment_inventory_hash": inventory_hash,
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "metrics.json").write_text(
        json.dumps(
            {
                "run_id": "route-a-r1",
                "task_success": True,
                "semantic_success": True,
                "protocol_error": False,
                "executor_error": False,
                "model_error": False,
                "steps_executed": 3,
                "duration_seconds": 12.5,
                "peak_vram_mb": 7000.0,
                "failure_reason": None,
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "final-state.json").write_text(
        json.dumps({"final_url": "http://127.0.0.1:8000/products/teclado-mecanico"}),
        encoding="utf-8",
    )
    inventory_path.write_text(
        json.dumps(
            {
                "platform": {"system": "Windows", "release": "11", "architecture": "AMD64"},
                "nvidia_smi": {"query": "MUTATED"},
            }
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / "campaign.yaml"
    manifest.write_text(
        "\n".join(
            [
                "campaign_id: suite-a-sample",
                "benchmark: browser_computer_use",
                "suite_version: suite-a-controlled-v1",
                "require_clean_worktree: true",
                "task_ids:",
                "  - t1-product-navigation",
                "repetitions_per_task: 1",
                "routes:",
                "  - route_id: route-a",
                "    label: Route A",
                "    model: microsoft/Fara1.5-4B",
                "    model_checkpoint: microsoft/Fara1.5-4B",
                "    execution_class: quantized",
                "    runtime: openai-compatible-endpoint",
                "    runtime_version: transformers-1",
                "    quantization: bitsandbytes-4bit",
                "    offload_policy: none",
                "    endpoint_contract: openai-chat-completions-multimodal-computer-use",
                "    endpoint_base_url: http://127.0.0.1:8001",
                "    runs:",
                "      - task_id: t1-product-navigation",
                "        artifact_dir: artifacts/runs/t1-product-navigation/route-a-r1",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Environment inventory hash mismatch"):
        consolidate_campaign(manifest_path=manifest, output_dir=tmp_path / "results")


def test_consolidate_campaign_rejects_empty_string_contract_wildcards(tmp_path: Path) -> None:
    run_dir = tmp_path / "artifacts" / "runs" / "t1-product-navigation" / "route-a-r1"
    run_dir.mkdir(parents=True)
    inventory_path = tmp_path / "artifacts" / "environment-inventory.json"
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(
        json.dumps(
            {
                "platform": {"system": "Windows", "release": "11", "architecture": "AMD64"},
                "nvidia_smi": {"query": "RTX 4060, 8188, 7900, 580.0, P0, 72, 140"},
            }
        ),
        encoding="utf-8",
    )
    inventory_hash = hashlib.sha256(inventory_path.read_bytes()).hexdigest()[:16]
    (run_dir / "metadata.json").write_text(
        json.dumps(
            {
                "run_id": "route-a-r1",
                "task_id": "t1-product-navigation",
                "model": "microsoft/Fara1.5-4B",
                "suite": "suite-a-controlled",
                "suite_version": "suite-a-controlled-v1",
                "campaign_id": "suite-a-sample",
                "model_checkpoint": "microsoft/Fara1.5-4B",
                "execution_class": "quantized",
                "runtime": "openai-compatible-endpoint",
                "runtime_version": "transformers-1",
                "quantization": "bitsandbytes-4bit",
                "offload_policy": None,
                "endpoint_base_url": "http://127.0.0.1:8001",
                "endpoint_contract": "openai-chat-completions-multimodal-computer-use",
                "benchmark_git_sha": "abc123",
                "benchmark_git_dirty": False,
                "benchmark_git_diff_hash": None,
                "task_snapshot_hash": "suitehash123",
                "seed_data_hash": "seedhash123",
                "environment_inventory_path": str(inventory_path),
                "environment_inventory_hash": inventory_hash,
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "metrics.json").write_text(
        json.dumps(
            {
                "run_id": "route-a-r1",
                "task_success": True,
                "semantic_success": True,
                "protocol_error": False,
                "executor_error": False,
                "model_error": False,
                "steps_executed": 3,
                "duration_seconds": 12.5,
                "peak_vram_mb": 7000.0,
                "failure_reason": None,
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "final-state.json").write_text(
        json.dumps({"final_url": "http://127.0.0.1:8000/products/teclado-mecanico"}),
        encoding="utf-8",
    )
    manifest = tmp_path / "campaign.yaml"
    manifest.write_text(
        "\n".join(
            [
                "campaign_id: suite-a-sample",
                "benchmark: browser_computer_use",
                "suite_version: suite-a-controlled-v1",
                "require_clean_worktree: true",
                "task_ids:",
                "  - t1-product-navigation",
                "repetitions_per_task: 1",
                "routes:",
                "  - route_id: route-a",
                "    label: Route A",
                '    runtime: ""',
                "    runs:",
                "      - task_id: t1-product-navigation",
                "        artifact_dir: artifacts/runs/t1-product-navigation/route-a-r1",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing required contract fields"):
        consolidate_campaign(manifest_path=manifest, output_dir=tmp_path / "results")


def test_consolidate_campaign_rejects_omitted_route_contract_fields(tmp_path: Path) -> None:
    run_dir = tmp_path / "artifacts" / "runs" / "t1-product-navigation" / "route-a-r1"
    run_dir.mkdir(parents=True)
    inventory_path = tmp_path / "artifacts" / "environment-inventory.json"
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(
        json.dumps(
            {
                "platform": {"system": "Windows", "release": "11", "architecture": "AMD64"},
                "nvidia_smi": {"query": "RTX 4060, 8188, 7900, 580.0, P0, 72, 140"},
            }
        ),
        encoding="utf-8",
    )
    inventory_hash = hashlib.sha256(inventory_path.read_bytes()).hexdigest()[:16]
    (run_dir / "metadata.json").write_text(
        json.dumps(
            {
                "run_id": "route-a-r1",
                "task_id": "t1-product-navigation",
                "model": "microsoft/Fara1.5-4B",
                "suite": "suite-a-controlled",
                "suite_version": "suite-a-controlled-v1",
                "campaign_id": "suite-a-sample",
                "model_checkpoint": "microsoft/Fara1.5-4B",
                "execution_class": "quantized",
                "runtime": "openai-compatible-endpoint",
                "runtime_version": "transformers-1",
                "quantization": "bitsandbytes-4bit",
                "offload_policy": None,
                "endpoint_base_url": "http://127.0.0.1:8001",
                "endpoint_contract": "openai-chat-completions-multimodal-computer-use",
                "benchmark_git_sha": "abc123",
                "benchmark_git_dirty": False,
                "benchmark_git_diff_hash": None,
                "task_snapshot_hash": "suitehash123",
                "seed_data_hash": "seedhash123",
                "environment_inventory_path": str(inventory_path),
                "environment_inventory_hash": inventory_hash,
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "metrics.json").write_text(
        json.dumps(
            {
                "run_id": "route-a-r1",
                "task_success": True,
                "semantic_success": True,
                "protocol_error": False,
                "executor_error": False,
                "model_error": False,
                "steps_executed": 3,
                "duration_seconds": 12.5,
                "peak_vram_mb": 7000.0,
                "failure_reason": None,
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "final-state.json").write_text(
        json.dumps({"final_url": "http://127.0.0.1:8000/products/teclado-mecanico"}),
        encoding="utf-8",
    )
    manifest = tmp_path / "campaign.yaml"
    manifest.write_text(
        "\n".join(
            [
                "campaign_id: suite-a-sample",
                "benchmark: browser_computer_use",
                "suite_version: suite-a-controlled-v1",
                "require_clean_worktree: true",
                "task_ids:",
                "  - t1-product-navigation",
                "repetitions_per_task: 1",
                "routes:",
                "  - route_id: route-a",
                "    label: Route A",
                "    runs:",
                "      - task_id: t1-product-navigation",
                "        artifact_dir: artifacts/runs/t1-product-navigation/route-a-r1",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing required contract fields"):
        consolidate_campaign(manifest_path=manifest, output_dir=tmp_path / "results")


def test_consolidate_campaign_rejects_mixed_dirty_diff_hashes_when_allowed(tmp_path: Path) -> None:
    inventory_path = tmp_path / "artifacts" / "environment-inventory.json"
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(
        json.dumps(
            {
                "platform": {"system": "Windows", "release": "11", "architecture": "AMD64"},
                "nvidia_smi": {"query": "RTX 4060, 8188, 7900, 580.0, P0, 72, 140"},
            }
        ),
        encoding="utf-8",
    )
    inventory_hash = hashlib.sha256(inventory_path.read_bytes()).hexdigest()[:16]

    for task_id, diff_hash in [("t1-product-navigation", "diff-a"), ("t2-create-customer", "diff-b")]:
        run_dir = tmp_path / "artifacts" / "runs" / task_id / f"{task_id}-r1"
        run_dir.mkdir(parents=True)
        (run_dir / "metadata.json").write_text(
            json.dumps(
                {
                    "run_id": f"{task_id}-r1",
                    "task_id": task_id,
                    "model": "microsoft/Fara1.5-4B",
                    "suite": "suite-a-controlled",
                    "suite_version": "suite-a-controlled-v1",
                    "campaign_id": "suite-a-sample",
                    "model_checkpoint": "microsoft/Fara1.5-4B",
                    "execution_class": "quantized",
                    "runtime": "openai-compatible-endpoint",
                    "runtime_version": "transformers-1",
                    "quantization": "bitsandbytes-4bit",
                    "offload_policy": None,
                    "endpoint_base_url": "http://127.0.0.1:8001",
                    "endpoint_contract": "openai-chat-completions-multimodal-computer-use",
                    "benchmark_git_sha": "abc123",
                    "benchmark_git_dirty": True,
                    "benchmark_git_diff_hash": diff_hash,
                    "task_snapshot_hash": "suitehash123",
                    "seed_data_hash": "seedhash123",
                    "environment_inventory_path": str(inventory_path),
                    "environment_inventory_hash": inventory_hash,
                }
            ),
            encoding="utf-8",
        )
        (run_dir / "metrics.json").write_text(
            json.dumps(
                {
                    "run_id": f"{task_id}-r1",
                    "task_success": True,
                    "semantic_success": True,
                    "protocol_error": False,
                    "executor_error": False,
                    "model_error": False,
                    "steps_executed": 3,
                    "duration_seconds": 12.5,
                    "peak_vram_mb": 7000.0,
                    "failure_reason": None,
                }
            ),
            encoding="utf-8",
        )
        (run_dir / "final-state.json").write_text(
            json.dumps({"final_url": f"http://127.0.0.1:8000/{task_id}"}),
            encoding="utf-8",
        )

    manifest = tmp_path / "campaign.yaml"
    manifest.write_text(
        "\n".join(
            [
                "campaign_id: suite-a-sample",
                "benchmark: browser_computer_use",
                "suite_version: suite-a-controlled-v1",
                "require_clean_worktree: false",
                "task_ids:",
                "  - t1-product-navigation",
                "  - t2-create-customer",
                "repetitions_per_task: 1",
                "routes:",
                "  - route_id: route-a",
                "    label: Route A",
                "    model: microsoft/Fara1.5-4B",
                "    model_checkpoint: microsoft/Fara1.5-4B",
                "    execution_class: quantized",
                "    runtime: openai-compatible-endpoint",
                "    runtime_version: transformers-1",
                "    quantization: bitsandbytes-4bit",
                "    offload_policy: none",
                "    endpoint_contract: openai-chat-completions-multimodal-computer-use",
                "    endpoint_base_url: http://127.0.0.1:8001",
                "    runs:",
                "      - task_id: t1-product-navigation",
                "        artifact_dir: artifacts/runs/t1-product-navigation/t1-product-navigation-r1",
                "      - task_id: t2-create-customer",
                "        artifact_dir: artifacts/runs/t2-create-customer/t2-create-customer-r1",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="benchmark_git_diff_hash"):
        consolidate_campaign(manifest_path=manifest, output_dir=tmp_path / "results")

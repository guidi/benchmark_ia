from __future__ import annotations

import json
import platform
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil


def _run_command(command: list[str]) -> str | None:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except Exception:
        return None
    return result.stdout.strip()


def _bytes_to_gib(value: int) -> float:
    return round(value / (1024**3), 2)


def collect_environment_inventory() -> dict[str, Any]:
    inventory: dict[str, Any] = {
        "captured_at": datetime.now().isoformat(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "architecture": platform.machine(),
        },
        "cpu": {
            "processor": platform.processor(),
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
        },
        "memory": {
            "total_bytes": psutil.virtual_memory().total,
            "total_gib": _bytes_to_gib(psutil.virtual_memory().total),
        },
        "disks": [],
        "python": {
            "version": platform.python_version(),
            "executable": shutil.which("python"),
        },
        "node": {
            "version": _run_command(["node", "--version"]),
        },
        "git": {
            "version": _run_command(["git", "--version"]),
        },
        "nvidia_smi": {
            "summary": _run_command(["nvidia-smi"]),
        },
    }

    for partition in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(partition.mountpoint)
        except PermissionError:
            continue
        inventory["disks"].append(
            {
                "device": partition.device,
                "mountpoint": partition.mountpoint,
                "filesystem": partition.fstype,
                "total_gib": _bytes_to_gib(usage.total),
                "used_gib": _bytes_to_gib(usage.used),
                "free_gib": _bytes_to_gib(usage.free),
            }
        )

    gpu_query = _run_command(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total,memory.free,driver_version,pstate,temperature.gpu,power.limit",
            "--format=csv,noheader,nounits",
        ]
    )
    if gpu_query:
        inventory["nvidia_smi"]["query"] = gpu_query

    return inventory


def write_environment_inventory(output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = collect_environment_inventory()
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path


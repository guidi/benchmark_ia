from __future__ import annotations

import csv
import os
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import psutil

try:
    import pynvml
except Exception:  # pragma: no cover - environment-dependent import
    pynvml = None


@dataclass
class ResourceSample:
    timestamp: float
    ram_mb: float
    gpu_vram_mb: float | None = None
    gpu_utilization_percent: float | None = None
    gpu_temperature_c: float | None = None
    gpu_power_watts: float | None = None


class ResourceMonitor:
    def __init__(self, sample_interval_seconds: float = 0.5) -> None:
        self.sample_interval_seconds = sample_interval_seconds
        self.samples: list[ResourceSample] = []
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._nvml_handle: Any | None = None
        self._nvml_ready = False
        self._process = psutil.Process(os.getpid())

    def start(self) -> None:
        self._prepare_nvml()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="resource-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        if self._nvml_ready and pynvml is not None:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass
        self._nvml_ready = False
        self._nvml_handle = None

    def summary(self) -> dict[str, float | None]:
        ram_values = [sample.ram_mb for sample in self.samples]
        vram_values = [sample.gpu_vram_mb for sample in self.samples if sample.gpu_vram_mb is not None]
        util_values = [sample.gpu_utilization_percent for sample in self.samples if sample.gpu_utilization_percent is not None]
        temperature_values = [sample.gpu_temperature_c for sample in self.samples if sample.gpu_temperature_c is not None]
        power_values = [sample.gpu_power_watts for sample in self.samples if sample.gpu_power_watts is not None]
        return {
            "peak_ram_mb": max(ram_values) if ram_values else None,
            "peak_vram_mb": max(vram_values) if vram_values else None,
            "gpu_utilization_average": round(sum(util_values) / len(util_values), 2) if util_values else None,
            "gpu_utilization_peak": max(util_values) if util_values else None,
            "gpu_temperature_peak": max(temperature_values) if temperature_values else None,
            "gpu_power_peak_watts": max(power_values) if power_values else None,
        }

    def write_csv(self, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            fieldnames = [
                "timestamp",
                "ram_mb",
                "gpu_vram_mb",
                "gpu_utilization_percent",
                "gpu_temperature_c",
                "gpu_power_watts",
            ]
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for sample in self.samples:
                writer.writerow(asdict(sample))
        return output_path

    def _prepare_nvml(self) -> None:
        if pynvml is None:
            return
        try:
            pynvml.nvmlInit()
            self._nvml_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            self._nvml_ready = True
        except Exception:
            self._nvml_ready = False
            self._nvml_handle = None

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self.samples.append(self._collect_sample())
            self._stop_event.wait(self.sample_interval_seconds)

    def _collect_sample(self) -> ResourceSample:
        ram_mb = round(self._process_tree_rss_bytes() / (1024 * 1024), 2)
        sample = ResourceSample(timestamp=time.time(), ram_mb=ram_mb)
        if self._nvml_ready and self._nvml_handle is not None and pynvml is not None:
            try:
                memory = pynvml.nvmlDeviceGetMemoryInfo(self._nvml_handle)
                utilization = pynvml.nvmlDeviceGetUtilizationRates(self._nvml_handle)
                temperature = pynvml.nvmlDeviceGetTemperature(self._nvml_handle, pynvml.NVML_TEMPERATURE_GPU)
                power = pynvml.nvmlDeviceGetPowerUsage(self._nvml_handle) / 1000.0
                sample.gpu_vram_mb = round(memory.used / (1024 * 1024), 2)
                sample.gpu_utilization_percent = float(utilization.gpu)
                sample.gpu_temperature_c = float(temperature)
                sample.gpu_power_watts = round(power, 2)
            except Exception:
                pass
        return sample

    def _process_tree_rss_bytes(self) -> int:
        total = 0
        try:
            total += self._process.memory_info().rss
            for child in self._process.children(recursive=True):
                try:
                    total += child.memory_info().rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return 0
        return total

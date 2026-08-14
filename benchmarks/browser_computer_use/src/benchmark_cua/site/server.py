from __future__ import annotations

import os
import secrets
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

import requests


@dataclass
class ManagedServerHandle:
    base_url: str
    internal_token: str


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as handle:
        handle.bind(("127.0.0.1", 0))
        return int(handle.getsockname()[1])


@contextmanager
def managed_server(host: str = "127.0.0.1", port: int | None = None) -> Iterator[ManagedServerHandle]:
    port = port or find_free_port()
    base_url = f"http://{host}:{port}"
    internal_token = secrets.token_urlsafe(24)
    env = os.environ.copy()
    env["BENCHMARK_INTERNAL_TOKEN"] = internal_token
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "benchmark_cua.site.app:create_app",
            "--factory",
            "--host",
            host,
            "--port",
            str(port),
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.time() + 20
        while time.time() < deadline:
            try:
                response = requests.get(f"{base_url}/health", timeout=2)
                if response.ok:
                    yield ManagedServerHandle(base_url=base_url, internal_token=internal_token)
                    return
            except requests.RequestException:
                time.sleep(0.3)
        raise RuntimeError("controlled benchmark app did not start in time")
    finally:
        process.terminate()
        process.wait(timeout=10)

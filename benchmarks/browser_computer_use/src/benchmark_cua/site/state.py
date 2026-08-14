from __future__ import annotations

from threading import RLock
from typing import Any

from benchmark_cua.site.data import clone_seed_data
from benchmark_cua.site.scenarios import build_task_definitions


class BenchmarkState:
    def __init__(self) -> None:
        self._lock = RLock()
        self._data = clone_seed_data()
        self._tasks = build_task_definitions(self._data)
        self._ui = self._initial_ui_state()

    def _initial_ui_state(self) -> dict[str, Any]:
        return {
            "modal_choice": None,
            "recovery_error_seen": False,
            "recovery_completed": False,
            "journey": {
                "profile": None,
                "preferences": {},
                "review_code": None,
                "launch_window": None,
                "completed": False,
            },
        }

    def reset(self) -> dict[str, Any]:
        with self._lock:
            self._data = clone_seed_data()
            self._tasks = build_task_definitions(self._data)
            self._ui = self._initial_ui_state()
            return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return clone_seed_data() if self._data is None else {
                "products": [dict(product) for product in self._data["products"]],
                "customers": [dict(customer) for customer in self._data["customers"]],
                "orders": [dict(order) for order in self._data["orders"]],
                "notes": list(self._data["notes"]),
            }

    def customers(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(customer) for customer in self._data["customers"]]

    def products(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(product) for product in self._data["products"]]

    def orders(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(order) for order in self._data["orders"]]

    def add_customer(self, name: str, email: str, city: str) -> dict[str, Any]:
        with self._lock:
            customer = {"name": name, "email": email, "city": city}
            self._data["customers"].append(customer)
            return dict(customer)

    def tasks(self) -> dict[str, Any]:
        with self._lock:
            return {task_id: task.model_copy(deep=True) for task_id, task in self._tasks.items()}

    def record_modal_choice(self, choice: str) -> None:
        with self._lock:
            self._ui["modal_choice"] = choice

    def modal_choice(self) -> str | None:
        with self._lock:
            return self._ui["modal_choice"]

    def mark_recovery_attempt(self, success: bool) -> None:
        with self._lock:
            if success:
                self._ui["recovery_completed"] = True
            else:
                self._ui["recovery_error_seen"] = True

    def recovery_status(self) -> dict[str, bool]:
        with self._lock:
            return {
                "error_seen": bool(self._ui["recovery_error_seen"]),
                "completed": bool(self._ui["recovery_completed"]),
            }

    def set_journey_profile(self, team: str) -> None:
        with self._lock:
            self._ui["journey"]["profile"] = team

    def set_journey_preferences(self, receive_alerts: bool, density: str) -> None:
        with self._lock:
            self._ui["journey"]["preferences"] = {
                "receive_alerts": receive_alerts,
                "density": density,
            }

    def set_journey_review_code(self, code: str) -> None:
        with self._lock:
            self._ui["journey"]["review_code"] = code

    def set_journey_launch_window(self, launch_window: str) -> None:
        with self._lock:
            self._ui["journey"]["launch_window"] = launch_window

    def finish_journey(self, expected: dict[str, Any]) -> bool:
        with self._lock:
            journey = self._ui["journey"]
            preferences = journey["preferences"]
            valid = (
                journey["profile"] == expected["team"]
                and preferences.get("receive_alerts") is True
                and preferences.get("density") == expected["density"]
                and journey["review_code"] == expected["review_code"]
                and journey["launch_window"] == expected["launch_window"]
            )
            journey["completed"] = valid
            return valid

    def journey_status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "profile": self._ui["journey"]["profile"],
                "preferences": dict(self._ui["journey"]["preferences"]),
                "review_code": self._ui["journey"]["review_code"],
                "launch_window": self._ui["journey"]["launch_window"],
                "completed": bool(self._ui["journey"]["completed"]),
            }


STATE = BenchmarkState()

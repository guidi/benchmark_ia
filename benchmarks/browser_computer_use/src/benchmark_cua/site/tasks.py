from __future__ import annotations

import re
from typing import Callable

from benchmark_cua.schemas import ValidationRequest, ValidationResult
from benchmark_cua.site.state import STATE


def _normalize_answer(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^0-9.,]", "", value.strip().lower())



def _validate_task_1(request: ValidationRequest) -> ValidationResult:
    task = STATE.tasks()["t1-product-navigation"]
    slug = task.private_context["product_slug"]
    expected_path = f"/products/{slug}"
    success = request.current_path == expected_path
    return ValidationResult(
        success=success,
        expected=expected_path,
        observed=request.current_path,
    )


def _validate_task_2(request: ValidationRequest) -> ValidationResult:
    task = STATE.tasks()["t2-create-customer"]
    customers = STATE.customers()
    target = {key: task.private_context[key] for key in ["name", "email", "city"]}
    success = any(customer == target for customer in customers)
    return ValidationResult(
        success=success,
        expected=f'customer {target["name"]} created',
        observed=str(target if success else customers[-1] if customers else None),
    )


def _validate_task_3(request: ValidationRequest) -> ValidationResult:
    task = STATE.tasks()["t3-open-order"]
    order_id = task.private_context["order_id"]
    expected_path = f"/orders/{order_id}"
    success = request.current_path == expected_path
    return ValidationResult(
        success=success,
        expected=expected_path,
        observed=request.current_path,
    )


def _validate_task_4(request: ValidationRequest) -> ValidationResult:
    task = STATE.tasks()["t4-pending-highest"]
    normalized = _normalize_answer(request.answer)
    accepted = {
        str(task.private_context["highest_order_id"]),
        task.private_context["highest_total"],
        task.private_context["highest_total"].replace(".", ","),
    }
    target_status = task.private_context["status"]
    on_filtered_view = request.current_path is not None and f"status={target_status}" in request.current_path
    success = normalized in accepted and on_filtered_view
    return ValidationResult(
        success=success,
        expected="highest order id or total for the filtered status",
        observed=request.answer,
        details={"current_path": request.current_path, "status": target_status},
    )


def _validate_task_5(request: ValidationRequest) -> ValidationResult:
    task = STATE.tasks()["t5-customer-recent-order"]
    normalized = _normalize_answer(request.answer)
    accepted = {str(task.private_context["recent_order_id"])}
    customer_name = task.private_context["customer_name"]
    on_customer_orders = request.current_path is not None and customer_name.replace(" ", "%20") in request.current_path
    success = normalized in accepted and on_customer_orders
    return ValidationResult(
        success=success,
        expected=str(task.private_context["recent_order_id"]),
        observed=request.answer,
        details={"current_path": request.current_path},
    )


def _validate_task_6(request: ValidationRequest) -> ValidationResult:
    task = STATE.tasks()["t6-scroll-checkpoint"]
    token = task.private_context["scroll_token"]
    expected_path = f"/scroll-lab/result?token={token}"
    success = request.current_path == expected_path
    return ValidationResult(success=success, expected=expected_path, observed=request.current_path)


def _validate_task_7(request: ValidationRequest) -> ValidationResult:
    task = STATE.tasks()["t7-modal-confirmation"]
    choice = STATE.modal_choice()
    success = request.current_path == "/modal-lab?confirmed=1" and choice == task.private_context["modal_choice"]
    return ValidationResult(
        success=success,
        expected=task.private_context["modal_choice"],
        observed=choice,
        details={"current_path": request.current_path},
    )


def _validate_task_8(request: ValidationRequest) -> ValidationResult:
    status = STATE.recovery_status()
    success = request.current_path == "/recovery-lab?success=1" and status["error_seen"] and status["completed"]
    return ValidationResult(
        success=success,
        expected="recoverable error observed before successful completion",
        observed=request.current_path,
        details=status,
    )


def _validate_task_9(request: ValidationRequest) -> ValidationResult:
    task = STATE.tasks()["t9-visual-ambiguity"]
    expected_path = f'/ambiguity-lab/{task.private_context["report_slug"]}'
    success = request.current_path == expected_path
    return ValidationResult(
        success=success,
        expected=expected_path,
        observed=request.current_path,
    )


def _validate_task_10(request: ValidationRequest) -> ValidationResult:
    journey = STATE.journey_status()
    success = request.current_path == "/journey-lab/done" and journey["completed"]
    return ValidationResult(
        success=success,
        expected="/journey-lab/done",
        observed=request.current_path,
        details=journey,
    )


TASK_VALIDATORS: dict[str, Callable[[ValidationRequest], ValidationResult]] = {
    "t1-product-navigation": _validate_task_1,
    "t2-create-customer": _validate_task_2,
    "t3-open-order": _validate_task_3,
    "t4-pending-highest": _validate_task_4,
    "t5-customer-recent-order": _validate_task_5,
    "t6-scroll-checkpoint": _validate_task_6,
    "t7-modal-confirmation": _validate_task_7,
    "t8-recovery-error": _validate_task_8,
    "t9-visual-ambiguity": _validate_task_9,
    "t10-long-journey": _validate_task_10,
}

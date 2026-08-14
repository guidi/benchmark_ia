from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Form, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from benchmark_cua.schemas import ValidationRequest
from benchmark_cua.site.scenarios import LAUNCH_WINDOWS, MODAL_CHOICES, REPORT_TARGETS, TEAMS
from benchmark_cua.site.state import STATE
from benchmark_cua.site.tasks import TASK_VALIDATORS

PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))


def _currency(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def create_app(internal_token: str | None = None) -> FastAPI:
    app = FastAPI(title="Controlled Benchmark App")
    app.mount("/static", StaticFiles(directory=str(PACKAGE_DIR / "static")), name="static")
    configured_internal_token = internal_token or os.environ.get("BENCHMARK_INTERNAL_TOKEN", "")

    def require_internal(x_benchmark_token: str | None = Header(default=None)) -> None:
        if not configured_internal_token or x_benchmark_token != configured_internal_token:
            raise HTTPException(status_code=401, detail="Missing or invalid benchmark token")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request) -> HTMLResponse:
        snapshot = STATE.snapshot()
        cards = [
            {"title": "Produtos", "href": "/products", "value": len(snapshot["products"])},
            {"title": "Clientes", "href": "/customers", "value": len(snapshot["customers"])},
            {"title": "Pedidos", "href": "/orders", "value": len(snapshot["orders"])},
        ]
        return TEMPLATES.TemplateResponse(
            request,
            "home.html",
            {
                "cards": cards,
                "notes": snapshot["notes"],
                "task_count": len(STATE.tasks()),
            },
        )

    @app.get("/products", response_class=HTMLResponse)
    def products(request: Request, q: str = "") -> HTMLResponse:
        items = STATE.products()
        if q:
            query = q.lower()
            items = [item for item in items if query in item["name"].lower() or query in item["category"].lower()]
        return TEMPLATES.TemplateResponse(request, "products.html", {"products": items, "query": q, "currency": _currency})

    @app.get("/products/{slug}", response_class=HTMLResponse)
    def product_detail(request: Request, slug: str) -> HTMLResponse:
        product = next((item for item in STATE.products() if item["slug"] == slug), None)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return TEMPLATES.TemplateResponse(request, "product_detail.html", {"product": product, "currency": _currency})

    @app.get("/customers", response_class=HTMLResponse)
    def customers(request: Request, created: int = 0, error: str = "") -> HTMLResponse:
        return TEMPLATES.TemplateResponse(
            request,
            "customers.html",
            {
                "customers": STATE.customers(),
                "created": bool(created),
                "error": error,
            },
        )

    @app.post("/customers/create")
    def create_customer(
        name: str = Form(...),
        email: str = Form(...),
        city: str = Form(...),
    ) -> RedirectResponse:
        if not name.strip() or not email.strip() or not city.strip():
            return RedirectResponse("/customers?error=Preencha%20todos%20os%20campos", status_code=303)
        STATE.add_customer(name.strip(), email.strip(), city.strip())
        return RedirectResponse("/customers?created=1", status_code=303)

    @app.get("/orders", response_class=HTMLResponse)
    def orders(request: Request, status: str = "Todos", q: str = "", page: int = 1) -> HTMLResponse:
        items = STATE.orders()
        if status != "Todos":
            items = [order for order in items if order["status"] == status]
        if q:
            query = q.lower()
            items = [
                order
                for order in items
                if query in str(order["order_id"]).lower() or query in order["customer_name"].lower()
            ]
        page_size = 5
        total_pages = max(1, (len(items) + page_size - 1) // page_size)
        page = min(max(page, 1), total_pages)
        page_items = items[(page - 1) * page_size : page * page_size]
        return TEMPLATES.TemplateResponse(
            request,
            "orders.html",
            {
                "orders": page_items,
                "status": status,
                "query": q,
                "page": page,
                "total_pages": total_pages,
                "currency": _currency,
            },
        )

    @app.get("/orders/{order_id}", response_class=HTMLResponse)
    def order_detail(request: Request, order_id: int) -> HTMLResponse:
        order = next((item for item in STATE.orders() if item["order_id"] == order_id), None)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        return TEMPLATES.TemplateResponse(request, "order_detail.html", {"order": order, "currency": _currency})

    @app.get("/workspace", response_class=HTMLResponse)
    def workspace(request: Request) -> HTMLResponse:
        return TEMPLATES.TemplateResponse(request, "workspace.html", {})

    @app.get("/scroll-lab", response_class=HTMLResponse)
    def scroll_lab(request: Request) -> HTMLResponse:
        task = STATE.tasks()["t6-scroll-checkpoint"]
        return TEMPLATES.TemplateResponse(
            request,
            "scroll_lab.html",
            {
                "target_name": task.private_context["target_name"],
                "scroll_token": task.private_context["scroll_token"],
            },
        )

    @app.get("/scroll-lab/result", response_class=HTMLResponse)
    def scroll_lab_result(request: Request, token: str) -> HTMLResponse:
        return TEMPLATES.TemplateResponse(request, "scroll_result.html", {"token": token})

    @app.get("/modal-lab", response_class=HTMLResponse)
    def modal_lab(request: Request, confirmed: int = 0) -> HTMLResponse:
        task = STATE.tasks()["t7-modal-confirmation"]
        return TEMPLATES.TemplateResponse(
            request,
            "modal_lab.html",
            {
                "options": MODAL_CHOICES,
                "confirmed": bool(confirmed),
                "selected_choice": STATE.modal_choice(),
                "target_choice": task.private_context["modal_choice"],
            },
        )

    @app.post("/modal-lab/confirm")
    def confirm_modal(choice: str = Form(...)) -> RedirectResponse:
        STATE.record_modal_choice(choice)
        return RedirectResponse("/modal-lab?confirmed=1", status_code=303)

    @app.get("/recovery-lab", response_class=HTMLResponse)
    def recovery_lab(request: Request, error: int = 0, success: int = 0) -> HTMLResponse:
        return TEMPLATES.TemplateResponse(
            request,
            "recovery_lab.html",
            {
                "error": bool(error),
                "success": bool(success),
            },
        )

    @app.post("/recovery-lab/submit")
    def submit_recovery(code: str = Form(...)) -> RedirectResponse:
        task = STATE.tasks()["t8-recovery-error"]
        expected_code = task.private_context["recovery_code"]
        if code.strip() == expected_code:
            STATE.mark_recovery_attempt(success=True)
            return RedirectResponse("/recovery-lab?success=1", status_code=303)
        STATE.mark_recovery_attempt(success=False)
        return RedirectResponse("/recovery-lab?error=1", status_code=303)

    @app.post("/recovery-lab/quick")
    def quick_recovery() -> RedirectResponse:
        STATE.mark_recovery_attempt(success=False)
        return RedirectResponse("/recovery-lab?error=1", status_code=303)

    @app.get("/ambiguity-lab", response_class=HTMLResponse)
    def ambiguity_lab(request: Request) -> HTMLResponse:
        task = STATE.tasks()["t9-visual-ambiguity"]
        target_slug = task.private_context["report_slug"]
        ordered_reports = sorted(REPORT_TARGETS, key=lambda item: (item["slug"] != target_slug, item["label"]))
        return TEMPLATES.TemplateResponse(
            request,
            "ambiguity_lab.html",
            {
                "reports": ordered_reports,
                "target_label": task.private_context["report_label"],
            },
        )

    @app.get("/ambiguity-lab/{report_slug}", response_class=HTMLResponse)
    def ambiguity_report(request: Request, report_slug: str) -> HTMLResponse:
        report = next((item for item in REPORT_TARGETS if item["slug"] == report_slug), None)
        if report is None:
            raise HTTPException(status_code=404, detail="Report not found")
        return TEMPLATES.TemplateResponse(request, "ambiguity_report.html", {"report": report})

    @app.get("/journey-lab/start", response_class=HTMLResponse)
    def journey_start(request: Request) -> HTMLResponse:
        return TEMPLATES.TemplateResponse(request, "journey_start.html", {})

    @app.get("/journey-lab/profile", response_class=HTMLResponse)
    def journey_profile(request: Request) -> HTMLResponse:
        return TEMPLATES.TemplateResponse(request, "journey_profile.html", {"teams": TEAMS})

    @app.post("/journey-lab/profile")
    def journey_profile_submit(team: str = Form(...)) -> RedirectResponse:
        STATE.set_journey_profile(team)
        return RedirectResponse("/journey-lab/preferences", status_code=303)

    @app.get("/journey-lab/preferences", response_class=HTMLResponse)
    def journey_preferences(request: Request) -> HTMLResponse:
        return TEMPLATES.TemplateResponse(request, "journey_preferences.html", {})

    @app.post("/journey-lab/preferences")
    def journey_preferences_submit(
        receive_alerts: str | None = Form(default=None),
        density: str = Form(...),
    ) -> RedirectResponse:
        STATE.set_journey_preferences(receive_alerts == "yes", density)
        return RedirectResponse("/journey-lab/review", status_code=303)

    @app.get("/journey-lab/review", response_class=HTMLResponse)
    def journey_review(request: Request) -> HTMLResponse:
        return TEMPLATES.TemplateResponse(request, "journey_review.html", {})

    @app.post("/journey-lab/review")
    def journey_review_submit(review_code: str = Form(...)) -> RedirectResponse:
        STATE.set_journey_review_code(review_code.strip())
        return RedirectResponse("/journey-lab/confirm", status_code=303)

    @app.get("/journey-lab/confirm", response_class=HTMLResponse)
    def journey_confirm(request: Request, selected: str = "") -> HTMLResponse:
        return TEMPLATES.TemplateResponse(
            request,
            "journey_confirm.html",
            {
                "launch_windows": LAUNCH_WINDOWS,
                "selected": selected,
            },
        )

    @app.post("/journey-lab/confirm")
    def journey_confirm_submit(launch_window: str = Form(...)) -> RedirectResponse:
        STATE.set_journey_launch_window(launch_window)
        return RedirectResponse(f"/journey-lab/final?selected={launch_window}", status_code=303)

    @app.get("/journey-lab/final", response_class=HTMLResponse)
    def journey_final(request: Request, selected: str = "") -> HTMLResponse:
        return TEMPLATES.TemplateResponse(request, "journey_final.html", {"selected": selected})

    @app.post("/journey-lab/finish")
    def journey_finish() -> RedirectResponse:
        task = STATE.tasks()["t10-long-journey"]
        valid = STATE.finish_journey(task.private_context)
        if valid:
            return RedirectResponse("/journey-lab/done", status_code=303)
        return RedirectResponse("/journey-lab/final?selected=invalid", status_code=303)

    @app.get("/journey-lab/done", response_class=HTMLResponse)
    def journey_done(request: Request) -> HTMLResponse:
        return TEMPLATES.TemplateResponse(request, "journey_done.html", {})

    @app.post("/api/internal/reset")
    def reset_state(x_benchmark_token: str | None = Header(default=None)) -> JSONResponse:
        require_internal(x_benchmark_token)
        return JSONResponse(STATE.reset())

    @app.get("/api/internal/tasks")
    def list_tasks(x_benchmark_token: str | None = Header(default=None)) -> list[dict]:
        require_internal(x_benchmark_token)
        return [task.model_dump(mode="json") for task in STATE.tasks().values()]

    @app.post("/api/internal/validate/{task_id}")
    def validate_task(task_id: str, payload: ValidationRequest, x_benchmark_token: str | None = Header(default=None)) -> dict:
        require_internal(x_benchmark_token)
        validator = TASK_VALIDATORS.get(task_id)
        if validator is None:
            raise HTTPException(status_code=404, detail=f"Unknown task: {task_id}")
        return validator(payload).model_dump(mode="json")

    return app

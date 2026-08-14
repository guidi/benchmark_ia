from __future__ import annotations

import hashlib
import json
import random
import re
from datetime import date

from benchmark_cua.schemas import TaskDefinition

FIRST_NAMES = ["Joao", "Beatriz", "Lucas", "Renata", "Paulo", "Marta"]
LAST_NAMES = ["da Silva", "Lopes", "Almeida", "Barbosa", "Rocha", "Mendes"]
CITIES = ["Curitiba", "Porto Alegre", "Campinas", "Goiania", "Salvador", "Fortaleza"]
MODAL_CHOICES = ["Operacoes", "Financeiro", "Suporte", "Compliance"]
REPORT_TARGETS = [
    {"slug": "fiscal", "label": "Relatorio Fiscal - Agosto"},
    {"slug": "fisico", "label": "Relatorio Fisico - Agosto"},
    {"slug": "financeiro", "label": "Relatorio Financeiro - Agosto"},
]
TEAMS = ["Operacoes", "Financeiro", "Suporte"]
DENSITIES = ["compacta", "confortavel"]
LAUNCH_WINDOWS = ["Manha", "Tarde", "Noite"]


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower())
    return normalized.strip("-")


def format_currency(value: float) -> str:
    return f"{value:.2f}"


def build_task_definitions(data: dict) -> dict[str, TaskDefinition]:
    seed_material = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    seed_value = int(hashlib.sha256(seed_material.encode("utf-8")).hexdigest()[:16], 16)
    rng = random.Random(seed_value)

    target_product = rng.choice(data["products"])
    target_order = rng.choice(data["orders"])

    customer_name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
    customer_email = f"{slugify(customer_name)}.{rng.randrange(100, 999)}@example.test"
    customer_city = rng.choice(CITIES)

    status_target = rng.choice(["Pendente", "Concluido"])
    eligible_orders = [order for order in data["orders"] if order["status"] == status_target]
    highest_order = max(eligible_orders, key=lambda order: float(order["total"]))

    customer_candidates = []
    for customer in data["customers"]:
        customer_orders = [order for order in data["orders"] if order["customer_name"] == customer["name"]]
        if len(customer_orders) >= 2:
            most_recent = max(customer_orders, key=lambda order: date.fromisoformat(order["created_at"]))
            customer_candidates.append((customer["name"], most_recent["order_id"]))
    recent_customer_name, recent_order_id = rng.choice(customer_candidates)

    scroll_target = rng.choice(data["products"])
    scroll_token = f"scroll-{rng.randrange(1000, 9999)}"
    modal_choice = rng.choice(MODAL_CHOICES)
    recovery_code = str(rng.randrange(2000, 9999))
    report_target = rng.choice(REPORT_TARGETS)
    journey_team = rng.choice(TEAMS)
    journey_density = rng.choice(DENSITIES)
    journey_launch_window = rng.choice(LAUNCH_WINDOWS)
    journey_review_code = str(rng.randrange(3000, 9999))

    return {
        "t1-product-navigation": TaskDefinition(
            task_id="t1-product-navigation",
            suite="suite-a-controlled",
            title="Navegacao simples",
            objective=f'Acesse a secao Produtos e abra o item "{target_product["name"]}".',
            start_url="/",
            private_context={
                "product_slug": target_product["slug"],
                "product_name": target_product["name"],
            },
        ),
        "t2-create-customer": TaskDefinition(
            task_id="t2-create-customer",
            suite="suite-a-controlled",
            title="Formulario",
            objective=(
                f'Cadastre um cliente chamado {customer_name}, e-mail {customer_email} '
                f"e cidade {customer_city}."
            ),
            start_url="/customers",
            private_context={
                "name": customer_name,
                "email": customer_email,
                "city": customer_city,
            },
        ),
        "t3-open-order": TaskDefinition(
            task_id="t3-open-order",
            suite="suite-a-controlled",
            title="Busca de pedido",
            objective=f'Encontre o pedido numero {target_order["order_id"]} e abra seus detalhes.',
            start_url="/orders",
            private_context={"order_id": target_order["order_id"]},
        ),
        "t4-pending-highest": TaskDefinition(
            task_id="t4-pending-highest",
            suite="suite-a-controlled",
            title="Filtros",
            objective=(
                f"Mostre somente os pedidos com status {status_target} e informe qual tem o maior valor."
            ),
            start_url="/orders",
            requires_answer=True,
            private_context={
                "status": status_target,
                "highest_order_id": highest_order["order_id"],
                "highest_total": format_currency(float(highest_order["total"])),
            },
        ),
        "t5-customer-recent-order": TaskDefinition(
            task_id="t5-customer-recent-order",
            suite="suite-a-controlled",
            title="Multi-step",
            objective=(
                f"Encontre a cliente {recent_customer_name}, abra seus pedidos e informe qual e o mais recente."
            ),
            start_url="/customers",
            requires_answer=True,
            private_context={
                "customer_name": recent_customer_name,
                "customer_slug": slugify(recent_customer_name),
                "recent_order_id": recent_order_id,
            },
        ),
        "t6-scroll-checkpoint": TaskDefinition(
            task_id="t6-scroll-checkpoint",
            suite="suite-a-controlled",
            title="Interface com scroll",
            objective=(
                f'Role ate o fim da pagina e abra o checkpoint "{scroll_target["name"]}" que esta fora da viewport inicial.'
            ),
            start_url="/scroll-lab",
            private_context={
                "scroll_token": scroll_token,
                "target_name": scroll_target["name"],
            },
        ),
        "t7-modal-confirmation": TaskDefinition(
            task_id="t7-modal-confirmation",
            suite="suite-a-controlled",
            title="Modal",
            objective=f"Abra o modal de aprovacao, selecione {modal_choice} e confirme.",
            start_url="/modal-lab",
            private_context={"modal_choice": modal_choice},
        ),
        "t8-recovery-error": TaskDefinition(
            task_id="t8-recovery-error",
            suite="suite-a-controlled",
            title="Recuperacao de erro",
            objective=(
                f"Finalize a revisao do lote coral usando o codigo {recovery_code}. "
                "Se aparecer um erro recuperavel, corrija e conclua."
            ),
            start_url="/recovery-lab",
            private_context={"recovery_code": recovery_code},
        ),
        "t9-visual-ambiguity": TaskDefinition(
            task_id="t9-visual-ambiguity",
            suite="suite-a-controlled",
            title="Pagina visualmente ambigua",
            objective=f'Abra exatamente o painel "{report_target["label"]}".',
            start_url="/ambiguity-lab",
            private_context={
                "report_slug": report_target["slug"],
                "report_label": report_target["label"],
            },
        ),
        "t10-long-journey": TaskDefinition(
            task_id="t10-long-journey",
            suite="suite-a-controlled",
            title="Sequencia longa",
            objective=(
                f"Complete o roteiro longo escolhendo o time {journey_team}, a densidade {journey_density}, "
                f"ativando alertas, usando o codigo {journey_review_code}, selecionando a janela {journey_launch_window} "
                "e finalize o fluxo."
            ),
            start_url="/journey-lab/start",
            private_context={
                "team": journey_team,
                "density": journey_density,
                "review_code": journey_review_code,
                "launch_window": journey_launch_window,
            },
        ),
    }

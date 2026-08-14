from __future__ import annotations

from copy import deepcopy


SEED_DATA = {
    "products": [
        {
            "slug": "teclado-mecanico",
            "name": "Teclado Mecanico",
            "category": "Perifericos",
            "price": 489.90,
            "stock": 18,
            "summary": "Switch tactil, layout ABNT2 e retroiluminacao branca.",
        },
        {
            "slug": "mouse-ergonomico",
            "name": "Mouse Ergonomico",
            "category": "Perifericos",
            "price": 229.50,
            "stock": 34,
            "summary": "Sensor preciso e pegada vertical para uso prolongado.",
        },
        {
            "slug": "monitor-ultrawide",
            "name": "Monitor Ultrawide 34",
            "category": "Monitores",
            "price": 2799.00,
            "stock": 7,
            "summary": "Painel 34 polegadas com alta area util para multitarefa.",
        },
        {
            "slug": "notebook-station",
            "name": "Notebook Station Dock",
            "category": "Acessorios",
            "price": 699.00,
            "stock": 12,
            "summary": "Dock USB-C com video, rede e portas adicionais.",
        },
    ],
    "customers": [
        {"name": "Maria Oliveira", "email": "maria.oliveira@example.test", "city": "Sao Paulo"},
        {"name": "Carlos Pereira", "email": "carlos.pereira@example.test", "city": "Curitiba"},
        {"name": "Ana Souza", "email": "ana.souza@example.test", "city": "Recife"},
    ],
    "orders": [
        {"order_id": 10480, "customer_name": "Carlos Pereira", "status": "Concluido", "total": 129.90, "created_at": "2026-07-12"},
        {"order_id": 10481, "customer_name": "Ana Souza", "status": "Pendente", "total": 899.00, "created_at": "2026-07-18"},
        {"order_id": 10482, "customer_name": "Maria Oliveira", "status": "Concluido", "total": 459.90, "created_at": "2026-07-22"},
        {"order_id": 10483, "customer_name": "Carlos Pereira", "status": "Pendente", "total": 1499.90, "created_at": "2026-07-23"},
        {"order_id": 10484, "customer_name": "Ana Souza", "status": "Cancelado", "total": 219.00, "created_at": "2026-07-24"},
        {"order_id": 10485, "customer_name": "Maria Oliveira", "status": "Pendente", "total": 319.00, "created_at": "2026-07-26"},
        {"order_id": 10486, "customer_name": "Carlos Pereira", "status": "Concluido", "total": 529.90, "created_at": "2026-07-29"},
        {"order_id": 10487, "customer_name": "Ana Souza", "status": "Pendente", "total": 4599.90, "created_at": "2026-08-01"},
        {"order_id": 10488, "customer_name": "Maria Oliveira", "status": "Concluido", "total": 999.00, "created_at": "2026-08-02"},
        {"order_id": 10489, "customer_name": "Carlos Pereira", "status": "Pendente", "total": 199.90, "created_at": "2026-08-03"},
        {"order_id": 10490, "customer_name": "Maria Oliveira", "status": "Concluido", "total": 749.50, "created_at": "2026-08-04"},
        {"order_id": 10491, "customer_name": "Ana Souza", "status": "Pendente", "total": 249.90, "created_at": "2026-08-05"},
        {"order_id": 10492, "customer_name": "Maria Oliveira", "status": "Concluido", "total": 1879.00, "created_at": "2026-08-06"},
    ],
    "notes": [
        "Revise os pedidos pendentes diariamente.",
        "Clientes VIP recebem prioridade no atendimento.",
        "Produtos sem estoque devem ser sinalizados na tela inicial.",
    ],
}


def clone_seed_data() -> dict:
    return deepcopy(SEED_DATA)

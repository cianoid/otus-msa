"""Shared saga helpers: step order and outbox entry builders.

Used by both the request handler (`api/order.py`) and the saga recovery worker
(`services/saga_recovery.py`) so that compensations and the notification are
built identically regardless of who finalizes the saga.
"""

from __future__ import annotations

import datetime as dt

import jwt

from src.core.config import settings
from src.models import OrderDB, SagaStepDB

# Saga steps in execution order; compensations are emitted in reverse.
STEP_ORDER = ("warehouse_reserve", "delivery_reserve", "billing_withdraw")


def mint_service_token(username: str) -> str:
    """Mint a short-lived service JWT for downstream calls (participants validate JWT locally)."""
    expire = dt.datetime.now(dt.UTC) + dt.timedelta(seconds=settings.saga_recovery_token_ttl_seconds)
    payload = {"sub": username, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def build_outbox_entries(
    *,
    order: OrderDB,
    steps: list[SagaStepDB],
    success: bool,
    email: str | None,
    token: str,
    error: str,
) -> list[dict]:
    """Build outbox entries: compensations for completed steps (on failure) + notification."""
    by_name = {step.step_name: step for step in steps}
    entries: list[dict] = []

    if not success:
        billing = by_name.get("billing_withdraw")
        if billing is not None and billing.status == "completed":
            entries.append(
                {
                    "kind": "compensation_billing",
                    "payload": {
                        "username": order.username,
                        "amount": billing.request_payload["amount"],
                        "token": token,
                        "idempotency_key": order.idempotency_key,
                    },
                }
            )
        delivery = by_name.get("delivery_reserve")
        if delivery is not None and delivery.status == "completed" and delivery.reservation_id:
            entries.append(
                {
                    "kind": "compensation_delivery",
                    "payload": {
                        "reservation_id": delivery.reservation_id,
                        "username": order.username,
                        "token": token,
                        "idempotency_key": order.idempotency_key,
                    },
                }
            )
        warehouse = by_name.get("warehouse_reserve")
        if warehouse is not None and warehouse.status == "completed" and warehouse.reservation_id:
            entries.append(
                {
                    "kind": "compensation_warehouse",
                    "payload": {
                        "reservation_id": warehouse.reservation_id,
                        "username": order.username,
                        "token": token,
                        "idempotency_key": order.idempotency_key,
                    },
                }
            )

    billing_step = by_name.get("billing_withdraw")
    billing_result = (billing_step.result_payload if billing_step else None) or {}
    entries.append(
        {
            "kind": "notification",
            "payload": {
                "notification_id": str(order.id),
                "message_type": "ORDER_SUCCESS" if success else "ORDER_FAILED",
                "username": order.username,
                "email": email,
                "data": {
                    "order_id": str(order.id),
                    "price": str(order.price),
                    "balance": str(billing_result.get("balance", "0.00")),
                    "error": error,
                },
            },
        }
    )
    return entries

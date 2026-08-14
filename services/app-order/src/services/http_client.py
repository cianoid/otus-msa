"""HTTP clients for synchronous service-to-service calls."""

from __future__ import annotations

from decimal import Decimal

import httpx
from src.core.config import settings
from src.core.logger import log
from src.core.tracing import start_span


class ServiceClient:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=5.0)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def withdraw_from_billing(self, username: str, amount: Decimal, token: str) -> dict:
        """Call billing service to withdraw money. Returns billing response."""
        with start_span(
            "http.billing.withdraw", attributes={"billing.username": username, "billing.amount": str(amount)}
        ):
            client = await self._get_client()
            url = f"{settings.billing_service_url}/api/v1/billing/withdraw"
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.post(url, json={"amount": str(amount)}, headers=headers)
            log.info("billing withdraw: username=%s status=%s body=%s", username, response.status_code, response.text)
            response.raise_for_status()
            return response.json()

    async def get_user_profile(self, token: str) -> dict:
        """Call user service to get current user profile."""
        with start_span("http.user.profile"):
            client = await self._get_client()
            url = f"{settings.user_service_url}/api/v1/profile"
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.get(url, headers=headers)
            log.info("user profile: status=%s body=%s", response.status_code, response.text)
            response.raise_for_status()
            return response.json()

    async def reserve_warehouse(self, order_id: str, product_id: int, quantity: int, token: str) -> dict:
        """Call warehouse service to reserve product stock."""
        with start_span(
            "http.warehouse.reserve",
            attributes={"order.id": order_id, "warehouse.product_id": product_id, "warehouse.quantity": quantity},
        ):
            client = await self._get_client()
            url = f"{settings.warehouse_service_url}/api/v1/warehouse/reserve"
            headers = {"Authorization": f"Bearer {token}"}
            body = {"order_id": order_id, "product_id": product_id, "quantity": quantity}
            response = await client.post(url, json=body, headers=headers)
            log.info("warehouse reserve: order_id=%s status=%s body=%s", order_id, response.status_code, response.text)
            response.raise_for_status()
            return response.json()

    async def cancel_warehouse_reservation(self, reservation_id: str, token: str) -> dict:
        """Compensation: cancel warehouse reservation and return stock."""
        with start_span("http.warehouse.cancel", attributes={"warehouse.reservation_id": reservation_id}):
            client = await self._get_client()
            url = f"{settings.warehouse_service_url}/api/v1/warehouse/cancel"
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.post(url, json={"reservation_id": reservation_id}, headers=headers)
            log.info(
                "warehouse cancel: reservation_id=%s status=%s body=%s",
                reservation_id,
                response.status_code,
                response.text,
            )
            response.raise_for_status()
            return response.json()

    async def reserve_delivery(self, order_id: str, slot_id: int, token: str) -> dict:
        """Call delivery service to reserve a courier slot."""
        with start_span(
            "http.delivery.reserve",
            attributes={"order.id": order_id, "delivery.slot_id": slot_id},
        ):
            client = await self._get_client()
            url = f"{settings.delivery_service_url}/api/v1/delivery/reserve"
            headers = {"Authorization": f"Bearer {token}"}
            body = {"order_id": order_id, "slot_id": slot_id}
            response = await client.post(url, json=body, headers=headers)
            log.info("delivery reserve: order_id=%s status=%s body=%s", order_id, response.status_code, response.text)
            response.raise_for_status()
            return response.json()

    async def cancel_delivery_reservation(self, reservation_id: str, token: str) -> dict:
        """Compensation: cancel delivery reservation."""
        with start_span("http.delivery.cancel", attributes={"delivery.reservation_id": reservation_id}):
            client = await self._get_client()
            url = f"{settings.delivery_service_url}/api/v1/delivery/cancel"
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.post(url, json={"reservation_id": reservation_id}, headers=headers)
            log.info(
                "delivery cancel: reservation_id=%s status=%s body=%s",
                reservation_id,
                response.status_code,
                response.text,
            )
            response.raise_for_status()
            return response.json()

    async def refund_billing(self, username: str, amount: Decimal, token: str) -> dict:
        """Compensation: deposit money back to the user balance."""
        with start_span(
            "http.billing.deposit", attributes={"billing.username": username, "billing.amount": str(amount)}
        ):
            client = await self._get_client()
            url = f"{settings.billing_service_url}/api/v1/billing/deposit"
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.post(url, json={"amount": str(amount)}, headers=headers)
            log.info("billing deposit: username=%s status=%s body=%s", username, response.status_code, response.text)
            response.raise_for_status()
            return response.json()

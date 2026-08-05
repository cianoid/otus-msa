"""HTTP clients for synchronous service-to-service calls."""

from __future__ import annotations

from decimal import Decimal

import httpx
from src.core.config import settings
from src.core.logger import log


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
        client = await self._get_client()
        url = f"{settings.billing_service_url}/api/v1/billing/withdraw"
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.post(url, json={"amount": str(amount)}, headers=headers)
        log.info("billing withdraw: username=%s status=%s body=%s", username, response.status_code, response.text)
        response.raise_for_status()
        return response.json()

    async def get_user_profile(self, token: str) -> dict:
        """Call user service to get current user profile."""
        client = await self._get_client()
        url = f"{settings.user_service_url}/api/v1/profile"
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get(url, headers=headers)
        log.info("user profile: status=%s body=%s", response.status_code, response.text)
        response.raise_for_status()
        return response.json()

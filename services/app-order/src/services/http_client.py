"""HTTP clients for synchronous service-to-service calls with retry and circuit breaker."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from decimal import Decimal
from functools import wraps
from typing import Any, Self, TypeVar

import httpx
from aiobreaker import CircuitBreaker
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from src.core.config import settings
from src.core.logger import log
from src.core.tracing import start_span

F = TypeVar("F", bound=Callable[..., Any])


class _CircuitBreakerWrapper:
    """Thin wrapper around aiobreaker.CircuitBreaker to make it usable as a decorator."""

    def __init__(self, name: str, fail_max: int, timeout: int) -> None:
        self.name = name
        self._breaker = CircuitBreaker(fail_max=fail_max, timeout_duration=timeout)

    def __call__(self, fn: F) -> F:
        @wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await self._breaker(fn)(*args, **kwargs)

        return wrapper  # type: ignore[return-value]


def _transient_error(exc: BaseException) -> bool:
    """Return True for errors worth retrying: connect/timeout/network and 5xx/429."""
    if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError, asyncio.TimeoutError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return code >= 500 or code == 429
    return False


def _saga_retry() -> Callable[[F], F]:
    return retry(  # type: ignore[return-value]
        wait=wait_exponential_jitter(
            initial=settings.saga_retry_min_seconds,
            max=settings.saga_retry_max_seconds,
            jitter=settings.saga_retry_jitter,
        ),
        stop=stop_after_attempt(settings.saga_retry_max_attempts),
        retry=retry_if_exception(_transient_error),
        reraise=True,
        before_sleep=before_sleep_log(log, "warning"),
    )


# Circuit breakers per downstream service.
_billing_circuit = _CircuitBreakerWrapper(
    "billing", settings.circuit_breaker_fail_max, settings.circuit_breaker_timeout
)
_warehouse_circuit = _CircuitBreakerWrapper(
    "warehouse", settings.circuit_breaker_fail_max, settings.circuit_breaker_timeout
)
_delivery_circuit = _CircuitBreakerWrapper(
    "delivery", settings.circuit_breaker_fail_max, settings.circuit_breaker_timeout
)
_user_circuit = _CircuitBreakerWrapper("user", settings.circuit_breaker_fail_max, settings.circuit_breaker_timeout)


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

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    @staticmethod
    def _headers(token: str, idempotency_key: str | None = None) -> dict[str, str]:
        headers: dict[str, str] = {"Authorization": f"Bearer {token}"}
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key
        return headers

    @_billing_circuit
    @_saga_retry()
    async def withdraw_from_billing(
        self, username: str, amount: Decimal, token: str, idempotency_key: str | None = None
    ) -> dict:
        """Call billing service to withdraw money. Returns billing response."""
        with start_span(
            "http.billing.withdraw", attributes={"billing.username": username, "billing.amount": str(amount)}
        ):
            client = await self._get_client()
            url = f"{settings.billing_service_url}/api/v1/billing/withdraw"
            response = await client.post(
                url,
                json={"amount": str(amount)},
                headers=self._headers(token, idempotency_key),
            )
            log.info("billing withdraw: username=%s status=%s body=%s", username, response.status_code, response.text)
            response.raise_for_status()
            return response.json()

    @_user_circuit
    @_saga_retry()
    async def get_user_profile(self, token: str, idempotency_key: str | None = None) -> dict:
        """Call user service to get current user profile."""
        with start_span("http.user.profile"):
            client = await self._get_client()
            url = f"{settings.user_service_url}/api/v1/profile"
            response = await client.get(url, headers=self._headers(token, idempotency_key))
            log.info("user profile: status=%s body=%s", response.status_code, response.text)
            response.raise_for_status()
            return response.json()

    @_warehouse_circuit
    @_saga_retry()
    async def reserve_warehouse(
        self,
        order_id: str,
        product_id: int,
        quantity: int,
        token: str,
        idempotency_key: str | None = None,
    ) -> dict:
        """Call warehouse service to reserve product stock."""
        with start_span(
            "http.warehouse.reserve",
            attributes={"order.id": order_id, "warehouse.product_id": product_id, "warehouse.quantity": quantity},
        ):
            client = await self._get_client()
            url = f"{settings.warehouse_service_url}/api/v1/warehouse/reserve"
            body = {"order_id": order_id, "product_id": product_id, "quantity": quantity}
            response = await client.post(url, json=body, headers=self._headers(token, idempotency_key))
            log.info("warehouse reserve: order_id=%s status=%s body=%s", order_id, response.status_code, response.text)
            response.raise_for_status()
            return response.json()

    @_warehouse_circuit
    @_saga_retry()
    async def cancel_warehouse_reservation(
        self, reservation_id: str, token: str, idempotency_key: str | None = None
    ) -> dict:
        """Compensation: cancel warehouse reservation and return stock."""
        with start_span("http.warehouse.cancel", attributes={"warehouse.reservation_id": reservation_id}):
            client = await self._get_client()
            url = f"{settings.warehouse_service_url}/api/v1/warehouse/cancel"
            response = await client.post(
                url,
                json={"reservation_id": reservation_id},
                headers=self._headers(token, idempotency_key),
            )
            log.info(
                "warehouse cancel: reservation_id=%s status=%s body=%s",
                reservation_id,
                response.status_code,
                response.text,
            )
            response.raise_for_status()
            return response.json()

    @_delivery_circuit
    @_saga_retry()
    async def reserve_delivery(
        self, order_id: str, slot_id: int, token: str, idempotency_key: str | None = None
    ) -> dict:
        """Call delivery service to reserve a courier slot."""
        with start_span(
            "http.delivery.reserve",
            attributes={"order.id": order_id, "delivery.slot_id": slot_id},
        ):
            client = await self._get_client()
            url = f"{settings.delivery_service_url}/api/v1/delivery/reserve"
            body = {"order_id": order_id, "slot_id": slot_id}
            response = await client.post(url, json=body, headers=self._headers(token, idempotency_key))
            log.info("delivery reserve: order_id=%s status=%s body=%s", order_id, response.status_code, response.text)
            response.raise_for_status()
            return response.json()

    @_delivery_circuit
    @_saga_retry()
    async def cancel_delivery_reservation(
        self, reservation_id: str, token: str, idempotency_key: str | None = None
    ) -> dict:
        """Compensation: cancel delivery reservation."""
        with start_span("http.delivery.cancel", attributes={"delivery.reservation_id": reservation_id}):
            client = await self._get_client()
            url = f"{settings.delivery_service_url}/api/v1/delivery/cancel"
            response = await client.post(
                url,
                json={"reservation_id": reservation_id},
                headers=self._headers(token, idempotency_key),
            )
            log.info(
                "delivery cancel: reservation_id=%s status=%s body=%s",
                reservation_id,
                response.status_code,
                response.text,
            )
            response.raise_for_status()
            return response.json()

    @_billing_circuit
    @_saga_retry()
    async def refund_billing(
        self, username: str, amount: Decimal, token: str, idempotency_key: str | None = None
    ) -> dict:
        """Compensation: deposit money back to the user balance."""
        with start_span(
            "http.billing.deposit", attributes={"billing.username": username, "billing.amount": str(amount)}
        ):
            client = await self._get_client()
            url = f"{settings.billing_service_url}/api/v1/billing/deposit"
            response = await client.post(
                url,
                json={"amount": str(amount)},
                headers=self._headers(token, idempotency_key),
            )
            log.info("billing deposit: username=%s status=%s body=%s", username, response.status_code, response.text)
            response.raise_for_status()
            return response.json()

"""Custom Prometheus metrics for business-level observability."""

from prometheus_client import Counter, Gauge

_ORDER_STATUSES = ("created", "paid", "failed")
_COMPENSATION_KINDS = ("compensation_delivery", "compensation_warehouse", "compensation_billing")
_OUTBOX_KINDS = ("compensation_delivery", "compensation_warehouse", "compensation_billing", "notification")
_OUTBOX_STATUSES = ("pending", "processing", "processed", "failed")
_SAGA_RECOVERY_RESULTS = ("paid", "failed", "error")

# Counter for order lifecycle events.
orders_total = Counter(
    "orders_total",
    "Total number of orders created by status",
    ["status"],
)

# Counter for saga compensations emitted to the outbox.
order_compensations_total = Counter(
    "order_compensations_total",
    "Total number of order saga compensations emitted",
    ["kind"],
)

# Counter for outbox message transitions.
outbox_messages_total = Counter(
    "outbox_messages_total",
    "Total number of outbox message state transitions",
    ["kind", "status"],
)

# Counter for outbox messages that exhausted retries (DLQ).
outbox_dlq_messages_total = Counter(
    "outbox_dlq_messages_total",
    "Total number of outbox messages moved to DLQ after exhausting retries",
    ["kind"],
)

# Gauge for the current number of pending outbox messages.
outbox_pending_messages = Gauge(
    "outbox_pending_messages",
    "Current number of pending outbox messages",
    ["kind"],
)

# Counter for sagas finalized by the recovery worker (stuck-saga repair).
saga_recovery_total = Counter(
    "saga_recovery_total",
    "Total number of stuck sagas finalized by the recovery worker",
    ["result"],
)

# Initialise counters so that recording rules and dashboards always see the series,
# even before the first event occurs.
for _status in _ORDER_STATUSES:
    orders_total.labels(status=_status)

for _kind in _COMPENSATION_KINDS:
    order_compensations_total.labels(kind=_kind)

for _kind in _OUTBOX_KINDS:
    outbox_pending_messages.labels(kind=_kind)
    outbox_dlq_messages_total.labels(kind=_kind)
    for _status in _OUTBOX_STATUSES:
        outbox_messages_total.labels(kind=_kind, status=_status)

for _result in _SAGA_RECOVERY_RESULTS:
    saga_recovery_total.labels(result=_result)

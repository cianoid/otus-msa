# app-order: saga improvements (round 3 — review fixes)

Follow-up fixes found on review of the round-2 changes:

1. **`compensation_billing` crashed the outbox worker with `KeyError`**
   - `OutboxWorker._process_compensation` read `payload["reservation_id"]`
     unconditionally, but the billing-refund payload has no `reservation_id`
     (only `username`/`amount`). The read is now per-kind.

2. **Compensation JWT could expire before the outbox retry budget ran out**
   - User access tokens live 30 min; recovery-minted tokens 600s, while outbox
     retries span ~15+ min and a saga can sit stuck for 15 min before recovery.
     An expired token means 401s, wasted attempts and eventual DLQ.
   - The outbox worker now mints a FRESH service JWT per attempt via the shared
     `mint_service_token` (`src/services/saga.py`); `username` was added to the
     delivery/warehouse compensation payloads for this. Legacy rows without
     `username` fall back to the stored token.
   - `SagaRecoveryWorker` reuses the same shared helper.

3. **Lint cleanup**: removed a stale `# noqa: F403` in `src/main.py` (RUF100).

# app-order: saga improvements (round 2 — consistency fixes)

Fixes for the remaining consistency gaps (outbox atomicity, guaranteed
compensations, stuck-saga repair):

1. **Outbox is now atomic with the order commit**
   - New `OrderCRUD.finalize_order_with_outbox` (`services/app-order/src/crud.py`)
     updates the order status AND inserts outbox entries (compensations +
     notification) in a single DB transaction. Previously the Kafka notification
     (`message.send.email`) and compensations were enqueued in a separate commit
     after the order update, so a crash in between lost them.
   - Unique constraint `uq_outbox_order_kind` on `outbox(order_id, kind)`
     (migration `d4e5f6a7b8c9_007_outbox_unique_order_kind`) + `ON CONFLICT DO
     NOTHING` makes enqueuing idempotent (request handler vs. recovery race).
   - `KafkaClient.send_notification` now re-raises send errors instead of
     swallowing them, so the outbox worker actually retries failed Kafka sends
     instead of marking the entry processed.

2. **Guaranteed compensations**
   - Compensations are committed atomically with the `failed` order status (see 1),
     so they cannot be lost once the saga outcome is known.
   - Outbox entries are built by the shared `src/services/saga.py`
     (`build_outbox_entries`) used by both the request handler and the recovery
     worker; it also covers `compensation_billing` (refund) for completed steps.

3. **Stuck-saga detection and repair**
   - New `SagaRecoveryWorker` (`services/app-order/src/services/saga_recovery.py`,
     started in `lifespan`) polls for orders stuck in `pending` longer than
     `SAGA_STUCK_THRESHOLD_SECONDS` (default 900s, must exceed worst-case
     request-path saga duration).
   - For each stuck order it resumes unfinished steps (`pending`/`in_progress`)
     re-calling participants with the ORIGINAL idempotency key (downstream
     idempotency makes this safe), then finalizes the saga via the same atomic
     `finalize_order_with_outbox` (compensations + notification).
   - The worker mints a short-lived service JWT (`SAGA_RECOVERY_TOKEN_TTL_SECONDS`,
     default 600s) with the shared JWT secret, since the original user token is
     not persisted; participants validate JWT locally.
   - New settings: `SAGA_RECOVERY_POLL_INTERVAL_SECONDS` (30),
     `SAGA_RECOVERY_BATCH_SIZE` (10), `SAGA_STUCK_THRESHOLD_SECONDS` (900),
     `SAGA_RECOVERY_TOKEN_TTL_SECONDS` (600).
   - New metric `saga_recovery_total{result=paid|failed|error}`.

# app-order: saga improvements

Changes made to address saga reliability feedback:

1. **Retry + Circuit Breaker**
   - Added `tenacity` retry with exponential backoff/jitter and `aiobreaker` circuit breaker in `services/app-order/src/services/http_client.py`.
   - One circuit breaker per downstream service (`billing`, `warehouse`, `delivery`, `user`).
   - Retry only on transient errors (connect/timeout/network, 5xx, 429), not on 4xx or `success=false` responses.
   - Forward `X-Idempotency-Key` header to all mutating downstream calls.

2. **Persistent saga state**
   - New tables: `saga_steps` and `outbox` (migration `005_saga_and_outbox`).
   - `POST /api/v1/order` now creates an `orders` row in `pending` status plus `saga_steps` rows before executing the saga.
   - Each step updates its DB state (`pending` → `in_progress` → `completed`/`failed`) so progress survives an orchestrator restart.

3. **Guaranteed compensations / outbox pattern**
   - On failure, compensations are enqueued in the `outbox` table instead of being executed inline.
   - A background `OutboxWorker` (started in `lifespan`) polls pending outbox entries using `SELECT ... FOR UPDATE SKIP LOCKED`, executes compensations with retries, and sends Kafka notifications.
   - Failed entries are retried with exponential backoff up to `OUTBOX_MAX_ATTEMPTS`.

# app-warehouse / app-delivery / app-billing: idempotency support

To make the saga retry safe, the three participant services now support the `X-Idempotency-Key` header on mutating endpoints:

- `app-warehouse`: `POST /api/v1/warehouse/reserve`, `POST /api/v1/warehouse/cancel`
- `app-delivery`: `POST /api/v1/delivery/reserve`, `POST /api/v1/delivery/cancel`
- `app-billing`: `POST /api/v1/billing/withdraw`, `POST /api/v1/billing/deposit`

Each service has a new `idempotency_keys` table (`idempotency_key`, `kind`, `payload`) with a unique constraint on `(idempotency_key, kind)`. The stored response is returned for duplicate keys, so retries from `app-order` never create double reservations or double charges.

# Helm
1. `helm template` - проверяем корректность манифестов
2. `helm install --dry-run` - проверяем, что манифест установится в кластер 

# Minikube
1. `minikube start --driver=vfkit` (для Apple Silicon. Но нужно пакет поставить сперва `brew install vfkit`)
2. `minikube start --driver=docker` (или другой вариант, если первый не завелся)

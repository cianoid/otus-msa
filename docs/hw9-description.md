# ДЗ «Идемпотентность и коммутативность API в HTTP и очередях»

## Выбранный паттерн

Для метода создания заказа `POST /api/v1/order` (сервис `app-order`) реализован паттерн
**Idempotency Key** (ключ идемпотентности):

- Клиент генерирует UUID и передаёт его в HTTP-заголовке `Idempotency-Key`.
- Перед запуском саги создания заказа `app-order` ищет в БД заказ с парой
  `(username, idempotency_key)`:
  - заказ найден → сага **не выполняется**, клиенту возвращается ранее сохранённый заказ
    с исходным HTTP-кодом ответа (`201` для `paid`, `409` для `failed`);
  - заказ не найден → выполняется сага (warehouse → delivery → billing), заказ сохраняется
    вместе с ключом идемпотентности.
- Заголовок **обязательный**: запрос без `Idempotency-Key` отклоняется с `422`
  (валидация FastAPI) до любых побочных эффектов.

### Почему выбран этот паттерн

- Это стандартный способ идемпотентности для HTTP API.
- Не требует менять контракт тела запроса и логику участников саги.
- Уникальный индекс в Postgres даёт exactly-once семантику сохранения заказа даже при
  параллельных ретраях.

### Схема взаимодействия

Исходник Mermaid: [hw9-architecture.mermaid](hw9-architecture.mermaid).

## Команда установки приложения

Namespace — **`default`**. Установка описана в [readme.md](../readme.md#установка-приложения):

## Запуск тестов Postman

Коллекция: [postman/otus-msa-hw9.postman_collection.json](../postman/otus-msa-hw9.postman_collection.json)

```shell
newman run postman/otus-msa-hw9.postman_collection.json
```

`baseUrl` уже задан в коллекции (`arch.homework`). При необходимости его можно переопределить.


## Результат работы тестов

```
newman

OTUS MSA HW9 — Idempotency (Idempotency-Key)

❏ 1. Auth
↳ Register user
  POST http://arch.homework/api/v1/auth/register [201 Created, 498B, 63ms]
  ┌
  │ 'REQUEST:', 'Register user', 'POST', 'http://arch.home
  │ work/api/v1/auth/register'
  │ 'REQUEST BODY:', '{\n' +
  │   '  "username": "Katlyn26",\n' +
  │   '  "email": "Dominique72@cianoid.ru",\n' +
  │   '  "password": "password123"\n' +
  │   '}'
  │ 'RESPONSE:', 201, '{"access_token":"eyJhbGciOiJIUzI1Ni
  │ IsInR5cCI6IkpXVCJ9.eyJzdWIiOiJLYXRseW4yNiIsImV4cCI6MTc
  │ 4NjgxMzYyMSwidHlwZSI6ImFjY2VzcyJ9.8O4BqR_vduR-IU6tRAro
  │ LuX4SRWQzOHM2WwvZm4uvdk","refresh_token":"eyJhbGciOiJI
  │ UzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJLYXRseW4yNiIsImV4c
  │ CI6MTc4NzQxNjYyMSwidHlwZSI6InJlZnJlc2gifQ.W4vYDvJNCNN7
  │ 7nA5_KuT-EVWD0EdwD4r_fn208BjEJk","token_type":"bearer"
  │ }'
  └
  ✓  Status is 201

↳ Login
  POST http://arch.homework/api/v1/auth/login [200 OK, 493B, 27ms]
  ┌
  │ 'REQUEST:', 'Login', 'POST', 'http://arch.homework/api
  │ /v1/auth/login'
  │ 'REQUEST BODY:', '{\n' +
  │   '  "username": "Katlyn26",\n' +
  │   '  "password": "password123"\n' +
  │   '}'
  │ 'RESPONSE:', 200, '{"access_token":"eyJhbGciOiJIUzI1Ni
  │ IsInR5cCI6IkpXVCJ9.eyJzdWIiOiJLYXRseW4yNiIsImV4cCI6MTc
  │ 4NjgxMzYyMSwidHlwZSI6ImFjY2VzcyJ9.8O4BqR_vduR-IU6tRAro
  │ LuX4SRWQzOHM2WwvZm4uvdk","refresh_token":"eyJhbGciOiJI
  │ UzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJLYXRseW4yNiIsImV4c
  │ CI6MTc4NzQxNjYyMSwidHlwZSI6InJlZnJlc2gifQ.W4vYDvJNCNN7
  │ 7nA5_KuT-EVWD0EdwD4r_fn208BjEJk","token_type":"bearer"
  │ }'
  └
  ✓  Status is 200

❏ 2. Setup (billing, warehouse, delivery)
↳ Deposit money
  POST http://arch.homework/api/v1/billing/deposit [200 OK, 175B, 6ms]
  ┌
  │ 'REQUEST:', 'Deposit money', 'POST', 'http://arch.home
  │ work/api/v1/billing/deposit'
  │ 'REQUEST BODY:', '{\n  "amount": "1000"\n}'
  │ 'RESPONSE:', 200, '{"username":"Katlyn26","balance":"1
  │ 000.00"}'
  └
  ✓  Status is 200
  ✓  Billing account created, balance equals deposit

↳ Create product
  POST http://arch.homework/api/v1/warehouse/products [201 Created, 175B, 8ms]
  ┌
  │ 'REQUEST:', 'Create product', 'POST', 'http://arch.hom
  │ ework/api/v1/warehouse/products'
  │ 'REQUEST BODY:', '{\n  "name": "Test Phone",\n  "stock
  │ ": 5\n}'
  │ 'RESPONSE:', 201, '{"id":7,"name":"Test Phone","stock"
  │ :5}'
  └
  ✓  Status is 201

↳ Create delivery slot
  POST http://arch.homework/api/v1/delivery/slots [201 Created, 209B, 6ms]
  ┌
  │ 'REQUEST:', 'Create delivery slot', 'POST', 'http://ar
  │ ch.homework/api/v1/delivery/slots'
  │ 'REQUEST BODY:', '{\n' +
  │   '  "time_slot": "2026-02-01 10:00-12:00",\n' +
  │   '  "capacity": 1\n' +
  │   '}'
  │ 'RESPONSE:', 201, '{"id":12,"time_slot":"2026-02-01 10
  │ :00-12:00","capacity":1,"reserved":0}'
  └
  ✓  Status is 201

❏ 3. Order with Idempotency-Key + replay
↳ Create order (with Idempotency-Key)
  ┌
  │ 'IDEMPOTENCY KEY:', '67d2c824-8c27-4628-9c46-fb30d1d11
  │ cde'
  └
  POST http://arch.homework/api/v1/order [201 Created, 390B, 88ms]
  ┌
  │ 'REQUEST:', 'Create order (with Idempotency-Key)', 'PO
  │ ST', 'http://arch.homework/api/v1/order'
  │ 'REQUEST BODY:', '{\n' +
  │   '  "price": 500,\n' +
  │   '  "product_id": 7,\n' +
  │   '  "quantity": 1,\n' +
  │   '  "slot_id": 12\n' +
  │   '}'
  │ 'RESPONSE:', 201, '{"id":"70d41dc9-bcaa-4046-b13a-6fa4
  │ 581c88a2","username":"Katlyn26","price":"500.00","stat
  │ us":"paid","product_id":7,"quantity":1,"slot_id":12,"c
  │ reated_at":"2026-08-15T16:37:01.362926Z","error":"","i
  │ dempotency_key":"67d2c824-8c27-4628-9c46-fb30d1d11cde"
  │ }'
  └
  ✓  Status is 201
  ✓  Order status is paid
  ✓  Idempotency key stored in order

↳ Replay same order (same Idempotency-Key)
  POST http://arch.homework/api/v1/order [201 Created, 390B, 5ms]
  ┌
  │ 'REQUEST:', 'Replay same order (same Idempotency-Key)'
  │ , 'POST', 'http://arch.homework/api/v1/order'
  │ 'REQUEST BODY:', '{\n' +
  │   '  "price": 500,\n' +
  │   '  "product_id": 7,\n' +
  │   '  "quantity": 1,\n' +
  │   '  "slot_id": 12\n' +
  │   '}'
  │ 'RESPONSE:', 201, '{"id":"70d41dc9-bcaa-4046-b13a-6fa4
  │ 581c88a2","username":"Katlyn26","price":"500.00","stat
  │ us":"paid","product_id":7,"quantity":1,"slot_id":12,"c
  │ reated_at":"2026-08-15T16:37:01.362926Z","error":"","i
  │ dempotency_key":"67d2c824-8c27-4628-9c46-fb30d1d11cde"
  │ }'
  └
  ✓  Status is 201 (same as original)
  ✓  Same order id returned (no duplicate)
  ✓  Order status is still paid

↳ Check balance decreased only once
  GET http://arch.homework/api/v1/billing/account [200 OK, 174B, 5ms]
  ┌
  │ 'REQUEST:', 'Check balance decreased only once', 'GET'
  │ , 'http://arch.homework/api/v1/billing/account'
  │ 'REQUEST BODY: <none>'
  │ 'RESPONSE:', 200, '{"username":"Katlyn26","balance":"5
  │ 00.00"}'
  └
  ✓  Status is 200
  ✓  Balance decreased by exactly one order price

↳ Check stock decreased only once
  GET http://arch.homework/api/v1/warehouse/products [200 OK, 407B, 4ms]
  ┌
  │ 'REQUEST:', 'Check stock decreased only once', 'GET', 
  │ 'http://arch.homework/api/v1/warehouse/products'
  │ 'REQUEST BODY: <none>'
  │ 'RESPONSE:', 200, '[{"id":1,"name":"Test Phone","stock
  │ ":9},{"id":2,"name":"Test Phone","stock":4},{"id":3,"n
  │ ame":"Test Phone","stock":4},{"id":4,"name":"Test Phon
  │ e","stock":4},{"id":5,"name":"Test Phone","stock":3},{
  │ "id":6,"name":"Test Phone","stock":3},{"id":7,"name":"
  │ Test Phone","stock":4}]'
  └
  ✓  Status is 200
  ✓  Product stock decreased by exactly 1

↳ Check slot reserved only once
  GET http://arch.homework/api/v1/delivery/slots [200 OK, 1kB, 4ms]
  ┌
  │ 'REQUEST:', 'Check slot reserved only once', 'GET', 'h
  │ ttp://arch.homework/api/v1/delivery/slots'
  │ 'REQUEST BODY: <none>'
  │ 'RESPONSE:', 200, '[{"id":1,"time_slot":"2026-01-01 10
  │ :00-12:00","capacity":1,"reserved":1},{"id":2,"time_sl
  │ ot":"2026-01-01 10:00-12:00","capacity":1,"reserved":1
  │ },{"id":3,"time_slot":"2026-01-02 10:00-12:00","capaci
  │ ty":1,"reserved":0},{"id":4,"time_slot":"2026-01-01 10
  │ :00-12:00","capacity":1,"reserved":1},{"id":5,"time_sl
  │ ot":"2026-01-02 10:00-12:00","capacity":1,"reserved":0
  │ },{"id":6,"time_slot":"2026-01-01 10:00-12:00","capaci
  │ ty":1,"reserved":1},{"id":7,"time_slot":"2026-01-02 10
  │ :00-12:00","capacity":1,"reserved":0},{"id":8,"time_sl
  │ ot":"2026-02-01 10:00-12:00","capacity":1,"reserved":1
  │ },{"id":9,"time_slot":"2026-02-02 10:00-12:00","capaci
  │ ty":1,"reserved":1},{"id":10,"time_slot":"2026-02-01 1
  │ 0:00-12:00","capacity":1,"reserved":1},{"id":11,"time_
  │ slot":"2026-02-02 10:00-12:00","capacity":1,"reserved"
  │ :1},{"id":12,"time_slot":"2026-02-01 10:00-12:00","cap
  │ acity":1,"reserved":1}]'
  └
  ✓  Status is 200
  ✓  Slot reserved = 1

↳ Check single order with this key
  GET http://arch.homework/api/v1/order [200 OK, 387B, 5ms]
  ┌
  │ 'REQUEST:', 'Check single order with this key', 'GET',
  │  'http://arch.homework/api/v1/order'
  │ 'REQUEST BODY: <none>'
  │ 'RESPONSE:', 200, '[{"id":"70d41dc9-bcaa-4046-b13a-6fa
  │ 4581c88a2","username":"Katlyn26","price":"500.00","sta
  │ tus":"paid","product_id":7,"quantity":1,"slot_id":12,"
  │ created_at":"2026-08-15T16:37:01.362926Z","error":"","
  │ idempotency_key":"67d2c824-8c27-4628-9c46-fb30d1d11cde
  │ "}]'
  └
  ✓  Status is 200
  ✓  Exactly one order with this idempotency key

❏ 4. New Idempotency-Key creates new order
↳ Create delivery slot 2
  POST http://arch.homework/api/v1/delivery/slots [201 Created, 209B, 5ms]
  ┌
  │ 'REQUEST:', 'Create delivery slot 2', 'POST', 'http://
  │ arch.homework/api/v1/delivery/slots'
  │ 'REQUEST BODY:', '{\n' +
  │   '  "time_slot": "2026-02-02 10:00-12:00",\n' +
  │   '  "capacity": 1\n' +
  │   '}'
  │ 'RESPONSE:', 201, '{"id":13,"time_slot":"2026-02-02 10
  │ :00-12:00","capacity":1,"reserved":0}'
  └
  ✓  Status is 201

↳ Create order (new Idempotency-Key)
  ┌
  │ 'IDEMPOTENCY KEY 2:', 'b3e25e67-f594-4c51-8143-76bcfc0
  │ f9fca'
  └
  POST http://arch.homework/api/v1/order [201 Created, 390B, 33ms]
  ┌
  │ 'REQUEST:', 'Create order (new Idempotency-Key)', 'POS
  │ T', 'http://arch.homework/api/v1/order'
  │ 'REQUEST BODY:', '{\n' +
  │   '  "price": 500,\n' +
  │   '  "product_id": 7,\n' +
  │   '  "quantity": 1,\n' +
  │   '  "slot_id": 13\n' +
  │   '}'
  │ 'RESPONSE:', 201, '{"id":"7973dcb9-9f51-4d50-9018-d94a
  │ b0195f95","username":"Katlyn26","price":"500.00","stat
  │ us":"paid","product_id":7,"quantity":1,"slot_id":13,"c
  │ reated_at":"2026-08-15T16:37:01.494381Z","error":"","i
  │ dempotency_key":"b3e25e67-f594-4c51-8143-76bcfc0f9fca"
  │ }'
  └
  ✓  Status is 201
  ✓  Order status is paid
  ✓  New order id (different from first)

↳ Check balance decreased twice
  GET http://arch.homework/api/v1/billing/account [200 OK, 172B, 4ms]
  ┌
  │ 'REQUEST:', 'Check balance decreased twice', 'GET', 'h
  │ ttp://arch.homework/api/v1/billing/account'
  │ 'REQUEST BODY: <none>'
  │ 'RESPONSE:', 200, '{"username":"Katlyn26","balance":"0
  │ .00"}'
  └
  ✓  Status is 200
  ✓  Balance decreased by two order prices

↳ Check stock decreased twice
  GET http://arch.homework/api/v1/warehouse/products [200 OK, 407B, 4ms]
  ┌
  │ 'REQUEST:', 'Check stock decreased twice', 'GET', 'htt
  │ p://arch.homework/api/v1/warehouse/products'
  │ 'REQUEST BODY: <none>'
  │ 'RESPONSE:', 200, '[{"id":1,"name":"Test Phone","stock
  │ ":9},{"id":2,"name":"Test Phone","stock":4},{"id":3,"n
  │ ame":"Test Phone","stock":4},{"id":4,"name":"Test Phon
  │ e","stock":4},{"id":5,"name":"Test Phone","stock":3},{
  │ "id":6,"name":"Test Phone","stock":3},{"id":7,"name":"
  │ Test Phone","stock":3}]'
  └
  ✓  Status is 200
  ✓  Product stock decreased by 2

❏ 5. Missing Idempotency-Key rejected
↳ Create order without Idempotency-Key
  POST http://arch.homework/api/v1/order [422 Unprocessable Content, 254B, 3ms]
  ┌
  │ 'REQUEST:', 'Create order without Idempotency-Key', 'P
  │ OST', 'http://arch.homework/api/v1/order'
  │ 'REQUEST BODY:', '{\n' +
  │   '  "price": 500,\n' +
  │   '  "product_id": 7,\n' +
  │   '  "quantity": 1,\n' +
  │   '  "slot_id": 13\n' +
  │   '}'
  │ 'RESPONSE:', 422, '{"detail":[{"type":"missing","loc":
  │ ["header","idempotency-key"],"msg":"Field required","i
  │ nput":null}]}'
  └
  ✓  Status is 422 (Idempotency-Key is required)
  ✓  Error mentions idempotency-key header

↳ Check balance unchanged after rejected request
  GET http://arch.homework/api/v1/billing/account [200 OK, 172B, 3ms]
  ┌
  │ 'REQUEST:', 'Check balance unchanged after rejected re
  │ quest', 'GET', 'http://arch.homework/api/v1/billing/ac
  │ count'
  │ 'REQUEST BODY: <none>'
  │ 'RESPONSE:', 200, '{"username":"Katlyn26","balance":"0
  │ .00"}'
  └
  ✓  Status is 200
  ✓  Balance unchanged (no side effects without key)

┌─────────────────────────┬──────────────────┬──────────────────┐
│                         │         executed │           failed │
├─────────────────────────┼──────────────────┼──────────────────┤
│              iterations │                1 │                0 │
├─────────────────────────┼──────────────────┼──────────────────┤
│                requests │               17 │                0 │
├─────────────────────────┼──────────────────┼──────────────────┤
│            test-scripts │               17 │                0 │
├─────────────────────────┼──────────────────┼──────────────────┤
│      prerequest-scripts │                2 │                0 │
├─────────────────────────┼──────────────────┼──────────────────┤
│              assertions │               32 │                0 │
├─────────────────────────┴──────────────────┴──────────────────┤
│ total run duration: 454ms                                     │
├───────────────────────────────────────────────────────────────┤
│ total data received: 3.6kB (approx)                           │
├───────────────────────────────────────────────────────────────┤
│ average response time: 16ms [min: 3ms, max: 88ms, s.d.: 23ms] │
└───────────────────────────────────────────────────────────────┘
```

# HW7 — IDL-описание API

Формальное описание контрактов взаимодействия сервисов.

- **OpenAPI (HTTP)** — общая часть для всех 4 вариантов: публичные эндпоинты, которые вызывает клиент,
  и синхронный межсервисный вызов списания средств (варианты 1, 2, 4; в варианте 1 дополнительно
  использовался бы `POST /api/v1/billing/account` для создания счёта — см. примечание ниже).
- **AsyncAPI (Kafka)** — относится к событийным вариантам: топик `message.send.email` (варианты 2, 3, 4)
  и топик `user.create` (варианты 3, 4). В варианте 3 дополнительно появляются топики `OrderCreated`,
  `PaymentSucceeded`, `PaymentFailed` (описаны в теории, здесь не формализуются, т.к. не реализованы).

Схемы соответствуют коду: `services/*/src/api/*.py`, `services/*/src/schemes.py`,
`services/app-auth/src/services/kafka.py`, `services/app-order/src/kafka.py`.

## OpenAPI (HTTP)

```yaml
openapi: 3.0.3
info:
  title: OTUS MSA HW7 — публичное API
  version: 1.0.0

paths:
  /api/v1/auth/register:
    post:
      tags: [auth]
      summary: Регистрация пользователя
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UserCreate'
      responses:
        '201':
          description: Пользователь создан, возвращается пара токенов
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TokenPair'
        '409':
          description: Username уже занят

  /api/v1/billing/deposit:
    post:
      tags: [billing]
      summary: Пополнение счёта текущего пользователя
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/DepositRequest'
      responses:
        '200':
          description: Счёт пополнен
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Account'
        '404':
          description: Счёт не найден

  /api/v1/billing/withdraw:
    post:
      tags: [billing]
      summary: Списание средств (вызывается app-order при создании заказа)
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/WithdrawRequest'
      responses:
        '200':
          description: Результат списания (success=false при нехватке средств)
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/WithdrawResponse'
        '404':
          description: Счёт не найден

  /api/v1/billing/account:
    get:
      tags: [billing]
      summary: Баланс счёта текущего пользователя
      security:
        - bearerAuth: []
      responses:
        '200':
          description: Текущий баланс
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Account'
        '404':
          description: Счёт не найден

  # Примечание: в варианте 1 (только HTTP) и варианте 2 здесь же был бы
  # POST /api/v1/billing/account { username } — синхронное создание счёта,
  # вызываемое app-auth при регистрации. В реализации (вариант 4) вместо него
  # используется событие user.create.

  /api/v1/order:
    post:
      tags: [order]
      summary: Создание заказа (синхронное списание, событие на письмо)
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/OrderCreate'
      responses:
        '201':
          description: Заказ создан (status = paid | failed)
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Order'

  /api/v1/notification:
    get:
      tags: [notification]
      summary: Список уведомлений текущего пользователя
      security:
        - bearerAuth: []
      responses:
        '200':
          description: Список уведомлений
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Notification'

components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

  schemas:
    UserCreate:
      type: object
      required: [username, password, email]
      properties:
        username: { type: string }
        password: { type: string }
        email:    { type: string, format: email }

    TokenPair:
      type: object
      required: [access_token, refresh_token]
      properties:
        access_token:  { type: string }
        refresh_token: { type: string }
        token_type:    { type: string, default: bearer }

    DepositRequest:
      type: object
      required: [amount]
      properties:
        amount:
          type: string   # Decimal, сериализуется строкой
          description: Сумма > 0, два знака после запятой
          example: "100.00"

    WithdrawRequest:
      type: object
      required: [amount]
      properties:
        amount:
          type: string   # Decimal
          description: Сумма > 0, два знака после запятой
          example: "50.00"

    WithdrawResponse:
      type: object
      required: [success, balance]
      properties:
        success: { type: boolean }
        balance: { type: string, description: Decimal, баланс после операции }

    Account:
      type: object
      required: [username, balance]
      properties:
        username: { type: string }
        balance:  { type: string, description: Decimal }

    OrderCreate:
      type: object
      required: [price]
      properties:
        price:
          type: string   # Decimal
          description: Цена > 0, два знака после запятой
          example: "99.90"

    Order:
      type: object
      required: [id, username, price, status, created_at]
      properties:
        id:         { type: string, format: uuid }
        username:   { type: string }
        price:      { type: string, description: Decimal }
        status:     { type: string, enum: [paid, failed] }
        created_at: { type: string, format: date-time }

    Notification:
      type: object
      required: [id, username, email, message_type, created_at, status]
      properties:
        id:           { type: string, format: uuid }
        username:     { type: string }
        email:        { type: string, format: email }
        message_type: { type: string, enum: [TEST_MESSAGE, ORDER_SUCCESS, ORDER_FAILED] }
        subject:      { type: string, nullable: true }
        body:         { type: string, nullable: true }
        created_at:   { type: string, format: date-time }
        status:       { type: string, enum: [READY_TO_SEND, SENT, ERROR] }
```

## AsyncAPI (Kafka)

Относится к событийным вариантам (2, 3, 4). В реализации (вариант 4) используются оба топика.

```yaml
asyncapi: 2.6.0
info:
  title: OTUS MSA HW7 — события Kafka
  version: 1.0.0

servers:
  kafka:
    url: kafka:9092
    protocol: kafka

channels:
  user.create:
    description: >
      Событие регистрации пользователя.
      Producer: app-auth. Consumers: app-billing (создание счёта), app-user (создание профиля).
      Key сообщения: username.
    publish:
      message:
        $ref: '#/components/messages/UserCreate'
    subscribe:
      message:
        $ref: '#/components/messages/UserCreate'

  message.send.email:
    description: >
      Команда/событие отправки письма по итогу создания заказа.
      Producer: app-order. Consumer: app-notification.
      Key сообщения: notification_id (= order id).
    publish:
      message:
        $ref: '#/components/messages/SendEmail'
    subscribe:
      message:
        $ref: '#/components/messages/SendEmail'

components:
  messages:
    UserCreate:
      name: userCreate
      contentType: application/json
      payload:
        $ref: '#/components/schemas/UserCreateEvent'

    SendEmail:
      name: sendEmail
      contentType: application/json
      payload:
        $ref: '#/components/schemas/SendEmailEvent'

  schemas:
    UserCreateEvent:
      type: object
      required: [username, email]
      properties:
        username: { type: string }
        email:    { type: string, format: email }

    SendEmailEvent:
      type: object
      required: [meta, data]
      properties:
        meta:
          type: object
          required: [message_type, username, email]
          properties:
            message_type:
              type: string
              enum: [TEST_MESSAGE, ORDER_SUCCESS, ORDER_FAILED]
            username: { type: string }
            email:    { type: string, format: email, nullable: true }
        data:
          type: object
          description: Полезная нагрузка письма (для заказа — order_id, price, balance)
          properties:
            order_id: { type: string, description: UUID заказа (строкой) }
            price:    { type: string, description: Decimal строкой }
            balance:  { type: string, description: Decimal строкой }
          additionalProperties: true
```

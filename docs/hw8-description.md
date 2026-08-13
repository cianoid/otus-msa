# ДЗ «Распределённые транзакции» — сага с оркестрацией

## Выбранный паттерн

Для создания заказа реализована сага с оркестрацией с компенсирующими
транзакциями. Оркестратором выступает `app-order`: он синхронно, по HTTP, вызывает участников
саги в строго заданном порядке и при отказе любого шага выполняет компенсирующие операции для всех
уже пройденных шагов — в обратном порядке.

### Порядок шагов саги (POST /api/v1/order)

1. `app-warehouse` — `POST /api/v1/warehouse/reserve` (резерв товара);
2. `app-delivery` — `POST /api/v1/delivery/reserve` (резерв курьера);
3. `app-billing` — `POST /api/v1/billing/withdraw` (оплата).

### Компенсирующие транзакции

Если любой из шагов завершился неудачей (`success: false` или HTTP-ошибка), откатываются все предыдущие шаги
в обратном порядке:

- отказ биллинга → `POST /api/v1/delivery/cancel` (освободить курьера),
  `POST /api/v1/warehouse/cancel` (вернуть товар на склад);
- отказ доставки → `POST /api/v1/warehouse/cancel`;
- отказ склада → компенсация не требуется (первый шаг).

Если бы списание денег было не последним шагом, компенсацией биллинга служил бы возврат средств —
`POST /api/v1/billing/deposit` на списанную сумму. Компенсации складом и доставкой идемпотентны:
повторный `cancel` по той же `reservation_id` возвращает `success: true`.

После завершения саги (успех или отказ) заказ сохраняется со статусом `paid` либо `failed`,
и через Kafka (`message.send.email`) отправляется уведомление `ORDER_SUCCESS` / `ORDER_FAILED`.

### Почему выбран этот паттерн

- **Простота реализации и отладки**: вся логика распределённой транзакции находится в одном месте
  (оркестраторе), последовательность шагов и компенсаций читается линейно.
- **Синхронный ответ клиенту**: результат заказа (`paid`/`failed`) известен в момент ответа на
  `POST /api/v1/order` — для платёжного сценария это важнее слабой связности.
- Существующий синхронный вызов `app-order → app-billing` естественно расширяется до саги
  без смены транспорта.

## Сервисы и их API

Все эндпоинты участников саги защищены JWT Bearer (общий секрет); `app-order` пробрасывает
пользовательский токен при вызовах. Внешний домен — `arch.homework`.

### app-warehouse (новый), префикс `/api/v1/warehouse`

| Метод | Путь | Body / ответ | Назначение |
|---|---|---|---|
| GET | `/products` | → 200 `[{id, name, stock}]` | Список товаров |
| POST | `/products` | `{name, stock}` → 201 `{id, name, stock}` | Создать товар |
| POST | `/reserve` | `{order_id, product_id, quantity}` → 200 `{success, reservation_id, stock}` | Шаг саги: атомарный резерв |
| POST | `/cancel` | `{reservation_id}` → 200 `{success}` | Компенсация: вернуть товар (идемпотентно) |

`/reserve` атомарен: при `stock >= quantity` уменьшает `stock`, создаёт резервацию (`uuid4`),
возвращает `success: true`; иначе `success: false`, `reservation_id: null`.

### app-delivery (новый), префикс `/api/v1/delivery`

| Метод | Путь | Body / ответ | Назначение |
|---|---|---|---|
| GET | `/slots` | → 200 `[{id, time_slot, capacity, reserved}]` | Список слотов |
| POST | `/slots` | `{time_slot, capacity}` → 201 `{id, time_slot, capacity, reserved}` | Создать слот |
| POST | `/reserve` | `{order_id, slot_id}` → 200 `{success, reservation_id}` | Шаг саги: резерв курьера |
| POST | `/cancel` | `{reservation_id}` → 200 `{success}` | Компенсация: освободить курьера (идемпотентно) |

`/reserve` атомарен: при `reserved < capacity` увеличивает `reserved` на 1, создаёт резервацию
(`uuid4`), возвращает `success: true`; иначе `success: false`.

### app-billing (существующий), префикс `/api/v1/billing`

| Метод | Путь | Назначение |
|---|---|---|
| POST | `/withdraw` (`{amount}` → `{success, balance}`) | Шаг саги: списание оплаты |
| POST | `/deposit` (`{amount}`) | Компенсация биллинга (возврат средств), а также пополнение счёта |

### app-order (оркестратор саги), префикс `/api/v1/order`

`POST /api/v1/order` принимает расширенный `OrderCreate`:
`{price, product_id, quantity, slot_id}`. Дальше выполняются шаги саги
(warehouse → delivery → billing) с компенсациями при отказе, заказ сохраняется со статусом
`paid`/`failed`, публикуется событие нотификации в Kafka. Ответ — заказ, как раньше
(плюс новые поля).

## Схема взаимодействия

Исходник Mermaid: [hw8-architecture.mermaid](hw8-architecture.mermaid).
Если схема не открывается, доступна картинка: [hw8-architecture.png](hw8-architecture.png)

## Команда установки приложения

Namespace — **`default`**. Установка описана в [readme.md](../readme.md#установка-приложения):

Перед установкой на уже развёрнутый кластер нужно создать базы `app_warehouse` и `app_delivery`
дав postgres — см. [readme.md](../readme.md#базы-данных-для-hw8).

## Запуск тестов Postman

Коллекция: [postman/otus-msa-hw8.postman_collection.json](../postman/otus-msa-hw8.postman_collection.json)

```shell
newman run postman/otus-msa-hw8.postman_collection.json
```

`baseUrl` уже задан в коллекции (`arch.homework`). При необходимости его можно переопределить.

Результат работы тестов:
```
OTUS MSA HW8 — Distributed Transactions (Saga)

❏ 1. Auth
↳ Register user
  POST http://arch.homework/api/v1/auth/register [201 Created, 495B, 77ms]
  ┌
  │ 'REQUEST:', 'Register user', 'POST'
  │ , 'http://arch.homework/api/v1/auth/register'
  │ 'REQUEST BODY:', '{\n' +
  │   '  "username": "Darby74",\n' +
  │   '  "email": "Cathy35@cianoid.ru",\n' +
  │   '  "password": "password123"\n' +
  │   '}'
  │ 'RESPONSE:', 201, '{"access_token":"eyJhbGciO
  │ iJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJEYXJieTc0IiwiZXhwIjoxNzg2Mzk2Mjk4LCJ0eXBlIjoiYWNjZX
  │ NzIn0.3hqj1ZpAEBy_lbDg-IEbyBLSCczdtYtEJBGKKpVlpOk","refresh_token":"eyJhbGciOiJIUzI1NiIsIn
  │ R5cCI6IkpXVCJ9.eyJzdWIiOiJEYXJieTc0IiwiZXhwIjoxNzg2OTk5Mjk4LCJ0eXBlIjoicmVmcmVzaCJ9.F9n6ro
  │ b31Spjt5ZOZLRfDVDDPvdTA0buFCX5IsClxNM","token_type":"bearer"}'
  └
  ✓  Status is 201

↳ Login
  POST http://arch.homework/api/v1/auth/login [200 OK, 490B, 33ms]
  ┌
  │ 'REQUEST:', 'Login', 'POST', [39m
  │ [90m'http://arch.homework/api/v1/auth/login'                                                
  │ 'REQUEST BODY:', '{\n  "username": "Darby74",\n  "password": "pas
  │ sword123"\n}'
  │ 'RESPONSE:', 200, '{"access_token":"eyJhbGciO
  │ iJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJEYXJieTc0IiwiZXhwIjoxNzg2Mzk2Mjk4LCJ0eXBlIjoiYWNjZX
  │ NzIn0.3hqj1ZpAEBy_lbDg-IEbyBLSCczdtYtEJBGKKpVlpOk","refresh_token":"eyJhbGciOiJIUzI1NiIsIn
  │ R5cCI6IkpXVCJ9.eyJzdWIiOiJEYXJieTc0IiwiZXhwIjoxNzg2OTk5Mjk4LCJ0eXBlIjoicmVmcmVzaCJ9.F9n6ro
  │ b31Spjt5ZOZLRfDVDDPvdTA0buFCX5IsClxNM","token_type":"bearer"}'
  └
  ✓  Status is 200

❏ 2. Billing setup
↳ Deposit money
  POST http://arch.homework/api/v1/billing/deposit [200 OK, 174B, 9ms]
  ┌
  │ 'REQUEST:', 'Deposit money', 'POST'
  │ , 'http://arch.homework/api/v1/billing/deposit'
  │ 'REQUEST BODY:', '{\n  "amount": "1000"\n}'
  │ 'RESPONSE:', 200, '{"username":"Darby74","bal
  │ ance":"1000.00"}'
  └
  ✓  Status is 200
  ✓  Billing account created, balance equals deposit

↳ Get account balance
  GET http://arch.homework/api/v1/billing/account [200 OK, 174B, 4ms]
  ┌
  │ 'REQUEST:', 'Get account balance', 'GET'
  │ , 'http://arch.homework/api/v1/billing/account'
  │ 'REQUEST BODY: <none>'
  │ 'RESPONSE:', 200, '{"username":"Darby74","bal
  │ ance":"1000.00"}'
  └
  ✓  Status is 200

❏ 3. Warehouse & Delivery setup
↳ Create product
  POST http://arch.homework/api/v1/warehouse/products [201 Created, 175B, 8ms]
  ┌
  │ 'REQUEST:', 'Create product', 'POST'[37[39m
  │ m, 'http://arch.homework/api/v1/warehouse/products'                                         
  │ 'REQUEST BODY:', '{\n  "name": "Test Phone",\n  "stock": 5\n}'[3[39m
  │ 9m                                                                                          
  │ 'RESPONSE:', 201, '{"id":4,"name":"Test Phone
  │ ","stock":5}'
  └
  ✓  Status is 201

↳ Create delivery slot
  POST http://arch.homework/api/v1/delivery/slots [201 Created, 208B, 9ms]
  ┌
  │ 'REQUEST:', 'Create delivery slot', 'POST'[3[39m
  │ 9m, 'http://arch.homework/api/v1/delivery/slots'                                            
  │ 'REQUEST BODY:', '{\n  "time_slot": "2026-01-01 10:00-12:00",\n  
  │ "capacity": 1\n}'
  │ 'RESPONSE:', 201, '{"id":6,"time_slot":"2026-
  │ 01-01 10:00-12:00","capacity":1,"reserved":0}'
  └
  ✓  Status is 201

❏ 4. Order — success (paid)
↳ Create order (success)
  POST http://arch.homework/api/v1/order [201 Created, 320B, 39ms]
  ┌
  │ 'REQUEST:', 'Create order (success)', 'POST'[39m
  │ [39m, 'http://arch.homework/api/v1/order'                                                   
  │ 'REQUEST BODY:', '{\n  "price": 500,\n  "product_id": 4,\n  "quan
  │ tity": 1,\n  "slot_id": 6\n}'
  │ 'RESPONSE:', 201, '{"id":"1e135015-0178-467e-
  │ 8456-397495bc26ae","username":"Darby74","price":"500.00","status":"paid","product_id":4,"q
  │ uantity":1,"slot_id":6,"created_at":"2026-08-10T20:41:38.381830Z"}'
  └
  ✓  Status is 201
  ✓  Order status is paid

↳ Check balance decreased
  GET http://arch.homework/api/v1/billing/account [200 OK, 173B, 4ms]
  ┌
  │ 'REQUEST:', 'Check balance decreased', 'GET'[39m
  │ [39m, 'http://arch.homework/api/v1/billing/account'                                         
  │ 'REQUEST BODY: <none>'
  │ 'RESPONSE:', 200, '{"username":"Darby74","bal
  │ ance":"500.00"}'
  └
  ✓  Status is 200
  ✓  Balance decreased by order price

↳ Check product stock decreased
  GET http://arch.homework/api/v1/warehouse/products [200 OK, 211B, 4ms]
  ┌
  │ 'REQUEST:', 'Check product stock decreased', 
  │ 'GET', 'http://arch.homework/api/v1/warehouse/products'
  │ 'REQUEST BODY: <none>'
  │ 'RESPONSE:', 200, '[{"id":3,"name":"Test Phon
  │ e","stock":4},{"id":4,"name":"Test Phone","stock":4}]'
  └
  ✓  Status is 200
  ✓  Product stock decreased by 1

↳ Check slot reserved
  GET http://arch.homework/api/v1/delivery/slots [200 OK, 278B, 4ms]
  ┌
  │ 'REQUEST:', 'Check slot reserved', 'GET'
  │ , 'http://arch.homework/api/v1/delivery/slots'
  │ 'REQUEST BODY: <none>'
  │ 'RESPONSE:', 200, '[{"id":5,"time_slot":"2026
  │ -01-01 10:00-12:00","capacity":1,"reserved":1},{"id":6,"time_slot":"2026-01-01 10:00-12:00
  │ ","capacity":1,"reserved":1}]'
  └
  ✓  Status is 200
  ✓  Slot reserved = 1

❏ 5. Order — not enough money (failed + compensation)
↳ Create delivery slot (fail scenario)
  POST http://arch.homework/api/v1/delivery/slots [201 Created, 208B, 5ms]
  ┌
  │ 'REQUEST:', 'Create delivery slot (fail scenario)', [3[39m
  │ 9m'POST', 'http://arch.homework/api/v1/delivery/slots'                                      
  │ 'REQUEST BODY:', '{\n  "time_slot": "2026-01-02 10:00-12:00",\n  
  │ "capacity": 1\n}'
  │ 'RESPONSE:', 201, '{"id":7,"time_slot":"2026-
  │ 01-02 10:00-12:00","capacity":1,"reserved":0}'
  └
  ✓  Status is 201

↳ Create order (failed, price > balance)
  POST http://arch.homework/api/v1/order [201 Created, 323B, 35ms]
  ┌
  │ 'REQUEST:', 'Create order (failed, price > balance)', [39m
  │ [39m'POST', 'http://arch.homework/api/v1/order'                                             
  │ 'REQUEST BODY:', '{\n  "price": 9999,\n  "product_id": 4,\n  "qua
  │ ntity": 1,\n  "slot_id": 7\n}'
  │ 'RESPONSE:', 201, '{"id":"75aa294e-731d-4c53-
  │ 80fd-76879a77f914","username":"Darby74","price":"9999.00","status":"failed","product_id":4
  │ ,"quantity":1,"slot_id":7,"created_at":"2026-08-10T20:41:38.482670Z"}'
  └
  ✓  Status is 201
  ✓  Order status is failed

↳ Check balance unchanged
  GET http://arch.homework/api/v1/billing/account [200 OK, 173B, 4ms]
  ┌
  │ 'REQUEST:', 'Check balance unchanged', 'GET'[39m
  │ [39m, 'http://arch.homework/api/v1/billing/account'                                         
  │ 'REQUEST BODY: <none>'
  │ 'RESPONSE:', 200, '{"username":"Darby74","bal
  │ ance":"500.00"}'
  └
  ✓  Status is 200
  ✓  Balance unchanged after failed order

↳ Check product stock restored (compensation)
  GET http://arch.homework/api/v1/warehouse/products [200 OK, 211B, 3ms]
  ┌
  │ 'REQUEST:', 'Check product stock restored (compensation)'[3[39m
  │ 7m, 'GET', 'http://arch.homework/api/v1/warehouse/products'[39m                             
  │ [39m                                                                                        
  │ 'REQUEST BODY: <none>'
  │ 'RESPONSE:', 200, '[{"id":3,"name":"Test Phon
  │ e","stock":4},{"id":4,"name":"Test Phone","stock":4}]'
  └
  ✓  Status is 200
  ✓  Product stock restored by compensation

↳ Check slot released (compensation)
  GET http://arch.homework/api/v1/delivery/slots [200 OK, 350B, 4ms]
  ┌
  │ 'REQUEST:', 'Check slot released (compensation)', 
  │ 'GET', 'http://arch.homework/api/v1/delivery/slots'
  │ 'REQUEST BODY: <none>'
  │ 'RESPONSE:', 200, '[{"id":5,"time_slot":"2026
  │ -01-01 10:00-12:00","capacity":1,"reserved":1},{"id":6,"time_slot":"2026-01-01 10:00-12:00
  │ ","capacity":1,"reserved":1},{"id":7,"time_slot":"2026-01-02 10:00-12:00","capacity":1,"re
  │ served":0}]'
  └
  ✓  Status is 200
  ✓  Slot released, reserved = 0

❏ 6. Order — not enough stock (failed)
↳ Create order (failed, quantity > stock)
  POST http://arch.homework/api/v1/order [201 Created, 323B, 19ms]
  ┌
  │ 'REQUEST:', 'Create order (failed, quantity > stock)', 
  │ 'POST', 'http://arch.homework/api/v1/order'
  │ 'REQUEST BODY:', '{\n  "price": 500,\n  "product_id": 4,\n  "quan
  │ tity": 10,\n  "slot_id": 6\n}'
  │ 'RESPONSE:', 201, '{"id":"ba87f8b1-7483-4dde-
  │ 9b99-15dff3390219","username":"Darby74","price":"500.00","status":"failed","product_id":4,
  │ "quantity":10,"slot_id":6,"created_at":"2026-08-10T20:41:38.552133Z"}'
  └
  ✓  Status is 201
  ✓  Order status is failed

↳ Check balance unchanged after stock failure
  GET http://arch.homework/api/v1/billing/account [200 OK, 173B, 4ms]
  ┌
  │ 'REQUEST:', 'Check balance unchanged after stock failure'[3[39m
  │ 7m, 'GET', 'http://arch.homework/api/v1/billing/account'[39[39m                             
  │ m                                                                                           
  │ 'REQUEST BODY: <none>'
  │ 'RESPONSE:', 200, '{"username":"Darby74","bal
  │ ance":"500.00"}'
  └
  ✓  Status is 200
  ✓  Balance unchanged after stock failure

❏ 7. Notifications
↳ Check notification (ORDER_SUCCESS)
  GET http://arch.homework/api/v1/notification [200 OK, 772B, 7ms]
  ┌
  │ 'REQUEST:', 'Check notification (ORDER_SUCCESS)', 
  │ 'GET', 'http://arch.homework/api/v1/notification'
  │ 'REQUEST BODY: <none>'
  │ 'RESPONSE:', 200, '[{"id":"1e135015-0178-467e
  │ -8456-397495bc26ae","username":"Darby74","email":"Cathy35@cianoid.ru","message_type":"ORDE
  │ R_SUCCESS","subject":"Заказ успешно оформлен","body":"<!doctype html>\\n<html lang=\\"ru\\
  │ ">\\n  <body>\\n    <h1>Здравствуйте, Darby74!</h1>\\n    <p>Ваш заказ №1e135015-0178-467e
  │ -8456-397495bc26ae успешно оформлен.</p>\\n    <p>\\n      Стоимость заказа: 500<br>\\n   
  │    Остаток на счёте: 500.00\\n    </p>\\n    <p>Спасибо за покупку!</p>\\n  </body>\\n</ht
  │ ml>","created_at":"2026-08-10T20:41:38.393786Z","status":"READY_TO_SEND"}]'
  └
  ✓  Status is 200

Attempting to set next request to Check notification (ORDER_SUCCESS)

↳ Check notification (ORDER_SUCCESS)
  GET http://arch.homework/api/v1/notification [200 OK, 2.17kB, 8ms]
  ┌
  │ 'REQUEST:', 'Check notification (ORDER_SUCCESS)', 
  │ 'GET', 'http://arch.homework/api/v1/notification'
  │ 'REQUEST BODY: <none>'
  │ 'RESPONSE:', 200, '[{"id":"ba87f8b1-7483-4dde
  │ -9b99-15dff3390219","username":"Darby74","email":"Cathy35@cianoid.ru","message_type":"ORDE
  │ R_FAILED","subject":"Не удалось оформить заказ","body":"<!doctype html>\\n<html lang=\\"ru
  │ \\">\\n  <body>\\n    <h1>Здравствуйте, Darby74!</h1>\\n    <p>К сожалению, заказ №ba87f8b
  │ 1-7483-4dde-9b99-15dff3390219 не удалось оформить.</p>\\n    <p>\\n      Стоимость заказа:
  │  500<br>\\n      Текущий баланс: 0.00\\n    </p>\\n    <p>Пожалуйста, пополните счёт и поп
  │ робуйте снова.</p>\\n  </body>\\n</html>","created_at":"2026-08-10T20:41:39.330517Z","stat
  │ us":"READY_TO_SEND"},{"id":"75aa294e-731d-4c53-80fd-76879a77f914","username":"Darby74","em
  │ ail":"Cathy35@cianoid.ru","message_type":"ORDER_FAILED","subject":"Не удалось оформить зак
  │ аз","body":"<!doctype html>\\n<html lang=\\"ru\\">\\n  <body>\\n    <h1>Здравствуйте, Darb
  │ y74!</h1>\\n    <p>К сожалению, заказ №75aa294e-731d-4c53-80fd-76879a77f914 не удалось офо
  │ рмить.</p>\\n    <p>\\n      Стоимость заказа: 9999<br>\\n      Текущий баланс: 500.00\\n 
  │    </p>\\n    <p>Пожалуйста, пополните счёт и попробуйте снова.</p>\\n  </body>\\n</html>"
  │ ,"created_at":"2026-08-10T20:41:38.812057Z","status":"SENT"},{"id":"1e135015-0178-467e-845
  │ 6-397495bc26ae","username":"Darby74","email":"Cathy35@cianoid.ru","message_type":"ORDER_SU
  │ CCESS","subject":"Заказ успешно оформлен","body":"<!doctype html>\\n<html lang=\\"ru\\">\\
  │ n  <body>\\n    <h1>Здравствуйте, Darby74!</h1>\\n    <p>Ваш заказ №1e135015-0178-467e-845
  │ 6-397495bc26ae успешно оформлен.</p>\\n    <p>\\n      Стоимость заказа: 500<br>\\n      О
  │ статок на счёте: 500.00\\n    </p>\\n    <p>Спасибо за покупку!</p>\\n  </body>\\n</html>"
  │ ,"created_at":"2026-08-10T20:41:38.393786Z","status":"SENT"}]'
  └
  ✓  Status is 200

↳ Check notification (ORDER_FAILED)
  GET http://arch.homework/api/v1/notification [200 OK, 2.17kB, 5ms]
  ┌
  │ 'REQUEST:', 'Check notification (ORDER_FAILED)', [39m
  │ [90m'GET', 'http://arch.homework/api/v1/notification'                                       
  │ 'REQUEST BODY: <none>'
  │ 'RESPONSE:', 200, '[{"id":"ba87f8b1-7483-4dde
  │ -9b99-15dff3390219","username":"Darby74","email":"Cathy35@cianoid.ru","message_type":"ORDE
  │ R_FAILED","subject":"Не удалось оформить заказ","body":"<!doctype html>\\n<html lang=\\"ru
  │ \\">\\n  <body>\\n    <h1>Здравствуйте, Darby74!</h1>\\n    <p>К сожалению, заказ №ba87f8b
  │ 1-7483-4dde-9b99-15dff3390219 не удалось оформить.</p>\\n    <p>\\n      Стоимость заказа:
  │  500<br>\\n      Текущий баланс: 0.00\\n    </p>\\n    <p>Пожалуйста, пополните счёт и поп
  │ робуйте снова.</p>\\n  </body>\\n</html>","created_at":"2026-08-10T20:41:39.330517Z","stat
  │ us":"READY_TO_SEND"},{"id":"75aa294e-731d-4c53-80fd-76879a77f914","username":"Darby74","em
  │ ail":"Cathy35@cianoid.ru","message_type":"ORDER_FAILED","subject":"Не удалось оформить зак
  │ аз","body":"<!doctype html>\\n<html lang=\\"ru\\">\\n  <body>\\n    <h1>Здравствуйте, Darb
  │ y74!</h1>\\n    <p>К сожалению, заказ №75aa294e-731d-4c53-80fd-76879a77f914 не удалось офо
  │ рмить.</p>\\n    <p>\\n      Стоимость заказа: 9999<br>\\n      Текущий баланс: 500.00\\n 
  │    </p>\\n    <p>Пожалуйста, пополните счёт и попробуйте снова.</p>\\n  </body>\\n</html>"
  │ ,"created_at":"2026-08-10T20:41:38.812057Z","status":"SENT"},{"id":"1e135015-0178-467e-845
  │ 6-397495bc26ae","username":"Darby74","email":"Cathy35@cianoid.ru","message_type":"ORDER_SU
  │ CCESS","subject":"Заказ успешно оформлен","body":"<!doctype html>\\n<html lang=\\"ru\\">\\
  │ n  <body>\\n    <h1>Здравствуйте, Darby74!</h1>\\n    <p>Ваш заказ №1e135015-0178-467e-845
  │ 6-397495bc26ae успешно оформлен.</p>\\n    <p>\\n      Стоимость заказа: 500<br>\\n      О
  │ статок на счёте: 500.00\\n    </p>\\n    <p>Спасибо за покупку!</p>\\n  </body>\\n</html>"
  │ ,"created_at":"2026-08-10T20:41:38.393786Z","status":"SENT"}]'
  └
  ✓  Status is 200

┌─────────────────────────┬──────────────────┬──────────────────┐
│                         │         executed │           failed │
├─────────────────────────┼──────────────────┼──────────────────┤
│              iterations │                1 │                0 │
├─────────────────────────┼──────────────────┼──────────────────┤
│                requests │               20 │                0 │
├─────────────────────────┼──────────────────┼──────────────────┤
│            test-scripts │               20 │                0 │
├─────────────────────────┼──────────────────┼──────────────────┤
│      prerequest-scripts │                0 │                0 │
├─────────────────────────┼──────────────────┼──────────────────┤
│              assertions │               31 │                0 │
├─────────────────────────┴──────────────────┴──────────────────┤
│ total run duration: 1500ms                                    │
├───────────────────────────────────────────────────────────────┤
│ total data received: 6.89kB (approx)                          │
├───────────────────────────────────────────────────────────────┤
│ average response time: 14ms [min: 3ms, max: 77ms, s.d.: 18ms] │
└───────────────────────────────────────────────────────────────┘
```
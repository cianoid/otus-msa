import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Базовый URL приложения. Переопределяется через env BASE_URL.
const BASE_URL = __ENV.BASE_URL || 'http://arch.homework';

// Параметры нагрузки. Переопределяются через env VUS и DURATION.
const VUS = parseInt(__ENV.VUS || '50', 10);
const DURATION = __ENV.DURATION || '5m';
const RAMP_UP = __ENV.RAMP_UP || '1m';
const RAMP_DOWN = __ENV.RAMP_DOWN || '1m';

// Преобразует k6-длительность (например, '30s', '5m', '1h') в минуты.
function toMinutes(dur) {
  const match = String(dur).match(/^(\d+)([smh])$/);
  if (!match) return 0;
  const value = parseInt(match[1], 10);
  const unit = match[2];
  if (unit === 's') return Math.ceil(value / 60);
  if (unit === 'h') return value * 60;
  return value;
}

function randomString(length) {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let result = '';
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

function uuidv4() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

// Кастомные метрики для бизнес-уровня.
const orderSuccessRate = new Rate('order_success_rate');
const orderDuration = new Trend('order_duration');

export const options = {
  scenarios: {
    // Основной сценарий: создание заказов через сагу.
    create_orders: {
      executor: 'ramping-vus',
      startVUs: 1,
      stages: [
        { duration: RAMP_UP, target: VUS },
        { duration: DURATION, target: VUS },
        { duration: RAMP_DOWN, target: 0 },
      ],
      exec: 'createOrder',
    },
    // Лёгкий фоновый сценарий для GET-запросов (профиль, баланс, заказы).
    read_requests: {
      executor: 'constant-vus',
      vus: 5,
      duration: `${toMinutes(RAMP_UP) + toMinutes(DURATION) + toMinutes(RAMP_DOWN)}m`,
      exec: 'readRequests',
    },
  },
  thresholds: {
    // SLO приложения: P95 latency < 300 мс, error rate < 1%.
    http_req_duration: ['p(95)<300'],
    http_req_failed: ['rate<0.01'],
    order_success_rate: ['rate>0.95'],
  },
};

const jsonHeaders = {
  headers: { 'Content-Type': 'application/json' },
};

function authHeaders(token) {
  return {
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
  };
}

function fail(msg) {
  throw new Error(msg);
}

// Единоразовая подготовка тестовых данных: пользователь, баланс, товар и слот.
export function setup() {
  const username = `load-${randomString(8)}`;
  const password = 'loadtest-password';
  const email = `${username}@cianoid.ru`;

  // 1. Регистрация пользователя.
  const registerRes = http.post(
    `${BASE_URL}/api/v1/auth/register`,
    JSON.stringify({ username, password, email }),
    jsonHeaders
  );
  check(registerRes, {
    'register status is 201': (r) => r.status === 201,
    'register returns access_token': (r) => {
      const body = safeJson(r);
      return body && body.access_token && body.access_token.length > 0;
    },
  }) || fail(`register failed: ${registerRes.status} ${registerRes.body}`);

  const token = registerRes.json('access_token');

  // 2. Ожидаем создания счёта в app-billing (событие user.create обрабатывается
  // асинхронно через Kafka), затем пополняем его большим запасом для множества заказов.
  let accountRes;
  for (let attempt = 1; attempt <= 30; attempt++) {
    accountRes = http.get(`${BASE_URL}/api/v1/billing/account`, authHeaders(token));
    if (accountRes.status === 200) {
      break;
    }
    if (attempt < 30) {
      sleep(0.5);
    }
  }
  check(accountRes, {
    'billing account created': (r) => r.status === 200,
  }) || fail(`billing account was not created: ${accountRes.status} ${accountRes.body}`);

  const depositRes = http.post(
    `${BASE_URL}/api/v1/billing/deposit`,
    JSON.stringify({ amount: '100000000.00' }),
    authHeaders(token)
  );
  check(depositRes, {
    'deposit status is 200': (r) => r.status === 200,
  }) || fail(`deposit failed: ${depositRes.status} ${depositRes.body}`);

  // 3. Создание товара с большим запасом.
  const productRes = http.post(
    `${BASE_URL}/api/v1/warehouse/products`,
    JSON.stringify({ name: `Load Product ${randomString(6)}`, stock: 1000000 }),
    authHeaders(token)
  );
  check(productRes, {
    'create product status is 201': (r) => r.status === 201,
    'create product returns id': (r) => r.json('id') > 0,
  }) || fail(`create product failed: ${productRes.status} ${productRes.body}`);

  const productId = productRes.json('id');

  // 4. Создание слота доставки с большой вместимостью.
  const slotRes = http.post(
    `${BASE_URL}/api/v1/delivery/slots`,
    JSON.stringify({ time_slot: '2026-12-31 10:00-12:00', capacity: 1000000 }),
    authHeaders(token)
  );
  check(slotRes, {
    'create slot status is 201': (r) => r.status === 201,
    'create slot returns id': (r) => r.json('id') > 0,
  }) || fail(`create slot failed: ${slotRes.status} ${slotRes.body}`);

  const slotId = slotRes.json('id');

  console.log(
    `setup complete: user=${username}, product=${productId}, slot=${slotId}`
  );

  return { token, productId, slotId, username };
}

// Основной сценарий нагрузки: создание заказа с Idempotency-Key.
export function createOrder(data) {
  const idempotencyKey = uuidv4();
  const orderPayload = JSON.stringify({
    price: '100.00',
    product_id: data.productId,
    quantity: 1,
    slot_id: data.slotId,
  });

  const params = authHeaders(data.token);
  params.headers['Idempotency-Key'] = idempotencyKey;

  const res = http.post(`${BASE_URL}/api/v1/order`, orderPayload, params);
  orderDuration.add(res.timings.duration);

  const body = safeJson(res);
  const isPaid = res.status === 201 && body && body.status === 'paid';
  orderSuccessRate.add(isPaid);

  check(res, {
    'order status is 201 or 409': (r) => r.status === 201 || r.status === 409,
    'order status paid when 201': (r) =>
      r.status !== 201 || (body && body.status === 'paid'),
    'order response time < 300ms': (r) => r.timings.duration < 300,
  });
}

// Фоновый сценарий чтения: баланс, заказы, профиль.
export function readRequests(data) {
  const headers = authHeaders(data.token);

  const balanceRes = http.get(`${BASE_URL}/api/v1/billing/account`, headers);
  check(balanceRes, {
    'get account status is 200': (r) => r.status === 200,
  });

  const ordersRes = http.get(`${BASE_URL}/api/v1/order`, headers);
  check(ordersRes, {
    'get orders status is 200': (r) => r.status === 200,
  });

  const profileRes = http.get(`${BASE_URL}/api/v1/profile`, headers);
  check(profileRes, {
    'get profile status is 200': (r) => r.status === 200,
  });

  sleep(1);
}

function safeJson(response) {
  try {
    return response.json();
  } catch (e) {
    return null;
  }
}

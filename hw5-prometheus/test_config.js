import http from 'k6/http';

// агрессивный
const timeUnit = '60m';
const duration = timeUnit;
const countMany = 300000;
const countMedium = 3000;
const countFew = 1800;
const countSelect = 500000;

// проверка
// const timeUnit = '1m';
// const duration = timeUnit;
// const countMany = 100;
// const countMedium = 5;
// const countFew = 3;
// const countSelect = 50;

export const options = {
  scenarios: {
    // Сценарий 1: 10 000 запросов за 10 минут
    many_requests: {
      executor: 'constant-arrival-rate',
      rate: countMany,
      timeUnit: timeUnit,
      duration: duration,
      preAllocatedVUs: 10,
      maxVUs: 100,
      exec: 'sendMany',
    },
    // Сценарий 2: 100 запросов за 10 минут
    few_requests: {
      executor: 'constant-arrival-rate',
      rate: countFew,
      timeUnit: timeUnit,
      duration: duration,
      preAllocatedVUs: 1,
      maxVUs: 10,
      exec: 'sendFew',
    },
    // Сценарий 3: 300 запросов за 10 минут
    medium_requests: {
      executor: 'constant-arrival-rate',
      rate: countMedium,
      timeUnit: timeUnit,
      duration: duration,
      preAllocatedVUs: 1,
      maxVUs: 15,
      exec: 'sendMedium',
    },
    // Сценарий 4:
    select_requests: {
      executor: 'constant-arrival-rate',
      rate: countSelect,
      timeUnit: timeUnit,
      duration: duration,
      preAllocatedVUs: 1,
      maxVUs: 15,
      exec: 'select',
    }
  },
};

const url = 'http://arch.homework/users/';
const params = {
  headers: { 'Content-Type': 'application/json' },
};

// Вспомогательная функция для создания случайного email [1]
function generateRandomEmail() {
  const rand = Math.random().toString(36).substring(2, 10);
  const timestamp = Date.now();
  return `user-${rand}-${timestamp}@example.com`; // Итог: user-a1b2c3d4-1718900000@example.com
}

// Сценарий 1 (10 000 запросов)
export function sendMany() {
  const payload = JSON.stringify({
    email: generateRandomEmail(),
    name: "heavy_user",
    age: 10
  });
  http.post(url, payload, params);
}

// Сценарий 2 (100 запросов)
export function sendFew() {
  const payload = JSON.stringify({
    email: generateRandomEmail(),
    name: "rare_user",
    age: -1
  });
  http.post(url, payload, params);
}

// Сценарий 3 (300 запросов)
export function sendMedium() {
  const payload = JSON.stringify({
    age: "test"
  });
  http.post(url, payload, params);
}

// Сценарий 3 (300 запросов)
export function select() {
  http.get(url);
}

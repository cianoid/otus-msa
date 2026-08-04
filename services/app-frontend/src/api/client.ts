import type {
  Account,
  ApiError,
  DepositRequest,
  Notification,
  Order,
  OrderCreate,
  TokenPair,
  User,
  UserCreate,
  UserLogin,
  UserUpdate,
  WithdrawRequest,
  WithdrawResponse,
} from '@/types'

const API_BASE = '/api/v1'

function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem('access_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorText = `HTTP ${res.status}`
    try {
      const err: ApiError = await res.json()
      errorText = err.detail || errorText
    } catch {
      // ignore parse error
    }
    throw new Error(errorText)
  }
  return res.json() as Promise<T>
}

export const authApi = {
  register: (data: UserCreate): Promise<TokenPair> =>
    fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then((res) => handleResponse<TokenPair>(res)),

  login: (data: UserLogin): Promise<TokenPair> =>
    fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then((res) => handleResponse<TokenPair>(res)),

  refresh: (refreshToken: string): Promise<TokenPair> =>
    fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    }).then((res) => handleResponse<TokenPair>(res)),
}

export const billingApi = {
  getAccount: (): Promise<Account> =>
    fetch(`${API_BASE}/billing/account`, {
      headers: { ...getAuthHeaders() },
    }).then((res) => handleResponse<Account>(res)),

  deposit: (data: DepositRequest): Promise<Account> =>
    fetch(`${API_BASE}/billing/deposit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify(data),
    }).then((res) => handleResponse<Account>(res)),

  withdraw: (data: WithdrawRequest): Promise<WithdrawResponse> =>
    fetch(`${API_BASE}/billing/withdraw`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify(data),
    }).then((res) => handleResponse<WithdrawResponse>(res)),
}

export const orderApi = {
  list: (): Promise<Order[]> =>
    fetch(`${API_BASE}/order`, {
      headers: { ...getAuthHeaders() },
    }).then((res) => handleResponse<Order[]>(res)),

  create: (data: OrderCreate): Promise<Order> =>
    fetch(`${API_BASE}/order`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify(data),
    }).then((res) => handleResponse<Order>(res)),
}

export const notificationApi = {
  list: (): Promise<Notification[]> =>
    fetch(`${API_BASE}/notification`, {
      headers: { ...getAuthHeaders() },
    }).then((res) => handleResponse<Notification[]>(res)),
}

export const userApi = {
  getProfile: (): Promise<User> =>
    fetch(`${API_BASE}/profile`, {
      headers: { ...getAuthHeaders() },
    }).then((res) => handleResponse<User>(res)),

  updateProfile: (data: UserUpdate): Promise<User> =>
    fetch(`${API_BASE}/profile`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify(data),
    }).then((res) => handleResponse<User>(res)),
}

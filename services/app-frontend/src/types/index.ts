export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface UserCreate {
  username: string
  password: string
  email: string
}

export interface UserLogin {
  username: string
  password: string
}

export interface User {
  username: string
  email: string
  telegram: string | null
}

export interface UserUpdate {
  email?: string
  telegram?: string
}

export interface Account {
  username: string
  balance: string
}

export interface DepositRequest {
  amount: string
}

export interface WithdrawRequest {
  amount: string
}

export interface WithdrawResponse {
  success: boolean
  balance: string
}

export interface Order {
  id: string
  username: string
  price: string
  status: 'paid' | 'failed'
  product_id: number | null
  quantity: number | null
  slot_id: number | null
  created_at: string
}

export interface OrderCreate {
  price: string
  product_id: number
  quantity: number
  slot_id: number
}

export interface Product {
  id: number
  name: string
  stock: number
}

export interface ProductCreate {
  name: string
  stock: number
}

export interface DeliverySlot {
  id: number
  time_slot: string
  capacity: number
  reserved: number
}

export interface DeliverySlotCreate {
  time_slot: string
  capacity: number
}

export interface Notification {
  id: string
  username: string
  email: string
  message_type: 'TEST_MESSAGE' | 'ORDER_SUCCESS' | 'ORDER_FAILED'
  subject: string | null
  body: string | null
  created_at: string
  status: 'READY_TO_SEND' | 'SENT' | 'ERROR'
}

export interface ApiError {
  detail: string
}

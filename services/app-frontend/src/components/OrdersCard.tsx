import { useEffect, useState } from 'react'
import type { DeliverySlot, Order, Product } from '@/types'
import { deliveryApi, orderApi, warehouseApi } from '@/api/client'

export default function OrdersCard() {
  const [orders, setOrders] = useState<Order[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  const [products, setProducts] = useState<Product[]>([])
  const [slots, setSlots] = useState<DeliverySlot[]>([])

  const [productId, setProductId] = useState('')
  const [quantity, setQuantity] = useState('1')
  const [slotId, setSlotId] = useState('')
  const [price, setPrice] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [createError, setCreateError] = useState('')
  const [createSuccess, setCreateSuccess] = useState('')

  const [productName, setProductName] = useState('')
  const [productStock, setProductStock] = useState('')
  const [productMessage, setProductMessage] = useState('')

  const [slotTime, setSlotTime] = useState('')
  const [slotCapacity, setSlotCapacity] = useState('')
  const [slotMessage, setSlotMessage] = useState('')

  const load = async () => {
    setIsLoading(true)
    setError('')
    try {
      const list = await orderApi.list()
      setOrders(list)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка загрузки заказов')
    } finally {
      setIsLoading(false)
    }
  }

  const loadCatalogs = async () => {
    try {
      const [productList, slotList] = await Promise.all([
        warehouseApi.listProducts(),
        deliveryApi.listSlots(),
      ])
      setProducts(productList)
      setSlots(slotList)
    } catch {
      // каталоги могут быть временно недоступны — не блокируем заказы
    }
  }

  useEffect(() => {
    load()
    loadCatalogs()
  }, [])

  const handleCreate = async () => {
    setCreateError('')
    setCreateSuccess('')
    if (!productId) {
      setCreateError('Выберите товар')
      return
    }
    if (!quantity || parseInt(quantity, 10) <= 0) {
      setCreateError('Введите корректное количество')
      return
    }
    if (!slotId) {
      setCreateError('Выберите слот доставки')
      return
    }
    if (!price || parseFloat(price) <= 0) {
      setCreateError('Введите корректную цену')
      return
    }
    setIsCreating(true)
    try {
      const order = await orderApi.create({
        price,
        product_id: parseInt(productId, 10),
        quantity: parseInt(quantity, 10),
        slot_id: parseInt(slotId, 10),
      })
      setOrders((prev) => [order, ...prev])
      setPrice('')
      setQuantity('1')
      setCreateSuccess(`Заказ #${order.id.slice(0, 8)} создан — ${order.status === 'paid' ? 'оплачен' : 'отклонён'}`)
      loadCatalogs()
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : 'Ошибка создания заказа')
    } finally {
      setIsCreating(false)
    }
  }

  const handleAddProduct = async () => {
    setProductMessage('')
    if (!productName.trim() || !productStock || parseInt(productStock, 10) < 0) {
      setProductMessage('Введите название и остаток')
      return
    }
    try {
      await warehouseApi.createProduct({ name: productName.trim(), stock: parseInt(productStock, 10) })
      setProductName('')
      setProductStock('')
      setProductMessage('Товар добавлен')
      loadCatalogs()
    } catch (err) {
      setProductMessage(err instanceof Error ? err.message : 'Ошибка добавления товара')
    }
  }

  const handleAddSlot = async () => {
    setSlotMessage('')
    if (!slotTime.trim() || !slotCapacity || parseInt(slotCapacity, 10) <= 0) {
      setSlotMessage('Введите слот и вместимость')
      return
    }
    try {
      await deliveryApi.createSlot({ time_slot: slotTime.trim(), capacity: parseInt(slotCapacity, 10) })
      setSlotTime('')
      setSlotCapacity('')
      setSlotMessage('Слот добавлен')
      loadCatalogs()
    } catch (err) {
      setSlotMessage(err instanceof Error ? err.message : 'Ошибка добавления слота')
    }
  }

  const formatDate = (iso: string) => {
    const d = new Date(iso)
    return d.toLocaleString('ru-RU')
  }

  const productLabel = (id: number | null) =>
    id === null ? '—' : (products.find((p) => p.id === id)?.name ?? `#${id}`)

  const slotLabel = (id: number | null) =>
    id === null ? '—' : (slots.find((s) => s.id === id)?.time_slot ?? `#${id}`)

  return (
    <div className="card">
      <h2>Заказы</h2>

      <div className="order-create">
        <h3>Создать заказ</h3>
        <div className="form-stack">
          <div className="form-inline">
            <select value={productId} onChange={(e) => setProductId(e.target.value)}>
              <option value="">Товар</option>
              {products.map((p) => (
                <option key={p.id} value={p.id} disabled={p.stock <= 0}>
                  {p.name} (остаток: {p.stock})
                </option>
              ))}
            </select>
            <input
              type="number"
              min="1"
              placeholder="Кол-во"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
            />
          </div>
          <div className="form-inline">
            <select value={slotId} onChange={(e) => setSlotId(e.target.value)}>
              <option value="">Слот доставки</option>
              {slots.map((s) => (
                <option key={s.id} value={s.id} disabled={s.reserved >= s.capacity}>
                  {s.time_slot} (свободно: {s.capacity - s.reserved})
                </option>
              ))}
            </select>
            <input
              type="number"
              step="0.01"
              min="0.01"
              placeholder="Цена"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
            />
          </div>
          <div>
            <button className="btn btn-primary" onClick={handleCreate} disabled={isCreating}>
              {isCreating ? 'Создание...' : 'Создать'}
            </button>
          </div>
        </div>
        {createError && <div className="alert alert-error">{createError}</div>}
        {createSuccess && <div className="alert alert-success">{createSuccess}</div>}
      </div>

      <div className="order-create">
        <h3>Добавить товар на склад</h3>
        <div className="form-inline">
          <input
            type="text"
            placeholder="Название"
            value={productName}
            onChange={(e) => setProductName(e.target.value)}
          />
          <input
            type="number"
            min="0"
            placeholder="Остаток"
            value={productStock}
            onChange={(e) => setProductStock(e.target.value)}
          />
          <button className="btn btn-secondary" onClick={handleAddProduct}>
            Добавить
          </button>
        </div>
        {productMessage && <div className="alert alert-success">{productMessage}</div>}
      </div>

      <div className="order-create">
        <h3>Добавить слот доставки</h3>
        <div className="form-inline">
          <input
            type="text"
            placeholder="Например: 2026-08-12 14:00-16:00"
            value={slotTime}
            onChange={(e) => setSlotTime(e.target.value)}
          />
          <input
            type="number"
            min="1"
            placeholder="Курьеров"
            value={slotCapacity}
            onChange={(e) => setSlotCapacity(e.target.value)}
          />
          <button className="btn btn-secondary" onClick={handleAddSlot}>
            Добавить
          </button>
        </div>
        {slotMessage && <div className="alert alert-success">{slotMessage}</div>}
      </div>

      <h3>История заказов</h3>
      {isLoading ? (
        <p>Загрузка...</p>
      ) : error ? (
        <div className="alert alert-error">{error}</div>
      ) : orders.length === 0 ? (
        <p className="empty-state">Заказов пока нет</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Товар</th>
              <th>Кол-во</th>
              <th>Слот доставки</th>
              <th>Цена</th>
              <th>Статус</th>
              <th>Дата</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((o) => (
              <tr key={o.id}>
                <td>{o.id.slice(0, 8)}</td>
                <td>{productLabel(o.product_id)}</td>
                <td>{o.quantity ?? '—'}</td>
                <td>{slotLabel(o.slot_id)}</td>
                <td>{o.price} ₽</td>
                <td>
                  <span className={`badge badge-${o.status}`}>
                    {o.status === 'paid' ? 'Оплачен' : 'Отклонён'}
                  </span>
                </td>
                <td>{formatDate(o.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

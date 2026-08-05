import { useEffect, useState } from 'react'
import type { Order } from '@/types'
import { orderApi } from '@/api/client'

export default function OrdersCard() {
  const [orders, setOrders] = useState<Order[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [price, setPrice] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [createError, setCreateError] = useState('')
  const [createSuccess, setCreateSuccess] = useState('')

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

  useEffect(() => {
    load()
  }, [])

  const handleCreate = async () => {
    setCreateError('')
    setCreateSuccess('')
    if (!price || parseFloat(price) <= 0) {
      setCreateError('Введите корректную цену')
      return
    }
    setIsCreating(true)
    try {
      const order = await orderApi.create({ price })
      setOrders((prev) => [order, ...prev])
      setPrice('')
      setCreateSuccess(`Заказ #${order.id.slice(0, 8)} создан — ${order.status === 'paid' ? 'оплачен' : 'отклонён'}`)
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : 'Ошибка создания заказа')
    } finally {
      setIsCreating(false)
    }
  }

  const formatDate = (iso: string) => {
    const d = new Date(iso)
    return d.toLocaleString('ru-RU')
  }

  return (
    <div className="card">
      <h2>Заказы</h2>

      <div className="order-create">
        <h3>Создать заказ</h3>
        <div className="form-inline">
          <input
            type="number"
            step="0.01"
            min="0.01"
            placeholder="Цена"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
          />
          <button className="btn btn-primary" onClick={handleCreate} disabled={isCreating}>
            {isCreating ? 'Создание...' : 'Создать'}
          </button>
        </div>
        {createError && <div className="alert alert-error">{createError}</div>}
        {createSuccess && <div className="alert alert-success">{createSuccess}</div>}
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
              <th>Цена</th>
              <th>Статус</th>
              <th>Дата</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((o) => (
              <tr key={o.id}>
                <td>{o.id.slice(0, 8)}</td>
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

import { useEffect, useState } from 'react'
import type { Notification } from '@/types'
import { notificationApi } from '@/api/client'

export default function NotificationsCard() {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  const load = async () => {
    setIsLoading(true)
    setError('')
    try {
      const list = await notificationApi.list()
      setNotifications(list)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка загрузки уведомлений')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const formatDate = (iso: string) => {
    const d = new Date(iso)
    return d.toLocaleString('ru-RU')
  }

  const typeLabel = (type: Notification['message_type']) => {
    switch (type) {
      case 'ORDER_SUCCESS': return 'Заказ выполнен'
      case 'ORDER_FAILED': return 'Заказ отклонён'
      case 'TEST_MESSAGE': return 'Тест'
      default: return type
    }
  }

  const statusLabel = (status: Notification['status']) => {
    switch (status) {
      case 'READY_TO_SEND': return 'В очереди'
      case 'SENT': return 'Отправлено'
      case 'ERROR': return 'Ошибка'
      default: return status
    }
  }

  return (
    <div className="card">
      <h2>Уведомления</h2>
      {isLoading ? (
        <p>Загрузка...</p>
      ) : error ? (
        <div className="alert alert-error">{error}</div>
      ) : notifications.length === 0 ? (
        <p className="empty-state">Уведомлений пока нет</p>
      ) : (
        <div className="notification-list">
          {notifications.map((n) => (
            <div key={n.id} className={`notification-item notification-${n.status.toLowerCase()}`}>
              <div className="notification-header">
                <span className="notification-type">{typeLabel(n.message_type)}</span>
                <span className="notification-status">{statusLabel(n.status)}</span>
                <span className="notification-date">{formatDate(n.created_at)}</span>
              </div>
              {n.subject && <div className="notification-subject">{n.subject}</div>}
              {n.body && <div className="notification-body">{n.body}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

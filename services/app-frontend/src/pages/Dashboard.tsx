import { useState } from 'react'
import { useAuth } from '@/context/AuthContext'
import { useTheme } from '@/context/ThemeContext'
import ProfileCard from '@/components/ProfileCard'
import BillingCard from '@/components/BillingCard'
import OrdersCard from '@/components/OrdersCard'
import NotificationsCard from '@/components/NotificationsCard'

type Tab = 'profile' | 'billing' | 'orders' | 'notifications'

export default function DashboardPage() {
  const { username, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const [activeTab, setActiveTab] = useState<Tab>('profile')

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="dashboard-header-left">
          <h1>Личный кабинет</h1>
          <span className="username">@{username}</span>
        </div>
        <div className="dashboard-header-actions">
          <button
            className="theme-toggle"
            onClick={toggleTheme}
            title={theme === 'light' ? 'Тёмная тема' : 'Светлая тема'}
            aria-label="Переключить тему"
          >
            {theme === 'light' ? '🌙' : '☀️'}
          </button>
          <button className="btn btn-secondary" onClick={logout}>
            Выйти
          </button>
        </div>
      </header>

      <nav className="dashboard-nav">
        <button
          className={activeTab === 'profile' ? 'active' : ''}
          onClick={() => setActiveTab('profile')}
        >
          Профиль
        </button>
        <button
          className={activeTab === 'billing' ? 'active' : ''}
          onClick={() => setActiveTab('billing')}
        >
          Баланс
        </button>
        <button
          className={activeTab === 'orders' ? 'active' : ''}
          onClick={() => setActiveTab('orders')}
        >
          Заказы
        </button>
        <button
          className={activeTab === 'notifications' ? 'active' : ''}
          onClick={() => setActiveTab('notifications')}
        >
          Уведомления
        </button>
      </nav>

      <main className="dashboard-content">
        {activeTab === 'profile' && <ProfileCard />}
        {activeTab === 'billing' && <BillingCard />}
        {activeTab === 'orders' && <OrdersCard />}
        {activeTab === 'notifications' && <NotificationsCard />}
      </main>
    </div>
  )
}

import { useEffect, useState } from 'react'
import type { User, UserUpdate } from '@/types'
import { userApi } from '@/api/client'

export default function ProfileCard() {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [isEditing, setIsEditing] = useState(false)
  const [editEmail, setEditEmail] = useState('')
  const [editTelegram, setEditTelegram] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  const load = async () => {
    setIsLoading(true)
    setError('')
    try {
      const u = await userApi.getProfile()
      setUser(u)
      setEditEmail(u.email || '')
      setEditTelegram(u.telegram || '')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка загрузки профиля')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const handleSave = async () => {
    const data: UserUpdate = {}
    if (editEmail !== user?.email) data.email = editEmail
    if (editTelegram !== (user?.telegram || '')) data.telegram = editTelegram || undefined

    if (Object.keys(data).length === 0) {
      setIsEditing(false)
      return
    }

    setIsSaving(true)
    try {
      const updated = await userApi.updateProfile(data)
      setUser(updated)
      setIsEditing(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка сохранения')
    } finally {
      setIsSaving(false)
    }
  }

  if (isLoading) return <div className="card">Загрузка...</div>
  if (error) return <div className="card"><div className="alert alert-error">{error}</div></div>
  if (!user) return <div className="card">Профиль не найден</div>

  return (
    <div className="card">
      <h2>Профиль</h2>
      {isEditing ? (
        <div className="form-stack">
          <div className="form-group">
            <label>Имя пользователя</label>
            <input type="text" value={user.username} disabled />
          </div>
          <div className="form-group">
            <label>Email</label>
            <input type="email" value={editEmail} onChange={(e) => setEditEmail(e.target.value)} />
          </div>
          <div className="form-group">
            <label>Telegram</label>
            <input type="text" value={editTelegram} onChange={(e) => setEditTelegram(e.target.value)} placeholder="@username" />
          </div>
          <div className="btn-row">
            <button className="btn btn-primary" onClick={handleSave} disabled={isSaving}>
              {isSaving ? 'Сохранение...' : 'Сохранить'}
            </button>
            <button className="btn btn-secondary" onClick={() => setIsEditing(false)} disabled={isSaving}>
              Отмена
            </button>
          </div>
        </div>
      ) : (
        <div className="profile-readonly">
          <div className="profile-field">
            <span className="label">Имя пользователя</span>
            <span className="value">{user.username}</span>
          </div>
          <div className="profile-field">
            <span className="label">Email</span>
            <span className="value">{user.email}</span>
          </div>
          <div className="profile-field">
            <span className="label">Telegram</span>
            <span className="value">{user.telegram || '—'}</span>
          </div>
          <button className="btn btn-primary" onClick={() => setIsEditing(true)}>
            Редактировать
          </button>
        </div>
      )}
    </div>
  )
}

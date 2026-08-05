import { useEffect, useState } from 'react'
import type { Account } from '@/types'
import { billingApi } from '@/api/client'

export default function BillingCard() {
  const [account, setAccount] = useState<Account | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [depositAmount, setDepositAmount] = useState('')
  const [withdrawAmount, setWithdrawAmount] = useState('')
  const [actionError, setActionError] = useState('')
  const [actionSuccess, setActionSuccess] = useState('')
  const [isActionLoading, setIsActionLoading] = useState(false)

  const load = async () => {
    setIsLoading(true)
    setError('')
    try {
      const acc = await billingApi.getAccount()
      setAccount(acc)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка загрузки счёта')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const handleDeposit = async () => {
    setActionError('')
    setActionSuccess('')
    if (!depositAmount || parseFloat(depositAmount) <= 0) {
      setActionError('Введите корректную сумму')
      return
    }
    setIsActionLoading(true)
    try {
      const acc = await billingApi.deposit({ amount: depositAmount })
      setAccount(acc)
      setDepositAmount('')
      setActionSuccess(`Счёт пополнен. Новый баланс: ${acc.balance}`)
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Ошибка пополнения')
    } finally {
      setIsActionLoading(false)
    }
  }

  const handleWithdraw = async () => {
    setActionError('')
    setActionSuccess('')
    if (!withdrawAmount || parseFloat(withdrawAmount) <= 0) {
      setActionError('Введите корректную сумму')
      return
    }
    setIsActionLoading(true)
    try {
      const result = await billingApi.withdraw({ amount: withdrawAmount })
      if (result.success) {
        setAccount((prev) => (prev ? { ...prev, balance: result.balance } : null))
        setWithdrawAmount('')
        setActionSuccess(`Списание успешно. Баланс: ${result.balance}`)
      } else {
        setActionError(`Недостаточно средств. Баланс: ${result.balance}`)
        setAccount((prev) => (prev ? { ...prev, balance: result.balance } : null))
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Ошибка списания')
    } finally {
      setIsActionLoading(false)
    }
  }

  if (isLoading) return <div className="card">Загрузка...</div>
  if (error) return <div className="card"><div className="alert alert-error">{error}</div></div>

  return (
    <div className="card">
      <h2>Баланс</h2>
      <div className="balance-display">
        <span className="balance-amount">{account?.balance ?? '0.00'}</span>
        <span className="balance-currency">₽</span>
      </div>

      {actionError && <div className="alert alert-error">{actionError}</div>}
      {actionSuccess && <div className="alert alert-success">{actionSuccess}</div>}

      <div className="billing-actions">
        <div className="billing-action">
          <h3>Пополнить</h3>
          <div className="form-inline">
            <input
              type="number"
              step="0.01"
              min="0.01"
              placeholder="Сумма"
              value={depositAmount}
              onChange={(e) => setDepositAmount(e.target.value)}
            />
            <button className="btn btn-primary" onClick={handleDeposit} disabled={isActionLoading}>
              Пополнить
            </button>
          </div>
        </div>

        <div className="billing-action">
          <h3>Списать</h3>
          <div className="form-inline">
            <input
              type="number"
              step="0.01"
              min="0.01"
              placeholder="Сумма"
              value={withdrawAmount}
              onChange={(e) => setWithdrawAmount(e.target.value)}
            />
            <button className="btn btn-primary" onClick={handleWithdraw} disabled={isActionLoading}>
              Списать
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

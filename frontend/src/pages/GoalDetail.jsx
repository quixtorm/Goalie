import { useState } from 'react'
import { api } from '../api'
import { date, months, uzs } from '../format'
import { Chip, ConfirmModal, Progress, Row } from '../components/ui'

export default function GoalDetail({ state, id, go, onChanged, notify }) {
  const g = state.goals.find((x) => x.id === id)
  const [modal, setModal] = useState(null)
  const [busy, setBusy] = useState(false)
  if (!g) return <div className="card text-center">Цель не найдена. <button className="btn-link" onClick={() => go('home')}>На главную</button></div>

  async function run(fn, msg) {
    setBusy(true)
    try {
      await fn()
      notify({ text: msg })
      setModal(null)
      onChanged()
    } catch (e) {
      notify({ text: e.message, error: true })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-5">
      <button className="btn-link -ml-2" onClick={() => go('home')}>← Назад</button>
      <section className="card">
        <div className="flex items-start justify-between gap-3">
          <h1 className="text-2xl font-bold">🎯 {g.name}</h1>
          <Chip tone={g.disciplined ? 'green' : 'slate'} icon={g.disciplined ? '⭐' : '%'}>
            {g.disciplined ? `${g.rate}% — за дисциплину` : `${g.rate}% — базовый`}
          </Chip>
        </div>
        <p className="mt-4 text-slate-600">Собрано</p>
        <p className="num text-4xl font-bold">{uzs(g.saved)}</p>
        <p className="num text-slate-600">из {uzs(g.amount)}</p>
        <div className="mt-3"><Progress value={g.progress} tone={g.progress >= 100 ? 'green' : 'blue'} /></div>
        <p className="mt-2 text-sm text-slate-500">{g.progress}% готово</p>
      </section>

      {g.status === 'active' && (
        <section className="card">
          <h2 className="font-bold text-lg mb-1">Когда соберёте</h2>
          <Row label="Если доход как обычно" value={`≈ ${months(g.months_best)}`} />
          <Row label="Если доход самый низкий" value={`≈ ${months(g.months_worst)}`} />
          <Row label="Срок цели" value={`до ${date(g.expiry)}`} strong />
          <Row label="Откладываем" value={`${g.percent}% дохода (≈ ${uzs(g.contribution_worst)})`} />
          <Row label="Бонус уже начислен" value={uzs(g.accrued_bonus)} />
        </section>
      )}

      <section className="card bg-blue-50 border-blue-100">
        <p className="text-slate-700">
          🔒 Деньги защищены. Аптека и больница — без штрафа. Остальное — с паузой на сутки
          {g.disciplined ? ' и потерей бонуса за дисциплину.' : '.'}
        </p>
      </section>

      {g.can_use && (
        <button className="btn-success w-full !min-h-[56px] text-lg" onClick={() => setModal('use')}>🎉 Использовать накопленное</button>
      )}
      {g.status === 'active' && (
        <button className="btn-link w-full justify-center text-slate-500" onClick={() => setModal('close')}>Закрыть цель досрочно</button>
      )}
      {g.status === 'closing' && (
        <p className="text-center text-slate-600">⏳ Цель закрывается. Деньги вернутся на основную карту через 24 часа.</p>
      )}

      <ConfirmModal open={modal === 'use'} onClose={() => setModal(null)} busy={busy} tone="success"
        title="Использовать цель?"
        text={`${uzs(g.saved)} и бонус ${uzs(g.accrued_bonus)} перейдут на основную карту.`}
        confirmLabel="Да, перевести" onConfirm={() => run(() => api.useGoal(g.id), 'Поздравляем! Деньги на основной карте')} />
      <ConfirmModal open={modal === 'close'} onClose={() => setModal(null)} busy={busy}
        title="Закрыть цель досрочно?"
        text={`${uzs(g.saved)} вернутся на основную карту через 24 часа.\nНачисленный бонус ${uzs(g.accrued_bonus)} сгорит.`}
        confirmLabel="Да, закрыть" onConfirm={() => run(() => api.closeGoal(g.id), 'Цель закроется через 24 часа')} />
    </div>
  )
}

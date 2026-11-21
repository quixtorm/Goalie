import { useState } from 'react'
import { api } from '../api'
import { date, days, months, uzs } from '../format'
import { ConfirmModal, Modal } from './ui'

// Shows what the Anti-Impulse Guardian decided about a purchase.
export default function SpendResult({ result, onClose, onChanged, notify }) {
  const [busy, setBusy] = useState(false)
  const [final, setFinal] = useState(null)
  const [confirmProceed, setConfirmProceed] = useState(false)
  if (!result) return null
  const r = result

  async function choose(option, confirm = false) {
    setBusy(true)
    try {
      const res = await api.resolve(r.stop_id, option, confirm)
      setFinal(res.message)
      onChanged?.()
    } catch (e) {
      notify?.({ text: e.message, error: true })
    } finally {
      setBusy(false)
      setConfirmProceed(false)
    }
  }

  if (final) {
    return (
      <Modal open onClose={onClose} title="Готово">
        <p className="text-lg text-slate-700">{final}</p>
        <button className="btn-primary w-full mt-6" onClick={onClose}>Хорошо</button>
      </Modal>
    )
  }

  if (r.outcome === 'released') {
    return (
      <Modal open onClose={onClose}>
        <div className="text-center">
          <div className="text-5xl mb-3" aria-hidden>💚</div>
          <h2 className="text-xl font-bold">Оплачено без штрафа</h2>
          <p className="mt-2 text-slate-700">
            {r.label}: {uzs(r.amount)} из «{r.source_name}». Здоровье важнее — это не нарушение.
          </p>
          {r.expiry && (
            <div className="mt-4 rounded-2xl bg-emerald-50 p-4 text-left text-emerald-900">
              <p>✓ Бонус {r.rate}% годовых сохранён</p>
              <p>✓ Цель будет собрана до {date(r.expiry)} ({months(r.months_worst)})</p>
            </div>
          )}
        </div>
        <button className="btn-primary w-full mt-6" onClick={onClose}>Хорошо</button>
      </Modal>
    )
  }

  const opts = Object.fromEntries((r.options || []).map((o) => [o.key, o]))
  const isObl = r.outcome === 'stopped_obligation'

  return (
    <Modal open onClose={onClose}>
      <div className="text-center">
        <div className="text-5xl mb-2" aria-hidden>{isObl ? '🛡' : '✋'}</div>
        <h2 className="text-xl font-bold">
          {isObl ? `Это деньги на «${r.source_name}»` : `Подождите — это деньги на «${r.source_name}»`}
        </h2>
        <p className="mt-1 text-slate-600">{r.label}: {r.merchant} · <span className="num font-semibold">{uzs(r.amount)}</span></p>
      </div>

      <div className="mt-5 rounded-2xl bg-amber-50 border border-amber-200 p-4">
        <p className="font-semibold text-amber-900 mb-2">Если потратить сейчас:</p>
        {isObl ? (
          <p className="text-amber-900">⚠ Платёж {date(r.due_date, false)} — не хватит <b className="num">{uzs(r.shortfall_after)}</b></p>
        ) : (
          <ul className="space-y-1.5 text-amber-900">
            <li>⏳ Цель отложится на <b>{days(r.delay_days)}</b></li>
            {r.bonus_lost > 0 && <li>💸 Бонус уменьшится на <b className="num">{uzs(r.bonus_lost)}</b> (22% → 12% годовых)</li>}
          </ul>
        )}
      </div>

      {!isObl && <p className="mt-4 text-slate-700 text-center">Часто желание проходит за сутки. Давайте вернёмся к этому завтра?</p>}

      <div className="mt-5 grid gap-2">
        {opts.cooling && <button className="btn-primary" disabled={busy} onClick={() => choose('cooling')}>⏰ Подождать до завтра</button>}
        {opts.cover_from_main && (
          <button className={opts.cooling ? 'btn-soft' : 'btn-primary'} disabled={busy} onClick={() => choose('cover_from_main')}>
            💳 Оплатить с основной карты
          </button>
        )}
        <button className="btn-soft" disabled={busy} onClick={() => choose('decline')}>Отказаться от покупки</button>
        <button className="btn-link justify-center text-slate-500" disabled={busy}
          onClick={() => (isObl ? setConfirmProceed(true) : choose('proceed'))}>Всё равно потратить</button>
      </div>

      <ConfirmModal open={confirmProceed} onClose={() => setConfirmProceed(false)} busy={busy}
        title="Точно потратить?"
        text={`${uzs(r.amount)} уйдут из денег на «${r.source_name}». Платёж ${date(r.due_date, false)} может оказаться под угрозой.`}
        confirmLabel="Да, потратить" onConfirm={() => choose('proceed', true)} />
    </Modal>
  )
}

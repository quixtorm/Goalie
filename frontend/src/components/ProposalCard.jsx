import { useState } from 'react'
import { api } from '../api'

const ICON = { goal_percent: '🎯', obligation_topup: '🛡', cash_gap: '💡', cooling_ready: '⏰', create_goal: '✨',
  create_obligation: '🗓' }

export default function ProposalCard({ p, onDone, notify }) {
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(p.status !== 'pending' ? (p.result || statusText(p.status)) : null)

  async function act(fn) {
    setBusy(true)
    try {
      const r = await fn()
      setDone(r.message || (r.status === 'rejected' ? 'Хорошо, не сейчас.' : 'Готово'))
      onDone?.()
    } catch (e) {
      notify?.({ text: e.message, error: true })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card border-blue-100">
      <div className="flex gap-3">
        <div className="text-2xl" aria-hidden>{ICON[p.kind] || '💬'}</div>
        <div className="flex-1 min-w-0">
          <h3 className="font-bold text-lg leading-snug">{p.title}</h3>
          <p className="mt-1 text-slate-700 whitespace-pre-line">{p.text}</p>
        </div>
      </div>
      {done ? (
        <p className="mt-4 rounded-2xl bg-emerald-50 text-emerald-800 px-4 py-3 font-medium">✓ {done}</p>
      ) : (
        <div className="mt-4 grid gap-2">
          {p.options.map((o, i) => (
            o.key === 'proceed'
              ? <button key={o.key} className="btn-link justify-center text-slate-500" disabled={busy}
                  onClick={() => act(() => api.confirm(p.id, o.key))}>{o.label}</button>
              : <button key={o.key} className={i === 0 ? 'btn-primary' : 'btn-soft'} disabled={busy}
                  onClick={() => act(() => api.confirm(p.id, o.key))}>{busy && i === 0 ? 'Секунду…' : o.label}</button>
          ))}
          {p.kind !== 'cooling_ready' && (
            <button className="btn-link justify-center text-slate-500" disabled={busy}
              onClick={() => act(() => api.reject(p.id))}>Не сейчас</button>
          )}
        </div>
      )}
    </div>
  )
}

function statusText(s) {
  return { confirmed: 'Выполнено', rejected: 'Отклонено', resolved: 'Уже неактуально' }[s] || s
}

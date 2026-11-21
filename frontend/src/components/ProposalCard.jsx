import { useState } from 'react'
import { api } from '../api'
import { useApp } from '../ctx'

const ICON = { goal_percent: '🎯', obligation_topup: '🛡', cash_gap: '💡', cooling_ready: '⏰', create_goal: '✨', create_obligation: '🗓',
  transfer_save: '👪', security_notice: '🔐' }

export default function ProposalCard({ p, onDone, compact = false }) {
  const { t, notify, refresh, withStepUp } = useApp()
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(p.status !== 'pending' ? (p.result || null) : null)
  const closed = p.status !== 'pending' && !done
  const security = p.kind === 'security_notice'

  async function act(fn) {
    setBusy(true)
    try {
      const r = await fn()
      setDone(r.message || (r.status === 'rejected' ? (security ? t('itWasMe') : t('later')) : t('done')))
      refresh()
      onDone?.()
    } catch (e) {
      if (!e.cancelled) notify({ text: e.message, error: true })
    } finally {
      setBusy(false)
    }
  }

  // "proceed" (spend from the goal anyway) releases protected money -> step-up PIN
  const confirmOpt = (o) => act(() => (o.key === 'proceed'
    ? withStepUp((tok) => api.confirm(p.id, o.key, tok))
    : api.confirm(p.id, o.key)))

  return (
    <div className={`card !p-4 animate-rise ${security ? 'border-amber-300/40' : ''}`}>
      <div className="flex gap-3">
        <div className="text-2xl leading-none mt-0.5" aria-hidden>{ICON[p.kind] || '💬'}</div>
        <div className="flex-1 min-w-0">
          <h3 className="font-bold leading-snug">{p.title}</h3>
          <p className={`mt-1 text-muted whitespace-pre-line ${compact ? 'line-clamp-3' : ''}`}>{p.text}</p>
        </div>
      </div>
      {done || closed ? (
        <p className="mt-3 rounded-btn bg-emerald-400/10 text-emerald-300 px-4 py-2.5 font-medium">✓ {done || t('done')}</p>
      ) : (
        <div className={`mt-4 grid gap-2 ${compact ? 'grid-cols-2' : ''}`}>
          {p.options.filter((o) => !compact || o.key !== 'proceed').slice(0, compact ? 1 : 9).map((o, i) => (
            o.key === 'proceed'
              ? <button key={o.key} className="btn-link" disabled={busy} onClick={() => confirmOpt(o)}>{o.label}</button>
              : <button key={o.key} className={`${i === 0 ? (security ? 'btn bg-rose-600 text-white hover:bg-rose-500' : 'btn-primary') : 'btn-ghost'} !min-h-[46px]`}
                  disabled={busy} onClick={() => confirmOpt(o)}>
                  {busy && i === 0 ? t('busy') : (compact && !security ? t('confirm') : o.label)}
                </button>
          ))}
          {p.kind !== 'cooling_ready' && (
            compact
              ? <button className="btn-ghost !min-h-[46px]" disabled={busy} onClick={() => act(() => api.reject(p.id))}>{security ? t('itWasMe') : t('later')}</button>
              : <button className="btn-link" disabled={busy} onClick={() => act(() => api.reject(p.id))}>{security ? t('itWasMe') : t('notNow')}</button>
          )}
        </div>
      )}
    </div>
  )
}

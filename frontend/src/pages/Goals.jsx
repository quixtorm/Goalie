import { useState } from 'react'
import { api } from '../api'
import { useApp } from '../ctx'
import { months } from '../format'
import BankCard from '../components/BankCard'
import { coolingFor } from '../components/WalletStack'
import { Icon } from '../components/ui'

export default function Goals() {
  const { state, t, lang, go, notify, refresh } = useApp()
  const [busy, setBusy] = useState(false)
  const active = state.goals.filter((g) => g.status === 'active')
  const others = state.goals.filter((g) => g.status !== 'active')
  const canAdd = active.length < state.limits.max_goals

  async function move(i, dir) {
    const ids = active.map((g) => g.id)
    const j = i + dir
    if (j < 0 || j >= ids.length) return
    ;[ids[i], ids[j]] = [ids[j], ids[i]]
    setBusy(true)
    try { await api.reorder(ids); refresh() } catch (e) { notify({ text: e.message, error: true }) } finally { setBusy(false) }
  }

  return (
    <div className="space-y-5 pt-4">
      <div className="px-1 flex items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">{t('goalsTitle')}</h1>
          <p className="text-muted text-sm mt-1">{t('goalsUsed', state.used_percent, state.limits.max_total_percent)}</p>
        </div>
        <span className="text-muted text-sm">{active.length}/{state.limits.max_goals}</span>
      </div>

      {active.length > 1 && (
        <p className="card !p-4 text-sm text-muted flex gap-2"><Icon name="shield" size={18} className="shrink-0 mt-0.5" />{t('priorityHint')}</p>
      )}
      {state.goals.length === 0 && <div className="card text-center text-muted">{t('noGoals')}</div>}

      <div className="space-y-6">
        {[...active, ...others].map((g, i) => (
          <div key={g.id} className="animate-rise" style={{ animationDelay: `${i * 60}ms` }}>
            <BankCard goal={g} cooling={coolingFor(state, g.id)} onClick={() => go('goal', { id: g.id })}
              onUse={g.can_use ? () => go('goal', { id: g.id }) : undefined} />
            <div className="mt-3 flex items-center gap-2 px-1">
              <span className="flex-1 text-sm text-muted">
                {g.status === 'active' ? `${months(g.months_best, lang)} – ${months(g.months_worst, lang)}` : t('completed')}
                {' · '}{t('bonusShort', g.rate)}
              </span>
              {g.status === 'active' && active.length > 1 && (
                <>
                  <button className="press w-11 h-11 rounded-full bg-card2 border border-line grid place-items-center disabled:opacity-30"
                    disabled={busy || i === 0} onClick={() => move(i, -1)} aria-label={`${t('moveUp')}: ${g.name}`}><Icon name="chevronU" size={20} /></button>
                  <button className="press w-11 h-11 rounded-full bg-card2 border border-line grid place-items-center disabled:opacity-30"
                    disabled={busy || i === active.length - 1} onClick={() => move(i, 1)} aria-label={`${t('moveDown')}: ${g.name}`}><Icon name="chevronD" size={20} /></button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>

      {canAdd && (
        <button className="btn-primary w-full" onClick={() => go('create')}><Icon name="plus" /> {t('newGoal')}</button>
      )}
    </div>
  )
}

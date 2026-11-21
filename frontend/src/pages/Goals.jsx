import { useState } from 'react'
import { api } from '../api'
import { useApp } from '../ctx'
import { date, months } from '../format'
import { PRIO_BG, PrioBadge } from '../components/SubcardStack'
import { Chip, Icon, Money, Progress } from '../components/ui'

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
    try {
      await api.reorder(ids)
      refresh()
    } catch (e) {
      notify({ text: e.message, error: true })
    } finally {
      setBusy(false)
    }
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

      <div className="space-y-3">
        {[...active, ...others].map((g, i) => (
          <div key={g.id} className="card !p-0 overflow-hidden animate-rise" style={{ animationDelay: `${i * 50}ms` }}>
            <div className={`h-1.5 bg-gradient-to-r ${g.priority ? PRIO_BG[g.priority - 1] : 'from-slate-500 to-slate-600'}`} />
            <div className="p-4 flex gap-3">
              <button className="press flex-1 min-w-0 text-left" onClick={() => go('goal', { id: g.id })}>
                <div className="flex items-center gap-2.5">
                  {g.priority ? <PrioBadge n={g.priority} className={`bg-gradient-to-br ${PRIO_BG[g.priority - 1]}`} /> : <Chip tone="green" icon="✓">{t('completed')}</Chip>}
                  <span className="font-bold text-lg truncate">{g.name}</span>
                </div>
                <p className="mt-2 text-sm"><Money value={g.saved} /> <span className="text-muted">/ <Money value={g.amount} /></span></p>
                <Progress className="mt-2" value={g.progress} tone={g.progress >= 100 ? 'green' : 'blue'} />
                <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted">
                  <span>{g.progress}%</span>
                  {g.status === 'active' && <span>{t('until', date(g.expiry, lang))}</span>}
                  {g.status === 'active' && <span>{months(g.months_best, lang)}–{months(g.months_worst, lang)}</span>}
                  <Chip tone={g.disciplined ? 'green' : 'slate'} icon={g.disciplined ? '★' : null}>{t('bonusShort', g.rate)}</Chip>
                </div>
              </button>
              {g.status === 'active' && active.length > 1 && (
                <div className="flex flex-col gap-1.5 shrink-0">
                  <button className="press w-11 h-11 rounded-full bg-card2 border border-line grid place-items-center disabled:opacity-30"
                    disabled={busy || i === 0} onClick={() => move(i, -1)} aria-label={`${t('moveUp')}: ${g.name}`}>
                    <Icon name="chevronU" size={20} />
                  </button>
                  <button className="press w-11 h-11 rounded-full bg-card2 border border-line grid place-items-center disabled:opacity-30"
                    disabled={busy || i === active.length - 1} onClick={() => move(i, 1)} aria-label={`${t('moveDown')}: ${g.name}`}>
                    <Icon name="chevronD" size={20} />
                  </button>
                </div>
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

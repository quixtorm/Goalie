import { useState } from 'react'
import { useApp } from '../ctx'
import { date } from '../format'
import { Icon, Money } from './ui'

// Card colours by priority (#1, #2, #3).
export const PRIO_BG = [
  'from-emerald-500 to-teal-700',
  'from-violet-500 to-indigo-700',
  'from-amber-400 to-orange-600',
]

export function PrioBadge({ n, className = '' }) {
  return (
    <span className={`inline-grid place-items-center min-w-8 h-8 px-2 rounded-full bg-black/25 text-white text-sm font-bold ${className}`}
      aria-label={`priority ${n}`}>#{n}</span>
  )
}

// Wallet stack: subcards sit behind the main card and slide out above it.
export default function SubcardStack({ goals, max }) {
  const { t, lang, go } = useApp()
  const [open, setOpen] = useState(false)
  const n = goals.length

  if (n === 0) {
    return (
      <button onClick={() => go('create')}
        className="press w-full mb-3 rounded-card border-2 border-dashed border-white/25 bg-white/5 hover:bg-white/10 min-h-[64px] flex items-center justify-center gap-2 font-semibold text-white/90">
        <Icon name="plus" /> {t('addSubcard')}
      </button>
    )
  }

  return (
    <div className="mb-3">
      <button onClick={() => setOpen(!open)} aria-expanded={open}
        className="press w-full flex items-center justify-between rounded-btn bg-white/10 hover:bg-white/15 px-4 min-h-[48px] font-semibold text-white">
        <span className="flex items-center gap-2">
          <Icon name="target" size={20} />
          {open ? t('hideSubcards') : t('showSubcards')} ({n}/{max})
        </span>
        <Icon name={open ? 'chevronU' : 'chevronD'} size={20} />
      </button>

      {!open && (
        // peeking edges of the cards hidden behind the main card
        <div className="relative h-4 mt-2 mx-3" aria-hidden>
          {goals.slice(0, 3).map((g, i) => (
            <div key={g.id} className={`absolute inset-x-0 h-4 rounded-t-[14px] bg-gradient-to-r ${PRIO_BG[(g.priority || i + 1) - 1] || PRIO_BG[2]} opacity-80`}
              style={{ top: i * 5, left: (2 - i) * 6, right: (2 - i) * 6, zIndex: 3 - i }} />
          ))}
        </div>
      )}

      {open && (
        <div className="mt-3 space-y-2.5">
          {goals.map((g, i) => (
            <button key={g.id} onClick={() => go('goal', { id: g.id })}
              className={`press w-full text-left rounded-card p-4 text-white bg-gradient-to-br ${PRIO_BG[(g.priority || i + 1) - 1] || PRIO_BG[2]} shadow-soft animate-slide-out`}
              style={{ animationDelay: `${i * 70}ms` }}>
              <div className="flex items-center gap-3">
                <PrioBadge n={g.priority || '✓'} />
                <span className="flex-1 min-w-0 font-bold text-lg truncate">{g.name}</span>
                <span className="text-sm text-white/85 whitespace-nowrap">
                  {g.status === 'completed' ? '✓' : t('until', date(g.expiry, lang))}
                </span>
              </div>
              <div className="mt-3 h-2 rounded-full bg-black/20 overflow-hidden">
                <div className="h-full rounded-full bg-white transition-[width] duration-700" style={{ width: `${g.progress}%` }} />
              </div>
              <div className="mt-2 flex justify-between text-sm text-white/90">
                <span className="font-semibold">{g.progress}%</span>
                <span><Money value={g.saved} /> / <Money value={g.amount} /></span>
              </div>
            </button>
          ))}
          {n < max && (
            <button onClick={() => go('create')}
              className="press w-full rounded-card border-2 border-dashed border-white/25 min-h-[56px] flex items-center justify-center gap-2 text-white/85 hover:bg-white/5 animate-slide-out"
              style={{ animationDelay: `${n * 70}ms` }} aria-label={t('addSubcard')}>
              <Icon name="plus" /> {t('addSubcard')}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

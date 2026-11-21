import { useState } from 'react'
import { api } from '../api'
import { useApp } from '../ctx'
import { paletteFor } from './BankCard'
import { Icon, Sheet } from './ui'

// Accessible priority editor (buttons work with touch, keyboard and screen readers).
export default function ReorderSheet({ open, onClose }) {
  const { state, t, notify, refresh } = useApp()
  const [busy, setBusy] = useState(false)
  const active = state.goals.filter((g) => g.status === 'active')

  async function move(i, dir) {
    const ids = active.map((g) => g.id)
    const j = i + dir
    if (j < 0 || j >= ids.length) return
    ;[ids[i], ids[j]] = [ids[j], ids[i]]
    setBusy(true)
    try { await api.reorder(ids); refresh() } catch (e) { notify({ text: e.message, error: true }) } finally { setBusy(false) }
  }

  return (
    <Sheet open={open} onClose={onClose} label={t('reorderTitle')}>
      <div className="px-5 pb-8 space-y-3 overflow-y-auto">
        <h2 className="text-xl font-bold">{t('reorderTitle')}</h2>
        <p className="text-muted text-sm">{t('priorityHint')}</p>
        {active.map((g, i) => (
          <div key={g.id} className="flex items-center gap-3 rounded-card border border-line bg-card2 p-3">
            <span className="w-11 h-11 rounded-[14px] grid place-items-center font-bold text-white" style={{ background: paletteFor(g.priority).bg }}>#{g.priority}</span>
            <span className="flex-1 min-w-0 font-semibold truncate">{g.name}</span>
            <button className="press w-11 h-11 rounded-full bg-white/5 border border-line grid place-items-center disabled:opacity-30"
              disabled={busy || i === 0} onClick={() => move(i, -1)} aria-label={`${t('moveUp')}: ${g.name}`}><Icon name="chevronU" size={20} /></button>
            <button className="press w-11 h-11 rounded-full bg-white/5 border border-line grid place-items-center disabled:opacity-30"
              disabled={busy || i === active.length - 1} onClick={() => move(i, 1)} aria-label={`${t('moveDown')}: ${g.name}`}><Icon name="chevronD" size={20} /></button>
          </div>
        ))}
      </div>
    </Sheet>
  )
}

import { useState } from 'react'
import { api } from '../api'
import { useApp } from '../ctx'
import { date, months, uzs } from '../format'
import BankCard, { PALETTES, paletteFor } from '../components/BankCard'
import ReorderSheet from '../components/ReorderSheet'
import { coolingFor } from '../components/WalletStack'
import { ConfirmSheet, Icon, Money, Row, Sheet } from '../components/ui'

// Card detail screen, structured like a real bank card screen:
// tinted header with the card, three round actions, then list rows that open sheets.
export default function GoalDetail({ id }) {
  const { state, t, lang, go, notify, refresh, openAgent } = useApp()
  const g = state.goals.find((x) => x.id === id)
  const [modal, setModal] = useState(null)
  const [busy, setBusy] = useState(false)
  if (!g) return <div className="pt-4"><button className="btn-link" onClick={() => go('goals')}>{t('back')}</button></div>

  const pal = g.priority ? paletteFor(g.priority) : PALETTES.done
  const active = g.status === 'active'
  const cooling = coolingFor(state, g.id)
  const history = [
    ...(state.last_salary?.goals || []).filter((x) => x.id === g.id)
      .map((x) => ({ id: 'sal', title: t('contribution'), amount: x.amount, date: state.last_salary.date })),
    ...state.transactions.filter((tx) => tx.source === g.id).map((tx) => ({ id: tx.id, title: tx.title, amount: tx.amount, date: tx.date })),
  ]

  async function run(fn, msg) {
    setBusy(true)
    try { await fn(); notify({ text: msg }); setModal(null); refresh() } catch (e) { notify({ text: e.message, error: true }) } finally { setBusy(false) }
  }

  const actions = [
    { key: 'use', icon: 'check', label: t('actUse'), disabled: !g.can_use, onClick: () => setModal('use') },
    { key: 'prio', icon: 'sort', label: t('actPriority'), disabled: !active, onClick: () => setModal('prio') },
    { key: 'close', icon: 'close', label: t('actClose'), disabled: !active, onClick: () => setModal('close') },
  ]
  const rows = [
    { key: 'info', icon: 'info', title: t('rowGoal'), sub: t('rowGoalSub', g.percent) },
    { key: 'bonus', icon: 'star', title: t('rowBonus'), sub: t('rowBonusSub', g.rate, uzs(g.accrued_bonus)) },
    { key: 'history', icon: 'chart', title: t('rowHistory'), sub: t('rowHistorySub') },
    { key: 'agent', icon: 'sparkle', title: t('rowAgent'), sub: t('rowAgentSub') },
  ]

  return (
    <div className="pb-4">
      {/* tinted top section in the card's palette */}
      <section className="-mx-4 px-4 pt-3 pb-7 rounded-b-[32px] shadow-soft"
        style={{ background: `linear-gradient(180deg, ${pal.tint} 0%, #1B1E24 100%)` }}>
        <div className="flex items-center gap-2 mb-4">
          <button className="press w-11 h-11 -ml-2 grid place-items-center rounded-full hover:bg-white/10" onClick={() => go('goals')} aria-label={t('back')}>
            <Icon name="back" size={24} />
          </button>
          <h1 className="text-xl font-bold truncate">{g.name}</h1>
        </div>

        <BankCard goal={g} cooling={cooling} onUse={g.can_use ? () => setModal('use') : undefined} />

        <div className="mt-6 grid grid-cols-3 gap-2">
          {actions.map((a) => (
            <button key={a.key} onClick={a.onClick} disabled={a.disabled}
              className="press flex flex-col items-center gap-2 disabled:opacity-35 disabled:pointer-events-none">
              <span className="w-16 h-16 rounded-full grid place-items-center bg-white/12 border border-white/15 hover:bg-white/20" style={{ backgroundColor: 'rgba(255,255,255,.12)' }}>
                <Icon name={a.icon} size={26} />
              </span>
              <span className="text-sm font-semibold">{a.label}</span>
            </button>
          ))}
        </div>
      </section>

      {/* list rows */}
      <section className="mt-5 card !p-2">
        {rows.map((r, i) => (
          <button key={r.key} onClick={() => (r.key === 'agent' ? openAgent({ send: t('askAboutGoal', g.name) }) : setModal(r.key))}
            className={`press w-full flex items-center gap-3 p-3 text-left rounded-[16px] hover:bg-white/5 ${i < rows.length - 1 ? 'border-b border-dashed border-line' : ''}`}>
            <span className={`w-12 h-12 shrink-0 rounded-[14px] grid place-items-center ${r.key === 'agent' ? 'bg-amber-300/15 text-amber-200' : 'bg-card2'}`}>
              <Icon name={r.icon} size={22} fill={r.key === 'agent'} strokeWidth={r.key === 'agent' ? 0 : 1.8} />
            </span>
            <span className="flex-1 min-w-0">
              <span className="block font-semibold">{r.title}</span>
              <span className="block text-sm text-muted truncate">{r.sub}</span>
            </span>
            <Icon name="chevronR" size={20} className="text-muted shrink-0" />
          </button>
        ))}
      </section>

      {/* row sheets */}
      <Sheet open={modal === 'info'} onClose={() => setModal(null)} label={t('rowGoal')}>
        <div className="px-6 pb-8 overflow-y-auto">
          <h2 className="text-xl font-bold mb-2">{t('rowGoal')}</h2>
          <Row label={t('collected')}><Money value={g.saved} /> / <Money value={g.amount} /></Row>
          <Row label={t('perMonth')}>{t('pctIncome', g.percent)} · ≈ <Money value={g.contribution_worst} /></Row>
          {active && <Row label={t('bestCase')}>≈ {months(g.months_best, lang)}</Row>}
          {active && <Row label={t('worstCase')}>≈ {months(g.months_worst, lang)}</Row>}
          {active && <Row label={t('deadline')} strong>{t('until', date(g.expiry, lang))}</Row>}
          <p className="mt-4 text-sm text-muted flex gap-2"><Icon name="lock" size={18} className="shrink-0" />{t('lockShort')}</p>
        </div>
      </Sheet>
      <Sheet open={modal === 'bonus'} onClose={() => setModal(null)} label={t('rowBonus')}>
        <div className="px-6 pb-8">
          <h2 className="text-xl font-bold mb-2">{t('rowBonus')}</h2>
          <Row label={t('rate')} strong>{g.disciplined ? t('bonusDisc', g.rate) : t('bonusBase', g.rate)}</Row>
          <Row label={t('bonusNow')}><Money value={g.accrued_bonus} /></Row>
          <p className="mt-4 text-sm text-muted">{t('bannerSub')}</p>
        </div>
      </Sheet>
      <Sheet open={modal === 'history'} onClose={() => setModal(null)} label={t('rowHistory')}>
        <div className="px-6 pb-8 overflow-y-auto">
          <h2 className="text-xl font-bold mb-2">{t('rowHistory')}</h2>
          {history.length === 0 && <p className="text-muted">{t('noHistory')}</p>}
          {history.map((h) => (
            <div key={h.id} className="flex justify-between gap-3 py-3 border-b border-line last:border-0">
              <span className="min-w-0"><span className="block truncate">{h.title}</span><span className="text-sm text-muted">{date(h.date, lang, false)}</span></span>
              <span className={`font-semibold shrink-0 ${h.amount > 0 ? 'text-emerald-300' : ''}`}>{h.amount > 0 ? '+' : ''}<Money value={h.amount} /></span>
            </div>
          ))}
        </div>
      </Sheet>
      <ReorderSheet open={modal === 'prio'} onClose={() => setModal(null)} />

      <ConfirmSheet open={modal === 'use'} onClose={() => setModal(null)} busy={busy} tone="success"
        title={t('useTitle')} text={t('useText', uzs(g.saved), uzs(g.accrued_bonus))}
        confirmLabel={t('useOk')} onConfirm={() => run(() => api.useGoal(g.id), t('done'))} />
      <ConfirmSheet open={modal === 'close'} onClose={() => setModal(null)} busy={busy}
        title={t('closeTitle')} text={t('closeText', uzs(g.saved), uzs(g.accrued_bonus))}
        confirmLabel={t('closeOk')} onConfirm={() => run(() => api.closeGoal(g.id), t('closingNote'))} />
    </div>
  )
}

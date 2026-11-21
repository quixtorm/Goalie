import { useState } from 'react'
import { api } from '../api'
import { useApp } from '../ctx'
import { date, months, uzs } from '../format'
import { PRIO_BG, PrioBadge } from '../components/SubcardStack'
import { BackButton, Chip, ConfirmSheet, Icon, Money, Ring, Row } from '../components/ui'

export default function GoalDetail({ id }) {
  const { state, t, lang, go, notify, refresh } = useApp()
  const g = state.goals.find((x) => x.id === id)
  const [modal, setModal] = useState(null)
  const [busy, setBusy] = useState(false)
  if (!g) return <div className="pt-4"><BackButton onClick={() => go('goals')} /><div className="card text-center mt-3">—</div></div>

  async function run(fn, msg) {
    setBusy(true)
    try {
      await fn()
      notify({ text: msg })
      setModal(null)
      refresh()
    } catch (e) {
      notify({ text: e.message, error: true })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-5 pt-4">
      <BackButton onClick={() => go('goals')} />

      <section className="card text-center relative overflow-hidden">
        {g.priority > 0 && <div className={`absolute inset-x-0 top-0 h-1.5 bg-gradient-to-r ${PRIO_BG[g.priority - 1]}`} />}
        <div className="flex items-center justify-center gap-2">
          {g.priority > 0 && <PrioBadge n={g.priority} className={`bg-gradient-to-br ${PRIO_BG[g.priority - 1]}`} />}
          <h1 className="text-2xl font-bold">{g.name}</h1>
        </div>
        <div className="mt-4 flex justify-center"><Ring value={g.progress} /></div>
        <p className="mt-2 text-muted">{t('collected')}</p>
        <Money value={g.saved} className="block text-3xl font-bold" />
        <p className="text-muted">/ <Money value={g.amount} /></p>
        <div className="mt-3">
          <Chip tone={g.disciplined ? 'green' : 'slate'} icon={g.disciplined ? '★' : null}>
            {g.disciplined ? t('bonusDisc', g.rate) : t('bonusBase', g.rate)}
          </Chip>
        </div>
      </section>

      {g.status === 'active' && (
        <section className="card !py-2">
          <Row label={t('bestCase')}>≈ {months(g.months_best, lang)}</Row>
          <Row label={t('worstCase')}>≈ {months(g.months_worst, lang)}</Row>
          <Row label={t('deadline')} strong>{t('until', date(g.expiry, lang))}</Row>
          <Row label={t('perMonth')}>{t('pctIncome', g.percent)} · ≈ <Money value={g.contribution_worst} /></Row>
          <Row label={t('bonusAccrued')}><Money value={g.accrued_bonus} /></Row>
        </section>
      )}

      <section className="card !p-4 flex gap-3 bg-brand/10 border-brand/25">
        <Icon name="lock" className="shrink-0 text-brand-light mt-0.5" />
        <p className="text-ink/90 text-sm">{t('lockShort')}</p>
      </section>

      {g.can_use && (
        <button className="btn-success w-full !min-h-[56px] text-lg" onClick={() => setModal('use')}>🎉 {t('use')}</button>
      )}
      {g.status === 'active' && (
        <button className="btn-link w-full" onClick={() => setModal('close')}>{t('closeEarly')}</button>
      )}
      {g.status === 'closing' && <p className="text-center text-muted">⏳ {t('closingNote')}</p>}

      <ConfirmSheet open={modal === 'use'} onClose={() => setModal(null)} busy={busy} tone="success"
        title={t('useTitle')} text={t('useText', uzs(g.saved), uzs(g.accrued_bonus))}
        confirmLabel={t('useOk')} onConfirm={() => run(() => api.useGoal(g.id), t('done'))} />
      <ConfirmSheet open={modal === 'close'} onClose={() => setModal(null)} busy={busy}
        title={t('closeTitle')} text={t('closeText', uzs(g.saved), uzs(g.accrued_bonus))}
        confirmLabel={t('closeOk')} onConfirm={() => run(() => api.closeGoal(g.id), t('closingNote'))} />
    </div>
  )
}

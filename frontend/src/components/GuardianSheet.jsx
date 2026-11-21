import { useState } from 'react'
import { api } from '../api'
import { useApp } from '../ctx'
import { date, days, months, uzs } from '../format'
import { ConfirmSheet, Icon, Money, Sheet } from './ui'

// Anti-Impulse Guardian: opens automatically on every spend attempt from a goal or reserve.
export default function GuardianSheet({ result, onClose }) {
  const { t, lang, notify, refresh, withStepUp } = useApp()
  const [busy, setBusy] = useState(false)
  const [final, setFinal] = useState(null)
  const [sure, setSure] = useState(false)
  if (!result) return null
  const r = result

  async function choose(option, confirm = false) {
    setBusy(true)
    try {
      // "proceed anyway" releases protected money -> PIN; the other options don't
      const res = option === 'proceed'
        ? await withStepUp((tok) => api.resolve(r.stop_id, option, confirm, tok))
        : await api.resolve(r.stop_id, option, confirm)
      setFinal(res.message)
      refresh()
    } catch (e) {
      if (!e.cancelled) notify({ text: e.message, error: true })
    } finally {
      setBusy(false)
      setSure(false)
    }
  }

  if (final) {
    return (
      <Sheet open onClose={onClose} label={t('done')} z={60}>
        <div className="px-6 pb-8 text-center">
          <div className="mx-auto w-16 h-16 rounded-full bg-brand/15 text-brand-light grid place-items-center mb-3"><Icon name="check" size={30} /></div>
          <p className="text-lg">{final}</p>
          <button className="btn-primary w-full mt-6" onClick={onClose}>{t('ok')}</button>
        </div>
      </Sheet>
    )
  }

  if (r.outcome === 'released') {
    return (
      <Sheet open onClose={onClose} label={t('gFreeTitle')} z={60}>
        <div className="px-6 pb-8 text-center">
          <div className="mx-auto w-16 h-16 rounded-full bg-emerald-400/15 text-emerald-300 grid place-items-center mb-3 text-3xl" aria-hidden>💚</div>
          <h2 className="text-xl font-bold">{t('gFreeTitle')}</h2>
          <p className="mt-2 text-muted">{t('gFreeText', r.label, uzs(r.amount), r.source_name)}</p>
          {r.expiry && (
            <div className="mt-4 rounded-card bg-emerald-400/10 border border-emerald-400/25 p-4 text-left text-emerald-200 space-y-1">
              <p>✓ {t('gKept', r.rate)}</p>
              <p>✓ {t('gGoalBy', date(r.expiry, lang), months(r.months_worst, lang))}</p>
            </div>
          )}
          <button className="btn-primary w-full mt-6" onClick={onClose}>{t('ok')}</button>
        </div>
      </Sheet>
    )
  }

  const opts = Object.fromEntries((r.options || []).map((o) => [o.key, o]))
  const isObl = r.outcome === 'stopped_obligation'

  return (
    <Sheet open onClose={onClose} label={isObl ? t('gObl', r.source_name) : t('gWait', r.source_name)} z={60}>
      <div className="px-6 pb-8 overflow-y-auto">
        <div className="text-center">
          <div className="mx-auto w-16 h-16 rounded-full bg-amber-400/15 grid place-items-center text-3xl mb-2" aria-hidden>{isObl ? '🛡' : '✋'}</div>
          <h2 className="text-xl font-bold">{isObl ? t('gObl', r.source_name) : t('gWait', r.source_name)}</h2>
          <p className="mt-1 text-muted">{r.label}: {r.merchant} · <Money value={r.amount} className="font-semibold text-ink" /></p>
        </div>

        <div className="mt-5 rounded-card bg-amber-400/10 border border-amber-400/25 p-4 text-amber-100">
          <p className="font-semibold mb-2">{t('gIf')}</p>
          {isObl ? (
            <p>⚠ {t('gOblWarn', date(r.due_date, lang, false), uzs(r.shortfall_after))}</p>
          ) : (
            <ul className="space-y-1.5">
              <li>⏳ {t('gDelay', days(r.delay_days, lang))}</li>
              {r.bonus_lost > 0 && <li>💸 {t('gBonus', uzs(r.bonus_lost))} <span className="text-amber-200/70">({t('gRates')})</span></li>}
            </ul>
          )}
        </div>

        {!isObl && <p className="mt-4 text-center text-muted">{t('gHint')}</p>}

        <div className="mt-5 grid gap-2">
          {opts.cooling && <button className="btn-primary" disabled={busy} onClick={() => choose('cooling')}><Icon name="clock" size={20} /> {t('gCool')}</button>}
          {opts.cover_from_main && (
            <button className={opts.cooling ? 'btn-ghost' : 'btn-primary'} disabled={busy} onClick={() => choose('cover_from_main')}>
              <Icon name="pay" size={20} /> {t('gCover')}
            </button>
          )}
          <button className="btn-ghost" disabled={busy} onClick={() => choose('decline')}>{t('gDecline')}</button>
          <button className="btn-link" disabled={busy} onClick={() => (isObl ? setSure(true) : choose('proceed'))}>{t('gProceed')}</button>
        </div>
      </div>

      <ConfirmSheet open={sure} onClose={() => setSure(false)} busy={busy} title={t('gSure')}
        text={t('gSureText', uzs(r.amount), r.source_name, date(r.due_date, lang, false))}
        confirmLabel={t('gSureOk')} onConfirm={() => choose('proceed', true)} />
    </Sheet>
  )
}

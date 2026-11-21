import { useState } from 'react'
import { api } from '../api'
import { useApp } from '../ctx'
import { months as fmtMonths, uzs } from '../format'
import { ConfirmSheet, Icon, Money } from './ui'

// Offer cards rendered from the advise_credit result (code ranking of the DEMO catalog). Display only.
export default function CreditAdvice({ data }) {
  const { t, lang } = useApp()
  if (!data || !data.options?.length) return null
  const w = data.wait_option
  const noSafe = (data.warnings || []).includes('no_safe')
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between px-1">
        <span className="font-bold">{t('offersTitle')}</span>
        <span className="rounded-full border border-amber-300/40 bg-amber-300/10 text-amber-200 text-xs font-semibold px-2.5 py-0.5">{t('demoData')}</span>
      </div>
      {noSafe && <p className="rounded-card bg-rose-500/10 border border-rose-400/30 text-rose-200 p-3 text-sm">⚠ {t('noSafeWarn')}</p>}
      {data.options.map((o, i) => <OfferCard key={o.key} o={o} amount={data.amount} delay={i * 70} />)}
      {w && (
        <div className="rounded-card border border-emerald-400/25 bg-emerald-400/[0.06] px-4 py-3 text-sm flex items-center gap-3">
          <Icon name="target" size={20} className="text-emerald-300 shrink-0" />
          <span className="flex-1">{t('waitRow', fmtMonths(w.months_worst, lang))}
            {w.overpayment_avoided > 0 && <span className="text-muted"> · {t('waitSave', uzs(w.overpayment_avoided))}</span>}</span>
        </div>
      )}
    </div>
  )
}

function ShareChip({ p }) {
  const { t } = useApp()
  const cls = p > 40 ? 'bg-rose-500/15 text-rose-200 border-rose-400/30'
    : p > 30 ? 'bg-amber-400/15 text-amber-200 border-amber-400/30'
      : 'bg-emerald-400/15 text-emerald-200 border-emerald-400/30'
  const icon = p > 40 ? '⚠' : p > 30 ? '!' : '✓'
  return <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-semibold ${cls}`}>{icon} {t('shareSalary', p)}</span>
}

function OfferCard({ o, amount, delay }) {
  const { t, lang, notify, refresh } = useApp()
  const [open, setOpen] = useState(false)
  const [confirm, setConfirm] = useState(false)
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(null)
  const best = o.tags.includes('best_cost')

  async function apply() {
    setBusy(true)
    try {
      const r = await api.applyCredit(o.product_id, amount, o.months)
      setDone(r.message)
      notify({ text: r.message, long: true })
      refresh()
    } catch (e) {
      notify({ text: e.message, error: true })
    } finally {
      setBusy(false)
      setConfirm(false)
    }
  }

  return (
    <div className={`rounded-card border p-4 animate-rise ${best ? 'border-emerald-400/50 bg-emerald-400/[0.06] shadow-[0_0_24px_-8px_rgba(52,211,153,.5)]' : 'border-line bg-card2'}`}
      style={{ animationDelay: `${delay}ms` }}>
      <div className="flex flex-wrap gap-1.5 mb-2">
        {o.tags.map((tg) => (
          <span key={tg} className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${tg === 'best_cost' ? 'bg-emerald-400 text-emerald-950' : 'bg-white/10 text-ink/90'}`}>
            {tg === 'best_cost' && '★ '}{t(`tag_${tg}`)}
          </span>
        ))}
      </div>
      <div className="flex items-start justify-between gap-3">
        <h4 className="font-bold leading-snug">{o.name}</h4>
        <span className="shrink-0 text-sm font-semibold text-brand-light">{t('perYear', o.annual_rate)}</span>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
        <div><p className="text-muted text-xs">{t('payMonth')}</p><Money value={o.monthly_payment} className="font-bold text-base" /></div>
        <div><p className="text-muted text-xs">{t('overpay')}</p><Money value={o.total_overpayment} className="font-bold text-base" /></div>
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5">
        <ShareChip p={o.income_share_percent} />
        <span className="rounded-full border border-line bg-white/5 px-2 py-0.5 text-xs">{fmtMonths(o.months, lang)}</span>
        {o.goal_delays.filter((d) => d.delay_months).map((d) => (
          <span key={d.goal_id} className="rounded-full border border-violet-400/30 bg-violet-400/10 text-violet-200 px-2 py-0.5 text-xs font-semibold">
            {t('goalDelay', d.name, d.delay_months)}
          </span>
        ))}
      </div>
      {(o.risk || o.cash_gap) && (
        <p className="mt-2 text-xs text-rose-200">⚠ {o.risk ? t('riskWarn') : t('cashGapWarn')}</p>
      )}

      {open && (
        <div className="mt-3 rounded-[14px] bg-black/20 p-3 text-sm space-y-1.5 animate-rise">
          <Line k={t('term')} v={fmtMonths(o.months, lang)} />
          <Line k={t('interest')} v={uzs(o.interest)} />
          <Line k={t('fee')} v={`${o.fee_percent}% · ${uzs(o.origination_fee)}`} />
          <Line k={t('totalCost')} v={uzs(o.total_cost)} strong />
          <Line k={t('earlyRepay')} v={o.early_repayment_allowed ? t('yes') : t('no')} />
          {o.note && <p className="pt-1 text-muted">{o.note}</p>}
        </div>
      )}

      <div className="mt-3 flex gap-2">
        <button className="btn-ghost !min-h-[42px] flex-1 text-sm" onClick={() => setOpen(!open)}>{open ? t('hideDetails') : t('details')}</button>
        {done
          ? <span className="flex-1 grid place-items-center text-sm text-emerald-300 font-semibold">✓ {t('applied')}</span>
          : <button className="btn-primary !min-h-[42px] flex-1 text-sm !px-3" onClick={() => setConfirm(true)}>{t('applyDemo')}</button>}
      </div>

      <ConfirmSheet open={confirm} onClose={() => setConfirm(false)} busy={busy} title={t('applyTitle', o.name)}
        text={t('applyText', uzs(amount), fmtMonths(o.months, lang), uzs(o.monthly_payment), uzs(o.total_overpayment))}
        confirmLabel={t('applyOk')} onConfirm={apply} />
    </div>
  )
}

function Line({ k, v, strong }) {
  return <div className="flex justify-between gap-3"><span className="text-muted">{k}</span><span className={`num text-right ${strong ? 'font-bold' : ''}`}>{v}</span></div>
}

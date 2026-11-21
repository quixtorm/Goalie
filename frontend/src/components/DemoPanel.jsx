import { useEffect, useState } from 'react'
import { api } from '../api'
import { useApp } from '../ctx'
import { date, digitsOnly, groupDigits, uzs } from '../format'
import { Icon } from './ui'

const MERCHANT = { '7832': 'Magic Cinema', '5912': 'Dori-Darmon', '5812': 'Plov Center', '5814': 'Evos' }

// Presenter-only controls, visually separate from the product UI.
export default function DemoPanel() {
  const { state, t, lang, notify, refresh, openGuardian } = useApp()
  const [salary, setSalary] = useState(6375000)
  const [mccs, setMccs] = useState([])
  const [buy, setBuy] = useState({ source_id: '', mcc: '7832', amount: 150000, merchant: 'Magic Cinema' })
  const [busy, setBusy] = useState(false)

  useEffect(() => { api.mcc().then(setMccs).catch(() => {}) }, [lang])

  const sources = [
    ...state.goals.filter((g) => g.status === 'active').map((g) => ({ id: g.id, label: `#${g.priority} ${g.name}` })),
    ...state.obligations.map((o) => ({ id: o.id, label: `🛡 ${o.name}` })),
  ]
  const valid = sources.some((s) => s.id === buy.source_id)
  const sourceId = valid ? buy.source_id : (sources.find((s) => /Машина|Mashina/.test(s.label))?.id || sources[0]?.id || '')

  async function run(fn, msg) {
    setBusy(true)
    try {
      const r = await fn()
      if (msg) notify(typeof msg === 'function' ? msg(r) : { text: msg })
      refresh()
      return r
    } catch (e) {
      notify({ text: e.message, error: true })
    } finally {
      setBusy(false)
    }
  }

  const salaryMsg = (r) => {
    const lines = [t('salaryDone', uzs(r.main))]
    for (const s of r.shortfalls || []) lines.push(`⚠ ${t('salaryShort', s.name, uzs(s.shortfall))}`)
    return { text: lines.join('\n'), long: (r.shortfalls || []).length > 0 }
  }

  return (
    <section className="rounded-card border-2 border-dashed border-amber-300/40 bg-amber-300/[0.04] p-5 space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="font-bold text-lg flex items-center gap-2">🎬 {t('demo')}</h2>
        <span className="text-xs text-amber-200/80">{t('demoHint')}</span>
      </div>
      <p className="text-sm text-muted">{t('demoDate')}: {date(state.today, lang)}</p>

      <div>
        <label className="label" htmlFor="salary">💰 {t('salary')}</label>
        <div className="flex gap-2 mb-2">
          {[{ l: t('normal'), v: state.income.avg }, { l: '−15%', v: 6375000 }].map((p) => (
            <button key={p.l} className="btn-ghost !min-h-[38px] !px-3 text-sm" onClick={() => setSalary(p.v)}>{p.l}: {groupDigits(p.v)}</button>
          ))}
        </div>
        <div className="flex gap-2">
          <input id="salary" className="input num" inputMode="numeric" value={groupDigits(salary)}
            onChange={(e) => setSalary(digitsOnly(e.target.value))} />
          <button className="btn-primary shrink-0" disabled={busy || !salary} onClick={() => run(() => api.salary(salary), salaryMsg)}>
            {t('credit')}
          </button>
        </div>
      </div>

      <button className="btn-ghost w-full" disabled={busy} onClick={() => run(() => api.skip(24), t('skipped'))}>
        <Icon name="clock" size={20} /> {t('skip')}
      </button>

      <div className="space-y-2">
        <p className="label">🛒 {t('purchase')}</p>
        <select className="input" value={sourceId} onChange={(e) => setBuy({ ...buy, source_id: e.target.value })} aria-label="source">
          {sources.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
        </select>
        <select className="input" value={buy.mcc} aria-label="MCC"
          onChange={(e) => setBuy({ ...buy, mcc: e.target.value, merchant: MERCHANT[e.target.value] || 'Shop' })}>
          {mccs.map((m) => <option key={m.mcc} value={m.mcc}>{m.label} ({m.mcc})</option>)}
          <option value="1234">{t('unknownShop')} (1234)</option>
        </select>
        <input className="input num" inputMode="numeric" aria-label="amount" value={groupDigits(buy.amount)}
          onChange={(e) => setBuy({ ...buy, amount: digitsOnly(e.target.value) })} />
        <button className="btn-primary w-full" disabled={busy || !sourceId || !buy.amount}
          onClick={async () => {
            const r = await run(() => api.spend({ ...buy, source_id: sourceId }))
            if (r) openGuardian(r)
          }}>{t('payCard')}</button>
      </div>

      <button className="btn-link w-full !text-rose-300" disabled={busy} onClick={() => run(() => api.reset(), t('resetDone'))}>
        ↺ {t('reset')}
      </button>
    </section>
  )
}

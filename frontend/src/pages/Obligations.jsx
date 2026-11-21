import { useState } from 'react'
import { api } from '../api'
import { useApp } from '../ctx'
import { date, digitsOnly, dueText, groupDigits, uzs } from '../format'
import { StatusChip } from './Home'
import { ConfirmSheet, Icon, Money, Progress, Sheet } from '../components/ui'

export default function Obligations() {
  const { state, t, lang, notify, refresh } = useApp()
  const [pay, setPay] = useState(null)
  const [adding, setAdding] = useState(false)
  const [form, setForm] = useState({ name: '', amount: 0, due_date: '' })
  const [busy, setBusy] = useState(false)

  async function run(fn, msg, after) {
    setBusy(true)
    try {
      await fn()
      notify({ text: msg })
      after?.()
      refresh()
    } catch (e) {
      notify({ text: e.message, error: true })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-5 pt-4">
      <div className="px-1">
        <h1 className="text-2xl font-bold flex items-center gap-2"><Icon name="shield" /> {t('obligations')}</h1>
        <p className="text-muted mt-1">{t('oblIntro')}</p>
      </div>

      {state.obligations.length === 0 && <div className="card text-center text-muted">{t('noObl')}</div>}

      {state.obligations.map((o, i) => {
        const pct = Math.round((o.reserved * 100) / o.amount)
        return (
          <section key={o.id} className="card animate-rise" style={{ animationDelay: `${i * 50}ms` }}>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h2 className="font-bold text-lg truncate">{o.name}</h2>
                <p className="text-muted">{date(o.due_date, lang, false)} · {dueText(o.due_in_days, lang)}</p>
              </div>
              <StatusChip status={o.status} shortfall={o.shortfall} />
            </div>
            <Money value={o.amount} className="block text-3xl font-bold mt-3" />
            <Progress className="mt-3" value={pct} tone={o.shortfall ? 'amber' : 'green'} />
            <p className="mt-2 text-muted">
              {t('reserved')} <Money value={o.reserved} />
              {o.shortfall > 0 && <> · {t('missing')} <b className="text-amber-300"><Money value={o.shortfall} /></b></>}
            </p>
            <button className="btn-primary w-full mt-4" onClick={() => setPay(o)}>{t('pay')}</button>
          </section>
        )
      })}

      <button className="btn-ghost w-full" onClick={() => setAdding(true)}><Icon name="plus" /> {t('addPayment')}</button>

      <ConfirmSheet open={!!pay} onClose={() => setPay(null)} busy={busy} title={pay ? t('payTitle', pay.name) : ''}
        text={pay ? t('payText', uzs(pay.amount)) + (pay.shortfall > 0 ? `\n${t('payFromMain', uzs(pay.shortfall))}` : '') : ''}
        confirmLabel={t('payOk')} onConfirm={() => run(() => api.payObligation(pay.id), t('paid'), () => setPay(null))} />

      <Sheet open={adding} onClose={() => setAdding(false)} label={t('addPayment')}>
        <div className="px-6 pb-8 space-y-4 overflow-y-auto">
          <h2 className="text-xl font-bold">{t('addPayment')}</h2>
          <div>
            <label className="label" htmlFor="oname">{t('oblName')}</label>
            <input id="oname" className="input" maxLength={100} placeholder={t('oblNamePh')} value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="oamount">{t('oblAmount')}</label>
            <input id="oamount" className="input num" inputMode="numeric" placeholder="1 500 000" value={groupDigits(form.amount)}
              onChange={(e) => setForm({ ...form, amount: digitsOnly(e.target.value) })} />
          </div>
          <div>
            <label className="label" htmlFor="odate">{t('oblDate')}</label>
            <input id="odate" type="date" className="input [color-scheme:dark]" min={state.today} value={form.due_date}
              onChange={(e) => setForm({ ...form, due_date: e.target.value })} />
          </div>
          <button className="btn-primary w-full" disabled={busy || !form.name.trim() || !form.amount || !form.due_date}
            onClick={() => run(() => api.createObligation({ ...form, name: form.name.trim() }), t('added'), () => {
              setAdding(false); setForm({ name: '', amount: 0, due_date: '' })
            })}>{t('add')}</button>
        </div>
      </Sheet>
    </div>
  )
}

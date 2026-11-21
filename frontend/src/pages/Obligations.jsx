import { useState } from 'react'
import { api } from '../api'
import { date, digitsOnly, dueText, groupDigits, uzs } from '../format'
import { Chip, ConfirmModal, Modal, Progress } from '../components/ui'

const STATUS = {
  ok: { tone: 'green', icon: '✓', text: 'Хватает' },
  soon: { tone: 'blue', icon: '…', text: 'Копится' },
  shortfall: { tone: 'amber', icon: '⚠', text: 'Не хватает' },
  overdue: { tone: 'red', icon: '!', text: 'Просрочено' },
}

export default function Obligations({ state, onChanged, notify }) {
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
      onChanged()
    } catch (e) {
      notify({ text: e.message, error: true })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-5">
      <div className="px-1">
        <h1 className="text-2xl font-bold">🛡 Обязательные платежи</h1>
        <p className="text-slate-600 mt-1">Деньги на них откладываются первыми, с каждой зарплаты.</p>
      </div>

      {state.obligations.length === 0 && <div className="card text-center text-slate-600">Платежей нет. Можно добавить аренду или кредит.</div>}

      {state.obligations.map((o) => {
        const st = STATUS[o.status] || STATUS.ok
        const pct = Math.round((o.reserved * 100) / o.amount)
        return (
          <section key={o.id} className="card">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h2 className="font-bold text-lg truncate">{o.name}</h2>
                <p className="text-slate-600">{date(o.due_date, false)} · {dueText(o.due_in_days)}</p>
              </div>
              <Chip tone={st.tone} icon={st.icon}>{st.text}</Chip>
            </div>
            <p className="num text-3xl font-bold mt-3">{uzs(o.amount)}</p>
            <div className="mt-3"><Progress value={pct} tone={o.shortfall ? 'amber' : 'green'} /></div>
            <p className="mt-2 text-slate-600 num">
              Отложено {uzs(o.reserved)}{o.shortfall > 0 && <> · не хватает <b className="text-amber-800">{uzs(o.shortfall)}</b></>}
            </p>
            <button className="btn-primary w-full mt-4" onClick={() => setPay(o)}>Оплатить</button>
          </section>
        )
      })}

      <button className="btn-soft w-full" onClick={() => setAdding(true)}>＋ Добавить платёж</button>

      <ConfirmModal open={!!pay} onClose={() => setPay(null)} busy={busy} title={pay ? `Оплатить «${pay.name}»?` : ''}
        text={pay ? `Будет оплачено ${uzs(pay.amount)}.` + (pay.shortfall > 0 ? `\n${uzs(pay.shortfall)} возьмём с основной карты.` : '') : ''}
        confirmLabel="Да, оплатить" onConfirm={() => run(() => api.payObligation(pay.id), 'Оплачено', () => setPay(null))} />

      <Modal open={adding} onClose={() => setAdding(false)} title="Новый платёж">
        <div className="space-y-4">
          <div>
            <label className="label" htmlFor="oname">Что платим</label>
            <input id="oname" className="input" maxLength={100} placeholder="Например, долг брату" value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div>
            <label className="label" htmlFor="oamount">Сумма, so'm</label>
            <input id="oamount" className="input num" inputMode="numeric" placeholder="1 500 000" value={groupDigits(form.amount)}
              onChange={(e) => setForm({ ...form, amount: digitsOnly(e.target.value) })} />
          </div>
          <div>
            <label className="label" htmlFor="odate">До какого числа</label>
            <input id="odate" type="date" className="input" min={state.today} value={form.due_date}
              onChange={(e) => setForm({ ...form, due_date: e.target.value })} />
          </div>
          <button className="btn-primary w-full" disabled={busy || !form.name.trim() || !form.amount || !form.due_date}
            onClick={() => run(() => api.createObligation({ ...form, name: form.name.trim() }), 'Платёж добавлен', () => {
              setAdding(false); setForm({ name: '', amount: 0, due_date: '' })
            })}>Добавить</button>
        </div>
      </Modal>
    </div>
  )
}

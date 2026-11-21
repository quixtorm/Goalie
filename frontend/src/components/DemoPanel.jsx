import { useEffect, useState } from 'react'
import { api } from '../api'
import { digitsOnly, groupDigits, uzs } from '../format'

// Hidden by default: for the presenter only.
export default function DemoPanel({ state, onChanged, onSpend, notify }) {
  const [open, setOpen] = useState(false)
  const [salary, setSalary] = useState(6375000)
  const [mccs, setMccs] = useState([])
  const [buy, setBuy] = useState({ source_id: '', mcc: '7832', amount: 150000, merchant: 'Magic Cinema' })
  const [busy, setBusy] = useState(false)

  useEffect(() => { if (open && !mccs.length) api.mcc().then(setMccs).catch(() => {}) }, [open, mccs.length])

  const sources = [
    ...state.goals.filter((g) => g.status === 'active').map((g) => ({ id: g.id, label: `🎯 ${g.name}` })),
    ...state.obligations.map((o) => ({ id: o.id, label: `🛡 ${o.name}` })),
  ]
  const sourceId = buy.source_id || sources.find((s) => s.label.includes('Машина'))?.id || sources[0]?.id || ''

  async function run(fn, msg) {
    setBusy(true)
    try {
      const r = await fn()
      if (msg) notify({ text: typeof msg === 'function' ? msg(r) : msg })
      onChanged()
      return r
    } catch (e) {
      notify({ text: e.message, error: true })
    } finally {
      setBusy(false)
    }
  }

  const presets = [
    { label: 'Обычная', v: state.income.avg },
    { label: '−15%', v: 6375000 },
  ]

  const merchantFor = (code) => ({ '7832': 'Magic Cinema', '5912': 'Dori-Darmon', '5812': 'Ресторан Plov', '5814': 'Evos' }[code] || 'Магазин')

  return (
    <div className="mt-8 mb-4 rounded-3xl border-2 border-dashed border-slate-300 bg-slate-50">
      <button className="w-full flex items-center justify-between px-5 min-h-[52px] font-semibold text-slate-600"
        onClick={() => setOpen(!open)} aria-expanded={open}>
        <span>🎬 Управление демо</span><span aria-hidden>{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="px-5 pb-5 space-y-5">
          <p className="text-sm text-slate-500">Дата в демо: {state.today} · Агент: {state.agent_source || '—'}</p>

          <section>
            <label className="label" htmlFor="salary">💰 Пришла зарплата</label>
            <div className="flex gap-2 mb-2">
              {presets.map((p) => (
                <button key={p.label} className="btn-soft !min-h-[40px] !px-3 text-sm" onClick={() => setSalary(p.v)}>
                  {p.label}: {groupDigits(p.v)}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <input id="salary" className="input num" inputMode="numeric" value={groupDigits(salary)}
                onChange={(e) => setSalary(digitsOnly(e.target.value))} />
              <button className="btn-primary shrink-0" disabled={busy || !salary}
                onClick={() => run(() => api.salary(salary), (r) => `Зарплата распределена: на жизнь ${uzs(r.main)}`)}>
                Зачислить
              </button>
            </div>
          </section>

          <section>
            <p className="label">⏩ Время</p>
            <button className="btn-soft w-full" disabled={busy} onClick={() => run(() => api.skip(24), 'Прошли сутки')}>
              Перемотать на 24 часа
            </button>
          </section>

          <section className="space-y-2">
            <p className="label">🛒 Покупка из цели или резерва</p>
            <select className="input" value={sourceId} onChange={(e) => setBuy({ ...buy, source_id: e.target.value })} aria-label="Откуда">
              {sources.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
            </select>
            <select className="input" value={buy.mcc} aria-label="Тип покупки"
              onChange={(e) => setBuy({ ...buy, mcc: e.target.value, merchant: merchantFor(e.target.value) })}>
              {mccs.map((m) => <option key={m.mcc} value={m.mcc}>{m.label} ({m.mcc})</option>)}
              <option value="1234">Неизвестный магазин (1234)</option>
            </select>
            <input className="input num" inputMode="numeric" aria-label="Сумма" value={groupDigits(buy.amount)}
              onChange={(e) => setBuy({ ...buy, amount: digitsOnly(e.target.value) })} />
            <button className="btn-primary w-full" disabled={busy || !sourceId || !buy.amount}
              onClick={async () => {
                const r = await run(() => api.spend({ ...buy, source_id: sourceId }))
                if (r) onSpend(r)
              }}>
              Оплатить картой
            </button>
          </section>

          <button className="btn-link w-full justify-center text-rose-700" disabled={busy}
            onClick={() => run(() => api.reset(), 'Демо сброшено')}>↺ Сбросить демо</button>
        </div>
      )}
    </div>
  )
}

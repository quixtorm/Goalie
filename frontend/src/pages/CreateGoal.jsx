import { useEffect, useState } from 'react'
import { api } from '../api'
import { date, digitsOnly, groupDigits, months, uzs } from '../format'
import { ConfirmModal, Row } from '../components/ui'

const LOCK = 'Деньги в этой подкарте защищены от импульсных трат. Экстренные расходы (аптека, больница) проходят без штрафа, остальные — с остановкой, задержкой 24 часа и потерей бонуса за дисциплину.'

export default function CreateGoal({ state, go, onChanged, notify, askAgent }) {
  const cap = state.limits.max_total_percent - state.used_percent
  const [name, setName] = useState('')
  const [amount, setAmount] = useState(0)
  const [percent, setPercent] = useState(Math.min(10, Math.max(1, cap)))
  const [pv, setPv] = useState(null)
  const [err, setErr] = useState(null)
  const [confirm, setConfirm] = useState(false)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!amount || cap < 1) { setPv(null); return }
    const t = setTimeout(() => {
      api.preview(amount, percent).then((r) => { setPv(r); setErr(null) }).catch((e) => { setPv(null); setErr(e.message) })
    }, 250)
    return () => clearTimeout(t)
  }, [amount, percent, cap])

  if (cap < 1) {
    return (
      <div className="space-y-4">
        <button className="btn-link -ml-2" onClick={() => go('home')}>← Назад</button>
        <div className="card text-center">Уже {state.used_percent}% дохода идёт на цели — это максимум. Сначала завершите одну из целей.</div>
      </div>
    )
  }

  async function create() {
    setBusy(true)
    try {
      await api.createGoal({ name: name.trim(), amount, percent })
      notify({ text: `Цель «${name.trim()}» создана` })
      onChanged()
      go('home')
    } catch (e) {
      notify({ text: e.message, error: true })
    } finally {
      setBusy(false)
      setConfirm(false)
    }
  }

  const valid = name.trim() && amount > 0 && pv

  return (
    <div className="space-y-5">
      <button className="btn-link -ml-2" onClick={() => go('home')}>← Назад</button>
      <h1 className="text-2xl font-bold">Новая цель</h1>

      <section className="card space-y-4">
        <div>
          <label className="label" htmlFor="gname">На что копим?</label>
          <input id="gname" className="input" maxLength={100} placeholder="Например, машина" value={name}
            onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <label className="label" htmlFor="gamount">Сколько нужно, so'm</label>
          <input id="gamount" className="input num" inputMode="numeric" placeholder="50 000 000"
            value={groupDigits(amount)} onChange={(e) => setAmount(digitsOnly(e.target.value))} />
        </div>
        <div>
          <label className="label" htmlFor="gpct">Сколько откладывать с каждой зарплаты: <b className="text-slate-900">{percent}%</b></label>
          <input id="gpct" type="range" min={1} max={cap} value={percent} className="w-full h-11 accent-blue-600"
            onChange={(e) => setPercent(Number(e.target.value))} />
          <div className="flex justify-between text-sm text-slate-500"><span>1%</span><span>{cap}% (максимум)</span></div>
        </div>
      </section>

      {pv && (
        <section className="card">
          <h2 className="font-bold text-lg mb-1">Прогноз</h2>
          <Row label="В месяц" value={`≈ ${uzs(pv.contribution_worst)}`} />
          <Row label="Если доход как обычно" value={`≈ ${months(pv.months_best)}`} />
          <Row label="Если доход самый низкий" value={`≈ ${months(pv.months_worst)}`} />
          <Row label="Срок цели" value={`до ${date(pv.expiry)}`} strong />
        </section>
      )}
      {err && <p className="text-rose-700">⚠ {err}</p>}

      <button className="btn-primary w-full !min-h-[56px] text-lg" disabled={!valid} onClick={() => setConfirm(true)}>Создать цель</button>
      <button className="btn-link w-full justify-center" onClick={() => askAgent(
        amount ? `Хочу накопить ${amount} на ${name || 'цель'}. Сколько процентов откладывать?` : 'Помоги выбрать процент для новой цели')}>
        🤖 Спросить помощника
      </button>

      <ConfirmModal open={confirm} onClose={() => setConfirm(false)} busy={busy}
        title={`Создать «${name.trim()}»?`}
        text={`Будем откладывать ${percent}% с каждой зарплаты.\n\n🔒 ${LOCK}`}
        confirmLabel="Понятно, создать" onConfirm={create} />
    </div>
  )
}

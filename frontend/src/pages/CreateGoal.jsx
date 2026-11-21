import { useEffect, useState } from 'react'
import { api } from '../api'
import { useApp } from '../ctx'
import { date, digitsOnly, groupDigits, months, uzs } from '../format'
import BankCard from '../components/BankCard'
import { BackButton, ConfirmSheet, Icon, Money, Row, SalaryOnlyNote } from '../components/ui'

export default function CreateGoal() {
  const { state, t, lang, go, notify, refresh, openAgent } = useApp()
  const cap = state.limits.max_total_percent - state.used_percent
  const [name, setName] = useState('')
  const [amount, setAmount] = useState(0)
  const [percent, setPercent] = useState(Math.min(10, Math.max(1, cap)))
  const [pv, setPv] = useState(null)
  const [err, setErr] = useState(null)
  const [confirm, setConfirm] = useState(false)
  const [busy, setBusy] = useState(false)
  const [issued, setIssued] = useState(null)

  useEffect(() => {
    if (!amount || cap < 1) { setPv(null); return }
    const tm = setTimeout(() => {
      api.preview(amount, percent).then((r) => { setPv(r); setErr(null) }).catch((e) => { setPv(null); setErr(e.message) })
    }, 250)
    return () => clearTimeout(tm)
  }, [amount, percent, cap])

  const ask = () => openAgent({
    send: amount ? t('askAgentGoal', uzs(amount), name.trim() || t('newGoal').toLowerCase()) : t('askAgentEmpty'),
  })

  if (issued) {
    return (
      <div className="pt-16 text-center">
        <div className="animate-card-issue"><BankCard goal={issued} tilt={false} /></div>
        <p className="mt-8 text-2xl font-bold animate-rise" style={{ animationDelay: '600ms' }}>✨ {t('issued')}</p>
      </div>
    )
  }

  if (cap < 1 || state.goals.filter((g) => g.status === 'active').length >= state.limits.max_goals) {
    return (
      <div className="space-y-4 pt-4">
        <BackButton onClick={() => go('goals')} />
        <div className="card text-center text-muted">{t('maxGoals', state.used_percent)}</div>
      </div>
    )
  }

  async function create() {
    setBusy(true)
    try {
      const g = await api.createGoal({ name: name.trim(), amount, percent })
      setConfirm(false)
      setIssued(g) // card-issue animation, then go to the goals list
      refresh()
      setTimeout(() => { notify({ text: t('issued') }); go('goal', { id: g.id }) }, 1500)
    } catch (e) {
      notify({ text: e.message, error: true })
      setConfirm(false)
    } finally {
      setBusy(false)
    }
  }

  const valid = name.trim() && amount > 0 && pv
  // live card preview: the card being "issued" while the user types
  const preview = {
    name: name.trim(), saved: 0, amount, percent, progress: 0, status: 'active',
    priority: state.goals.filter((x) => x.status === 'active').length + 1, expiry: pv?.expiry,
  }

  return (
    <div className="space-y-5 pt-4">
      <BackButton onClick={() => go('goals')} />
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">{t('newGoal')}</h1>
        <button className="press inline-flex items-center gap-1.5 rounded-full bg-amber-300/15 text-amber-200 border border-amber-300/30 px-4 min-h-[44px] font-semibold"
          onClick={ask}>
          <Icon name="sparkle" size={18} fill strokeWidth={0} /> {t('askAgent')}
        </button>
      </div>

      <section aria-label={t('yourCard')}>
        <BankCard goal={preview} tilt={false} />
      </section>

      <section className="card space-y-4">
        <div>
          <label className="label" htmlFor="gname">{t('whatFor')}</label>
          <input id="gname" className="input" maxLength={100} placeholder={t('whatForPh')} value={name}
            onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <label className="label" htmlFor="gamount">{t('howMuch')}</label>
          <input id="gamount" className="input num" inputMode="numeric" placeholder="50 000 000"
            value={groupDigits(amount)} onChange={(e) => setAmount(digitsOnly(e.target.value))} />
        </div>
        <div>
          <label className="label" htmlFor="gpct">{t('howPct')}: <b className="text-ink text-base">{percent}%</b></label>
          <input id="gpct" type="range" min={1} max={cap} value={percent} className="w-full h-11 accent-[#2E7BD6]"
            onChange={(e) => setPercent(Number(e.target.value))} />
          <div className="flex justify-between text-sm text-muted"><span>1%</span><span>{cap}% ({t('max')})</span></div>
        </div>
      </section>

      {pv && (
        <section className="card !py-2 animate-rise">
          <h2 className="font-bold pt-2">{t('forecast')}</h2>
          <Row label={t('perMonth')}>≈ <Money value={pv.contribution_worst} /></Row>
          <Row label={t('bestCase')}>≈ {months(pv.months_best, lang)}</Row>
          <Row label={t('worstCase')}>≈ {months(pv.months_worst, lang)}</Row>
          <Row label={t('deadline')} strong>{t('until', date(pv.expiry, lang))}</Row>
          <div className="pb-3"><SalaryOnlyNote worstAnnual={state.income.worst_annual} /></div>
        </section>
      )}
      {!pv && <SalaryOnlyNote worstAnnual={state.income.worst_annual} />}
      {err && <p className="text-rose-300">⚠ {err}</p>}

      <button className="btn-primary w-full !min-h-[56px] text-lg" disabled={!valid} onClick={() => setConfirm(true)}>{t('create')}</button>

      <ConfirmSheet open={confirm} onClose={() => setConfirm(false)} busy={busy}
        title={t('createTitle', name.trim())}
        text={`${t('createText', percent)}\n\n🔒 ${t('lockFull')}`}
        confirmLabel={t('createOk')} onConfirm={create} />
    </div>
  )
}

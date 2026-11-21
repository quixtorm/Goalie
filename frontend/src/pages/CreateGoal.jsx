import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { useApp } from '../ctx'
import { date, digitsOnly, groupDigits } from '../format'
import BankCard from '../components/BankCard'
import { BackButton, ConfirmSheet, Icon, Money, SalaryOnlyNote } from '../components/ui'

// The user enters ONLY a name and an amount (optional term). The agent chooses the percent of salary on the
// server (/subcards/plan); it is shown read-only. There is no percent control anywhere.
const TERMS = [null, 12, 24, 36, 60]

export default function CreateGoal() {
  const { state, t, lang, go, notify, refresh } = useApp()
  const [name, setName] = useState('')
  const [amount, setAmount] = useState(0)
  const [term, setTerm] = useState(null) // null = "Агент подберёт"
  const [plan, setPlan] = useState(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState(null)
  const [confirm, setConfirm] = useState(false)
  const [busy, setBusy] = useState(false)
  const [issued, setIssued] = useState(null)
  const reqId = useRef(0)

  const ready = name.trim().length > 0 && amount > 0

  // auto-plan: 400 ms after name/amount/term change, ask the agent
  useEffect(() => {
    if (!ready) { setPlan(null); setErr(null); setLoading(false); return }
    setLoading(true)
    const id = ++reqId.current
    const tm = setTimeout(() => {
      api.planGoal(name.trim(), amount, term)
        .then((p) => { if (id === reqId.current) { setPlan(p); setErr(null) } })
        .catch((e) => { if (id === reqId.current) { setPlan(null); setErr(e.message) } })
        .finally(() => { if (id === reqId.current) setLoading(false) })
    }, 400)
    return () => clearTimeout(tm)
  }, [name, amount, term, ready, lang])

  if (issued) {
    return (
      <div className="pt-16 text-center">
        <div className="animate-card-issue"><BankCard goal={issued} tilt={false} /></div>
        <p className="mt-8 text-2xl font-bold animate-rise" style={{ animationDelay: '600ms' }}>✨ {t('issued')}</p>
      </div>
    )
  }

  if (state.goals.filter((g) => g.status === 'active').length >= state.limits.max_goals
      || state.used_percent >= state.limits.max_total_percent) {
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
      const g = await api.createGoal(name.trim(), amount, term) // no percent: the server recomputes it
      setConfirm(false)
      setIssued(g)
      refresh()
      setTimeout(() => { notify({ text: t('issued') }); go('goal', { id: g.id }) }, 1500)
    } catch (e) {
      notify({ text: e.message, error: true })
      setConfirm(false)
    } finally {
      setBusy(false)
    }
  }

  // live card preview: name, amount, agent percent and deadline
  const preview = {
    name: name.trim(), saved: 0, amount, percent: plan?.percent ?? 0, progress: 0, status: 'active',
    priority: state.goals.filter((x) => x.status === 'active').length + 1, expiry: plan?.expiry,
  }
  const termLabel = (m) => (m ? t('termN', m) : t('termAuto'))

  return (
    <div className="space-y-5 pt-4 pb-28">
      <BackButton onClick={() => go('goals')} />
      <h1 className="text-2xl font-bold">{t('newGoal')}</h1>

      <section aria-label={t('yourCard')}><BankCard goal={preview} tilt={false} /></section>

      {/* agent panel: read-only result */}
      <section className="card !p-4" aria-live="polite">
        <div className="flex items-center gap-2 mb-2">
          <span className="w-8 h-8 rounded-full bg-gradient-to-br from-amber-300 to-brand grid place-items-center text-white">
            <Icon name="sparkle" size={16} fill strokeWidth={0} />
          </span>
          <span className="font-bold">{t('agentPlan')}</span>
        </div>
        {!ready && <p className="text-muted text-sm">{t('agentWaiting')}</p>}
        {ready && loading && (
          <p className="text-muted flex items-center gap-2" role="status">
            <span className="flex gap-1">{[0, 1, 2].map((d) => <span key={d} className="w-2 h-2 rounded-full bg-muted animate-pulse" style={{ animationDelay: `${d * 150}ms` }} />)}</span>
            {t('agentCalc')}
          </p>
        )}
        {ready && !loading && err && <p className="text-rose-300">⚠ {err}</p>}
        {ready && !loading && plan && (
          <div className="animate-rise">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-3xl font-extrabold num">{t('pctOfSalary', plan.percent)}</span>
              <span className="rounded-full border border-amber-300/40 bg-amber-300/15 text-amber-200 text-xs font-semibold px-2.5 py-1">
                ✦ {t('pickedByAgent')}
              </span>
            </div>
            <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2 text-sm">
              <dt className="text-muted">{t('monthlyWorst')}</dt><dd className="text-right font-semibold"><Money value={plan.contribution_worst} /></dd>
              <dt className="text-muted">{t('expiryWorst')}</dt><dd className="text-right font-semibold">{t('until', date(plan.expiry, lang))}</dd>
              <dt className="text-muted">{t('bestCase')}</dt><dd className="text-right">{t('until', date(plan.best_date, lang))}</dd>
            </dl>
            <p className="mt-3 text-ink/90">{plan.explanation}</p>
            <SalaryOnlyNote worstAnnual={state.income.worst_annual} />
          </div>
        )}
      </section>

      {/* inputs: name, amount, optional term. NO percent. */}
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
          <p className="label">{t('termLabel')}</p>
          <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={t('termLabel')}>
            {TERMS.map((m) => (
              <button key={m ?? 'auto'} role="radio" aria-checked={term === m} onClick={() => setTerm(m)}
                className={`press rounded-full px-4 min-h-[40px] text-sm font-semibold border ${term === m ? 'bg-brand text-white border-brand' : 'bg-card2 text-ink/90 border-line'}`}>
                {m === null && '✦ '}{termLabel(m)}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* sticky create button (the tab bar is hidden on this screen) */}
      <div className="fixed bottom-0 left-1/2 -translate-x-1/2 z-40 w-full max-w-[420px] px-4 pt-3 pb-[max(16px,env(safe-area-inset-bottom))] bg-gradient-to-t from-bg via-bg/95 to-transparent">
        <button className="btn-primary w-full !min-h-[56px] text-lg" disabled={!plan || loading} onClick={() => setConfirm(true)}>
          {t('create')}
        </button>
      </div>

      <ConfirmSheet open={confirm} onClose={() => setConfirm(false)} busy={busy}
        title={t('createTitle', name.trim())}
        text={plan ? `${t('createText', plan.percent, t('until', date(plan.expiry, lang)))}\n\n🔒 ${t('lockFull')}` : ''}
        confirmLabel={t('createOk')} onConfirm={create} />
    </div>
  )
}

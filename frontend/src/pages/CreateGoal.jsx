import { useEffect, useState } from 'react'
import { api } from '../api'
import { useApp } from '../ctx'
import { date, digitsOnly, groupDigits, months, uzs } from '../format'
import { BackButton, ConfirmSheet, Icon, Money, Row } from '../components/ui'

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
      await api.createGoal({ name: name.trim(), amount, percent })
      notify({ text: `${t('done')}: «${name.trim()}»` })
      refresh()
      go('goals')
    } catch (e) {
      notify({ text: e.message, error: true })
    } finally {
      setBusy(false)
      setConfirm(false)
    }
  }

  const valid = name.trim() && amount > 0 && pv

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
        </section>
      )}
      {err && <p className="text-rose-300">⚠ {err}</p>}

      <button className="btn-primary w-full !min-h-[56px] text-lg" disabled={!valid} onClick={() => setConfirm(true)}>{t('create')}</button>

      <ConfirmSheet open={confirm} onClose={() => setConfirm(false)} busy={busy}
        title={t('createTitle', name.trim())}
        text={`${t('createText', percent)}\n\n🔒 ${t('lockFull')}`}
        confirmLabel={t('createOk')} onConfirm={create} />
    </div>
  )
}

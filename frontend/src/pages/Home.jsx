import { useApp } from '../ctx'
import { date, dueText } from '../format'
import SubcardStack from '../components/SubcardStack'
import ProposalCard from '../components/ProposalCard'
import { Chip, Icon, Money, Progress } from '../components/ui'

export default function Home() {
  const { state, t, lang, hidden, setHidden, go, openAgent } = useApp()
  const m = state.main
  const next = state.obligations[0]
  const advice = state.proposals_pending.find((p) => p.origin === 'agent')
  const ts = state.today_summary

  const actions = [
    { icon: 'plus', label: t('qaNewGoal'), onClick: () => go('create') },
    { icon: 'shield', label: t('qaObl'), onClick: () => go('payments') },
    { icon: 'pay', label: t('qaPay'), onClick: () => go('payments') },
    { icon: 'calc', label: t('qaCredit'), onClick: () => openAgent({ send: t('creditPrompt') }) },
  ]

  return (
    <div>
      {/* gradient continues from the header into the body */}
      <section className="-mx-4 px-4 pt-2 pb-6 bg-gradient-to-b from-brand to-bg">
        <div className="flex items-center gap-2 text-white/85">
          <span>{t('totalBalance')}</span>
          <button className="press w-9 h-9 grid place-items-center rounded-full hover:bg-white/10" onClick={() => setHidden(!hidden)}
            aria-label={hidden ? t('show') : t('hide')}>
            <Icon name={hidden ? 'eyeOff' : 'eye'} size={20} />
          </button>
        </div>
        <div className="flex items-center gap-3 mb-5">
          <Money value={state.total_balance} className="text-[32px] font-extrabold tracking-tight text-white" />
          <span className="rounded-full bg-white/15 px-3 py-1 text-sm font-semibold text-white">UZS</span>
        </div>

        <SubcardStack goals={state.goals} max={state.limits.max_goals} />

        {/* main card */}
        <div className="relative rounded-[22px] p-5 text-white shadow-glow bg-gradient-to-br from-[#1F5FC0] via-[#174A9A] to-[#0B2A6F] overflow-hidden">
          <div className="absolute -right-10 -top-12 w-48 h-48 rounded-full bg-white/10" aria-hidden />
          <div className="absolute -right-4 top-16 w-32 h-32 rounded-full bg-white/5" aria-hidden />
          <div className="relative flex justify-between items-start">
            <span className="font-extrabold tracking-wide">SmartGoal</span>
            <span className="w-10 h-7 rounded-md bg-gradient-to-br from-amber-200 to-amber-400 opacity-90" aria-hidden />
          </div>
          <p className="relative mt-5 text-white/75 text-sm">{t('mainCardLabel')}</p>
          <Money value={m.main_balance} className="relative block text-3xl font-bold mt-1" />
          <div className="relative mt-4 flex justify-between items-end">
            <div>
              <p className="text-white/70 text-xs">{t('freeToSpend')}</p>
              <Money value={Math.max(0, m.free_to_spend)} className="font-semibold" />
            </div>
            <span className="num tracking-widest text-white/80">•••• 4521</span>
          </div>
          {m.cash_gap && <p className="relative mt-3 text-amber-200 text-sm">⚠ {t('cashGap')}</p>}
        </div>
      </section>

      <div className="space-y-7">
        {/* quick actions */}
        <section>
          <h2 className="h-section">{t('quick')}</h2>
          <div className="grid grid-cols-4 gap-2">
            {actions.map((a) => (
              <button key={a.label} onClick={a.onClick} className="press flex flex-col items-center gap-2 text-center">
                <span className="w-16 h-16 rounded-full bg-card2 border border-line grid place-items-center text-ink hover:bg-white/10">
                  <Icon name={a.icon} size={26} />
                </span>
                <span className="text-[13px] leading-tight text-ink/90">{a.label}</span>
              </button>
            ))}
          </div>
        </section>

        {/* today */}
        <section>
          <h2 className="h-section">{t('today')}</h2>
          <div className="grid grid-cols-2 gap-3">
            <div className="card !p-4">
              <p className="text-muted text-sm">{t('spent')}</p>
              <p className="text-rose-300 font-semibold mt-1">− <Money value={ts.spent} /></p>
              <Progress className="mt-3" tone="amber" value={Math.round((ts.spent * 100) / ts.daily_baseline)} />
            </div>
            <div className="card !p-4">
              <p className="text-muted text-sm">{t('income')}</p>
              <p className="text-emerald-300 font-semibold mt-1">+ <Money value={ts.income} /></p>
              <Progress className="mt-3" tone="green" value={ts.income > 0 ? 100 : 0} />
            </div>
          </div>
        </section>

        {/* AI advisor */}
        <section>
          <h2 className="h-section flex items-center gap-2"><Icon name="sparkle" fill strokeWidth={0} className="text-amber-300" />{t('aiAdvisor')}</h2>
          {advice ? <ProposalCard key={advice.id} p={advice} compact /> : (
            <div className="card flex items-center gap-4">
              <span className="w-12 h-12 shrink-0 rounded-full bg-emerald-400/15 text-emerald-300 grid place-items-center"><Icon name="check" /></span>
              <div>
                <p className="font-bold">{t('allGood')}</p>
                <p className="text-muted text-sm">{t('allGoodSub')}</p>
              </div>
            </div>
          )}
        </section>

        {/* obligations strip */}
        {next && (
          <section>
            <h2 className="h-section">{t('obligations')}</h2>
            <button onClick={() => go('payments')} className="press w-full card text-left">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-bold truncate">{next.name}</p>
                  <p className="text-muted text-sm">{date(next.due_date, lang, false)} · {dueText(next.due_in_days, lang)}</p>
                </div>
                <StatusChip status={next.status} shortfall={next.shortfall} />
              </div>
              <Progress className="mt-3" tone={next.shortfall ? 'amber' : 'green'} value={Math.round((next.reserved * 100) / next.amount)} />
              <p className="mt-2 text-sm text-muted">{t('reserved')} <Money value={next.reserved} /> / <Money value={next.amount} /></p>
            </button>
          </section>
        )}

        {/* banner */}
        <section className="relative overflow-hidden rounded-card p-5 bg-gradient-to-r from-[#E9D3A8] via-[#D9B77A] to-[#B88A45] text-[#2A1C05]">
          <div className="absolute -right-6 -bottom-10 w-40 h-40 rounded-full bg-white/25" aria-hidden />
          <div className="absolute right-6 top-4 text-5xl" aria-hidden>📈</div>
          <p className="relative text-2xl font-extrabold max-w-[75%]">{t('bannerTitle')}</p>
          <p className="relative mt-1 text-sm max-w-[70%] text-[#3d2a0a]">{t('bannerSub')}</p>
        </section>

        {/* recent */}
        <section>
          <h2 className="h-section">{t('recent')}</h2>
          <div className="card !py-1">
            {state.transactions.slice(0, 5).map((tx) => (
              <div key={tx.id} className="flex justify-between gap-3 py-3 border-b border-line last:border-0">
                <span className="min-w-0">
                  <span className="block truncate">{tx.title}</span>
                  <span className="text-sm text-muted">{date(tx.date, lang, false)}</span>
                </span>
                <span className={`font-semibold shrink-0 ${tx.amount > 0 ? 'text-emerald-300' : ''}`}>
                  {tx.amount > 0 ? '+' : ''}<Money value={tx.amount} />
                </span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}

export function StatusChip({ status, shortfall }) {
  const { t } = useApp()
  if (status === 'overdue') return <Chip tone="red" icon="!">{t('st_overdue')}</Chip>
  if (status === 'shortfall') return <Chip tone="amber" icon="⚠">{t('st_shortfall')}</Chip>
  if (shortfall > 0) return <Chip tone="blue" icon="…">{t('st_soon')}</Chip>
  return <Chip tone="green" icon="✓">{t('st_ok')}</Chip>
}

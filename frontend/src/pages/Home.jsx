import { date, dueText, months, uzs } from '../format'
import { Chip, Progress } from '../components/ui'

export default function Home({ state, go }) {
  const m = state.main
  const next = state.obligations[0]
  const canAdd = state.goals.filter((g) => g.status === 'active').length < state.limits.max_goals

  return (
    <div className="space-y-5">
      {/* Main card */}
      <section className="rounded-3xl p-6 text-white shadow-lg bg-gradient-to-br from-blue-600 to-blue-800">
        <p className="text-blue-100">Основная карта · на жизнь</p>
        <p className="num text-4xl font-bold mt-1 tracking-tight">{uzs(m.main_balance)}</p>
        <div className="mt-4 rounded-2xl bg-white/10 px-4 py-3">
          <p className="text-blue-100 text-sm">Можно спокойно тратить до зарплаты</p>
          <p className="num text-xl font-semibold">{uzs(Math.max(0, m.free_to_spend))}</p>
        </div>
        {m.cash_gap && <p className="mt-3 text-amber-200">⚠ До зарплаты может не хватить денег</p>}
      </section>

      {/* Inbox banner */}
      {state.inbox_count > 0 && (
        <button onClick={() => go('agent')}
          className="w-full card flex items-center gap-3 text-left border-blue-200 bg-blue-50 hover:bg-blue-100">
          <span className="text-3xl" aria-hidden>🤖</span>
          <span className="flex-1">
            <span className="block font-bold">У помощника есть {state.inbox_count === 1 ? 'совет' : `${state.inbox_count} совета`}</span>
            <span className="text-slate-600">Нажмите, чтобы посмотреть</span>
          </span>
          <span className="rounded-full bg-blue-600 text-white w-8 h-8 grid place-items-center font-bold">{state.inbox_count}</span>
        </button>
      )}

      {/* Obligations strip */}
      {next && (
        <button onClick={() => go('obligations')} className="w-full card flex items-center gap-3 text-left hover:bg-slate-50">
          <span className="text-3xl" aria-hidden>🛡</span>
          <span className="flex-1 min-w-0">
            <span className="block font-bold truncate">{next.name}</span>
            <span className="text-slate-600">{uzs(next.amount)} · {dueText(next.due_in_days)}</span>
          </span>
          {next.status === 'shortfall' || next.status === 'overdue'
            ? <Chip tone="amber" icon="⚠">не хватает</Chip>
            : next.shortfall > 0
              ? <Chip tone="blue" icon="…">копится</Chip>
              : <Chip tone="green" icon="✓">отложено</Chip>}
        </button>
      )}

      {/* Goals */}
      <section>
        <div className="flex items-center justify-between mb-3 px-1">
          <h2 className="text-xl font-bold">Мои цели</h2>
          <span className="text-sm text-slate-500">{state.used_percent}% из {state.limits.max_total_percent}% дохода</span>
        </div>
        {state.goals.length === 0 && (
          <div className="card text-center text-slate-600">
            Пока нет целей. Начните с одной — например, на телефон.
          </div>
        )}
        <div className="space-y-3">
          {state.goals.map((g) => (
            <button key={g.id} onClick={() => go('goal', { id: g.id })} className="w-full card text-left hover:bg-slate-50">
              <div className="flex items-center justify-between gap-3">
                <span className="font-bold text-lg truncate">🎯 {g.name}</span>
                {g.status === 'completed'
                  ? <Chip tone="green" icon="🎉">собрано</Chip>
                  : g.status === 'closing'
                    ? <Chip tone="slate" icon="⏳">закрывается</Chip>
                    : <Chip tone={g.disciplined ? 'green' : 'slate'} icon={g.disciplined ? '⭐' : null}>бонус {g.rate}%</Chip>}
              </div>
              <p className="mt-2 text-slate-700 num">Собрано {uzs(g.saved)} из {uzs(g.amount)}</p>
              <div className="mt-2"><Progress value={g.progress} tone={g.progress >= 100 ? 'green' : 'blue'} /></div>
              <p className="mt-2 text-sm text-slate-500">
                {g.progress}% · {g.status === 'active' ? `до ${date(g.expiry)} (≈${months(g.months_worst)})` : ''}
              </p>
            </button>
          ))}
        </div>
        {canAdd && (
          <button className="btn-soft w-full mt-3" onClick={() => go('create')}>＋ Новая цель</button>
        )}
      </section>

      {/* Recent */}
      <section>
        <h2 className="text-xl font-bold mb-3 px-1">Последние операции</h2>
        <div className="card !py-2">
          {state.transactions.slice(0, 6).map((t) => (
            <div key={t.id} className="flex justify-between gap-3 py-2.5 border-b border-slate-100 last:border-0">
              <span className="min-w-0">
                <span className="block truncate">{t.title}</span>
                <span className="text-sm text-slate-500">{date(t.date, false)}</span>
              </span>
              <span className={`num font-semibold shrink-0 ${t.amount > 0 ? 'text-emerald-700' : ''}`}>
                {t.amount > 0 ? '+' : ''}{uzs(t.amount)}
              </span>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

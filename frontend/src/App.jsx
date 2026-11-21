import { useCallback, useEffect, useState } from 'react'
import { api } from './api'
import DemoPanel from './components/DemoPanel'
import SpendResult from './components/SpendResult'
import { ErrorBox, Loading, Toast } from './components/ui'
import Agent from './pages/Agent'
import CreateGoal from './pages/CreateGoal'
import GoalDetail from './pages/GoalDetail'
import Home from './pages/Home'
import Obligations from './pages/Obligations'

const TABS = [
  { key: 'home', icon: '🏠', label: 'Главная' },
  { key: 'obligations', icon: '🛡', label: 'Платежи' },
  { key: 'agent', icon: '🤖', label: 'Помощник' },
]

export default function App() {
  const [state, setState] = useState(null)
  const [error, setError] = useState(null)
  const [route, setRoute] = useState({ name: 'home' })
  const [toast, setToast] = useState(null)
  const [spendResult, setSpendResult] = useState(null)
  const [chat, setChat] = useState([])
  const [draft, setDraft] = useState('')

  const refresh = useCallback(() => {
    api.state().then((s) => { setState(s); setError(null) }).catch((e) => setError(e.message))
  }, [])
  useEffect(() => { refresh() }, [refresh])

  const go = (name, params = {}) => { setRoute({ name, ...params }); window.scrollTo(0, 0) }
  const notify = useCallback((t) => setToast(t), [])
  const tab = ['goal', 'create'].includes(route.name) ? 'home' : route.name
  const lastSource = [...chat].reverse().find((m) => m.source)?.source

  let page
  if (error && !state) page = <ErrorBox text={error} onRetry={refresh} />
  else if (!state) page = <Loading />
  else if (route.name === 'goal') page = <GoalDetail state={state} id={route.id} go={go} onChanged={refresh} notify={notify} />
  else if (route.name === 'create') page = (
    <CreateGoal state={state} go={go} onChanged={refresh} notify={notify}
      askAgent={(q) => { setDraft(q); go('agent') }} />
  )
  else if (route.name === 'obligations') page = <Obligations state={state} onChanged={refresh} notify={notify} />
  else if (route.name === 'agent') page = (
    <Agent state={state} chat={chat} setChat={setChat} draft={draft} setDraft={setDraft} onChanged={refresh} notify={notify} />
  )
  else page = <Home state={state} go={go} />

  return (
    <div className="mx-auto max-w-[420px] min-h-screen bg-[#eef2f7] relative">
      <header className="px-4 pt-5 pb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-9 h-9 rounded-xl bg-blue-600 text-white grid place-items-center font-bold" aria-hidden>M</span>
          <span className="font-bold text-lg">Мечта и Щит</span>
        </div>
        {state?.inbox_count > 0 && tab !== 'agent' && (
          <button className="relative min-h-[44px] min-w-[44px] grid place-items-center" onClick={() => go('agent')}
            aria-label={`Советы помощника: ${state.inbox_count}`}>
            <span className="text-2xl" aria-hidden>🔔</span>
            <span className="absolute top-0.5 right-0.5 rounded-full bg-rose-600 text-white text-xs min-w-5 h-5 px-1 grid place-items-center font-bold">
              {state.inbox_count}
            </span>
          </button>
        )}
      </header>

      <main className="px-4 pb-32">
        {page}
        {state?.demo_mode && route.name === 'home' && (
          <DemoPanel state={{ ...state, agent_source: lastSource }} onChanged={refresh} onSpend={setSpendResult} notify={notify} />
        )}
      </main>

      <nav className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-[420px] z-40 bg-white border-t border-slate-200 grid grid-cols-3 pb-[env(safe-area-inset-bottom)]">
        {TABS.map((t) => (
          <button key={t.key} onClick={() => go(t.key)} aria-current={tab === t.key ? 'page' : undefined}
            className={`flex flex-col items-center justify-center min-h-[64px] text-sm font-medium ${tab === t.key ? 'text-blue-700' : 'text-slate-500'}`}>
            <span className="text-2xl" aria-hidden>{t.icon}</span>{t.label}
          </button>
        ))}
      </nav>

      <SpendResult key={spendResult?.stop_id || spendResult?.merchant} result={spendResult}
        onClose={() => setSpendResult(null)} onChanged={refresh} notify={notify} />
      <Toast toast={toast} onClose={() => setToast(null)} />
    </div>
  )
}

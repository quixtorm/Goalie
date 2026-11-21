import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, setApiLang } from './api'
import { AppCtx } from './ctx'
import { makeT } from './i18n'
import AgentSheet from './components/AgentSheet'
import GuardianSheet from './components/GuardianSheet'
import Header from './components/Header'
import TabBar from './components/TabBar'
import { ErrorBox, Skeleton, Toast } from './components/ui'
import CardGallery from './pages/CardGallery'
import CreateGoal from './pages/CreateGoal'
import GoalDetail from './pages/GoalDetail'
import Goals from './pages/Goals'
import Home from './pages/Home'
import More from './pages/More'
import Obligations from './pages/Obligations'

const readPref = (k, d) => { try { return localStorage.getItem(k) ?? d } catch { return d } }
const writePref = (k, v) => { try { localStorage.setItem(k, v) } catch { /* private mode */ } }

export default function App() {
  const [state, setState] = useState(null)
  const [error, setError] = useState(null)
  const [route, setRoute] = useState({ name: 'home' })
  const [toast, setToast] = useState(null)
  const [guardian, setGuardian] = useState(null)
  const [agentReq, setAgentReq] = useState(null)
  const [chat, setChat] = useState([])
  const [lang, setLangState] = useState(() => {
    const l = readPref('lang', 'ru') === 'uz' ? 'uz' : 'ru'
    setApiLang(l) // before the first request
    return l
  })
  const [hidden, setHidden] = useState(false)

  const refresh = useCallback(() => {
    api.state().then((s) => { setState(s); setError(null) }).catch((e) => setError(e.message))
  }, [])
  // reload server texts (tips, names, transactions) whenever the language changes
  useEffect(() => { setApiLang(lang); refresh() }, [lang, refresh])

  const ctx = useMemo(() => ({
    state, lang, t: makeT(lang), hidden, setHidden, refresh,
    setLang: (l) => { setLangState(l); writePref('lang', l) },
    go: (name, params = {}) => { setRoute({ name, ...params }); window.scrollTo({ top: 0, behavior: 'smooth' }) },
    notify: (x) => setToast(x),
    openAgent: (opts = {}) => setAgentReq({ focus: 'chat', ...opts, nonce: Date.now() }),
    openGuardian: (r) => setGuardian(r),
  }), [state, lang, hidden, refresh])

  const tab = { goal: 'goals', create: 'goals', cards: 'more' }[route.name] || route.name

  let page
  if (error && !state) page = <ErrorBox text={error} onRetry={refresh} />
  else if (!state) page = <Skeleton />
  else if (route.name === 'goal') page = <GoalDetail id={route.id} />
  else if (route.name === 'create') page = <CreateGoal />
  else if (route.name === 'goals') page = <Goals />
  else if (route.name === 'payments') page = <Obligations />
  else if (route.name === 'more') page = <More />
  else if (route.name === 'cards') page = <CardGallery />
  else page = <Home />

  return (
    <AppCtx.Provider value={ctx}>
      <div className="mx-auto max-w-[420px] min-h-screen bg-bg relative overflow-x-clip">
        <Header />
        <main key={route.name + (route.id || '')} className="px-4 pb-32 animate-fade-in">{page}</main>
        <TabBar active={tab} />
        <AgentSheet req={agentReq} onClose={() => setAgentReq(null)} chat={chat} setChat={setChat} />
        <GuardianSheet key={guardian ? guardian.stop_id || guardian.merchant + guardian.amount : 'none'} result={guardian}
          onClose={() => setGuardian(null)} />
        <Toast toast={toast} onClose={() => setToast(null)} />
      </div>
    </AppCtx.Provider>
  )
}

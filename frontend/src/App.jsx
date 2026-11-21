import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, setApiLang } from './api'
import { AppCtx } from './ctx'
import { makeT } from './i18n'
import AgentSheet from './components/AgentSheet'
import GuardianSheet from './components/GuardianSheet'
import Header from './components/Header'
import SalarySheet from './components/SalarySheet'
import StepUpSheet from './components/StepUpSheet'
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
  const [salaryFlow, setSalaryFlow] = useState(null) // last salary waterfall, shown as an animated sheet
  const [agentReq, setAgentReq] = useState(null)
  const [chat, setChat] = useState([])
  const [lang, setLangState] = useState(() => {
    const p = readPref('lang', 'ru')
    const l = ['ru', 'uz', 'en'].includes(p) ? p : 'ru'
    setApiLang(l) // before the first request
    return l
  })
  const [hidden, setHidden] = useState(false)
  // step-up PIN: token kept in memory only (never storage), reused until it expires (5 min, server-side)
  const stepUpToken = useRef(null)
  const [pinReq, setPinReq] = useState(null)
  const askPin = useCallback(() => new Promise((resolve, reject) => setPinReq({ resolve, reject })), [])

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
    // after a salary event: go to Home (the card stack is the animation target) and show the split.
    // State is refreshed by the sheet once the amounts land, so the progress bars visibly grow.
    showSalary: (flow) => { setRoute({ name: 'home' }); window.scrollTo({ top: 0 }); setSalaryFlow(flow) },
    // Runs a protected action: fn(token). Asks for the PIN only if there is no valid token; if the server
    // says the token is no longer valid (401 step_up), asks once more. Cancelling the PIN rejects with .cancelled.
    withStepUp: async (fn) => {
      const cur = stepUpToken.current
      let tok = cur && cur.exp > Date.now() + 5000 ? cur.token : await askPin()
      try {
        return await fn(tok)
      } catch (e) {
        if (e.status === 401 && e.data?.step_up) {
          stepUpToken.current = null
          tok = await askPin()
          return fn(tok)
        }
        throw e
      }
    },
  }), [state, lang, hidden, refresh, askPin])

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
        {route.name !== 'create' && <TabBar active={tab} />}
        <AgentSheet req={agentReq} onClose={() => setAgentReq(null)} chat={chat} setChat={setChat} />
        <GuardianSheet key={guardian ? guardian.stop_id || guardian.merchant + guardian.amount : 'none'} result={guardian}
          onClose={() => setGuardian(null)} />
        <StepUpSheet req={pinReq}
          onDone={(r) => { stepUpToken.current = { token: r.token, exp: Date.now() + r.expires_in * 1000 }; pinReq?.resolve(r.token); setPinReq(null) }}
          onCancel={() => { const e = new Error('cancelled'); e.cancelled = true; pinReq?.reject(e); setPinReq(null) }} />
        <SalarySheet key={salaryFlow ? salaryFlow.breakdown?.length + ':' + salaryFlow.salary + ':' + salaryFlow.main : 'salary-none'}
          flow={salaryFlow} onLanded={refresh} onClose={() => { setSalaryFlow(null); refresh() }} />
        <Toast toast={toast} onClose={() => setToast(null)} />
      </div>
    </AppCtx.Provider>
  )
}

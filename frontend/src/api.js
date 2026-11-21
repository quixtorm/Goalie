// All calls go through the Vite proxy (/api -> FastAPI). No secrets live in the frontend.
// Every request carries X-Lang so server texts (tips, errors, guardian messages) come back in the UI language.
// Single source of truth: <html lang>, set by App before it loads data (a module variable can be duplicated
// by hot-reload, a DOM attribute cannot).
export const setApiLang = (l) => { document.documentElement.lang = l === 'uz' ? 'uz' : 'ru' }
const currentLang = () => (document.documentElement.lang === 'uz' ? 'uz' : 'ru')

const NET_ERR = {
  ru: ['Нет связи с сервером. Проверьте, что бэкенд запущен.', 'Что-то пошло не так. Попробуйте ещё раз.'],
  uz: ["Server bilan aloqa yo'q. Backend ishga tushganini tekshiring.", "Nimadir xato ketdi. Qayta urinib ko'ring."],
}

async function request(method, path, body) {
  const LANG = currentLang()
  let res
  try {
    res = await fetch(`/api${path}`, {
      method,
      headers: { 'X-Lang': LANG, ...(body ? { 'Content-Type': 'application/json' } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new Error(NET_ERR[LANG][0])
  }
  let data = null
  try { data = await res.json() } catch { /* empty body */ }
  if (!res.ok) throw new Error(data?.detail || NET_ERR[LANG][1])
  return data
}

export const api = {
  state: () => request('GET', '/state'),
  mcc: () => request('GET', '/mcc'),
  // The app never sends a percent: the server/agent chooses it.
  planGoal: (name, goal_amount, term_months) => request('POST', '/subcards/plan', { name, goal_amount, ...(term_months ? { term_months } : {}) }),
  createGoal: (name, goal_amount, term_months) => request('POST', '/subcards', { name, goal_amount, ...(term_months ? { term_months } : {}) }),
  useGoal: (id) => request('POST', `/subcards/${encodeURIComponent(id)}/use`),
  closeGoal: (id) => request('POST', `/subcards/${encodeURIComponent(id)}/cancel`, { confirm: true }),
  createObligation: (b) => request('POST', '/obligations', b),
  payObligation: (id) => request('POST', `/obligations/${encodeURIComponent(id)}/pay`, { confirm: true }),
  spend: (b) => request('POST', '/spend', b),
  resolve: (id, option, confirm = false) =>
    request('POST', `/spend/${encodeURIComponent(id)}/resolve`, { option, confirm }),
  reorder: (ids) => request('POST', '/subcards/reorder', { ids }),
  chat: (message, history, lang = 'ru') => request('POST', '/agent/chat', { message, history, lang }),
  inbox: () => request('GET', '/agent/inbox'),
  confirm: (id, option) => request('POST', `/agent/proposals/${encodeURIComponent(id)}/confirm`, option ? { option } : {}),
  reject: (id) => request('POST', `/agent/proposals/${encodeURIComponent(id)}/reject`),
  salary: (amount) => request('POST', '/demo/salary', { amount }),
  transferIn: (amount, source) => request('POST', '/demo/transfer-in', { amount, source }),
  skip: (hours) => request('POST', '/demo/skip-time', { hours }),
  reset: () => request('POST', '/demo/reset'),
}

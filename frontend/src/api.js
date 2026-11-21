// All calls go through the Vite proxy (/api -> FastAPI). No secrets live in the frontend.
// Every request carries X-Lang so server texts (tips, errors, guardian messages) come back in the UI language.
// Single source of truth: <html lang>, set by App before it loads data (a module variable can be duplicated
// by hot-reload, a DOM attribute cannot).
const LANG_CODES = ['ru', 'uz', 'en']
const norm = (l) => (LANG_CODES.includes(l) ? l : 'ru')
export const setApiLang = (l) => { document.documentElement.lang = norm(l) }
const currentLang = () => norm(document.documentElement.lang)

const NET_ERR = {
  ru: ['Нет связи с сервером. Проверьте, что бэкенд запущен.', 'Что-то пошло не так. Попробуйте ещё раз.'],
  uz: ["Server bilan aloqa yo'q. Backend ishga tushganini tekshiring.", "Nimadir xato ketdi. Qayta urinib ko'ring."],
}

// stepUp: short-lived token from POST /auth/step-up, sent only with the few protected actions.
async function request(method, path, body, stepUp) {
  const LANG = currentLang()
  let res
  try {
    res = await fetch(`/api${path}`, {
      method,
      headers: { 'X-Lang': LANG, ...(body ? { 'Content-Type': 'application/json' } : {}), ...(stepUp ? { 'X-Step-Up': stepUp } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new Error(NET_ERR[LANG][0])
  }
  let data = null
  try { data = await res.json() } catch { /* empty body */ }
  if (!res.ok) {
    const err = new Error(data?.detail || NET_ERR[LANG][1])
    err.status = res.status
    err.data = data
    throw err
  }
  return data
}

export const api = {
  state: () => request('GET', '/state'),
  mcc: () => request('GET', '/mcc'),
  // The app never sends a percent: the server/agent chooses it.
  planGoal: (name, goal_amount, term_months) => request('POST', '/subcards/plan', { name, goal_amount, ...(term_months ? { term_months } : {}) }),
  createGoal: (name, goal_amount, term_months) => request('POST', '/subcards', { name, goal_amount, ...(term_months ? { term_months } : {}) }),
  stepUp: (pin) => request('POST', '/auth/step-up', { pin }),
  // protected (need a step-up token): use, early close, proceed anyway, credit application
  useGoal: (id, tok) => request('POST', `/subcards/${encodeURIComponent(id)}/use`, undefined, tok),
  closeGoal: (id, tok) => request('POST', `/subcards/${encodeURIComponent(id)}/cancel`, { confirm: true }, tok),
  createObligation: (b) => request('POST', '/obligations', b),
  payObligation: (id) => request('POST', `/obligations/${encodeURIComponent(id)}/pay`, { confirm: true }),
  spend: (b) => request('POST', '/spend', b),
  resolve: (id, option, confirm = false, tok) =>
    request('POST', `/spend/${encodeURIComponent(id)}/resolve`, { option, confirm }, tok),
  adviseCredit: (amount, term_months, goal_id) => request('POST', '/credits/advise', { amount, ...(term_months ? { term_months } : {}), ...(goal_id ? { goal_id } : {}) }),
  applyCredit: (product_id, amount, months, tok) => request('POST', '/credits/apply', { product_id, amount, months, confirm: true }, tok),
  reorder: (ids) => request('POST', '/subcards/reorder', { ids }),
  chat: (message, history, lang = 'ru') => request('POST', '/agent/chat', { message, history, lang }),
  inbox: () => request('GET', '/agent/inbox'),
  confirm: (id, option, tok) => request('POST', `/agent/proposals/${encodeURIComponent(id)}/confirm`, option ? { option } : {}, tok),
  reject: (id) => request('POST', `/agent/proposals/${encodeURIComponent(id)}/reject`),
  salary: (amount) => request('POST', '/demo/salary', { amount }),
  transferIn: (amount, source) => request('POST', '/demo/transfer-in', { amount, source }),
  skip: (hours) => request('POST', '/demo/skip-time', { hours }),
  reset: () => request('POST', '/demo/reset'),
}

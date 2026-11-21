// All calls go through the Vite proxy (/api -> FastAPI). No secrets live in the frontend.
async function request(method, path, body) {
  let res
  try {
    res = await fetch(`/api${path}`, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new Error('Нет связи с сервером. Проверьте, что бэкенд запущен.')
  }
  let data = null
  try { data = await res.json() } catch { /* empty body */ }
  if (!res.ok) throw new Error(data?.detail || 'Что-то пошло не так. Попробуйте ещё раз.')
  return data
}

export const api = {
  state: () => request('GET', '/state'),
  mcc: () => request('GET', '/mcc'),
  preview: (amount, percent) => request('GET', `/calc/preview?amount=${amount}&percent=${percent}`),
  createGoal: (b) => request('POST', '/subcards', b),
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
  skip: (hours) => request('POST', '/demo/skip-time', { hours }),
  reset: () => request('POST', '/demo/reset'),
}

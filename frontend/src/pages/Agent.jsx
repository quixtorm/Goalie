import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import ProposalCard from '../components/ProposalCard'

const CHIPS = [
  'Хочу накопить 50 млн на машину за 3 года',
  'Хочу телефон в кредит за 20 млн на 12 месяцев под 28%',
  'Сколько я могу потратить?',
  'Мои платежи',
]

export default function Agent({ state, chat, setChat, draft, setDraft, onChanged, notify }) {
  const [inbox, setInbox] = useState(null)
  const [busy, setBusy] = useState(false)
  const endRef = useRef(null)

  const loadInbox = () => api.inbox().then(setInbox).catch((e) => notify({ text: e.message, error: true }))
  useEffect(() => { loadInbox() }, [state.inbox_count, state.clock]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [chat, busy])

  async function send(text) {
    const msg = (text ?? draft).trim()
    if (!msg || busy) return
    setDraft('')
    const history = chat.slice(-10).map((m) => ({ role: m.role, content: m.text.slice(0, 4000) }))
    setChat((c) => [...c, { role: 'user', text: msg }])
    setBusy(true)
    try {
      const r = await api.chat(msg, history)
      setChat((c) => [...c, { role: 'assistant', text: r.reply, proposals: r.proposals || [], source: r.source }])
      onChanged()
    } catch (e) {
      setChat((c) => [...c, { role: 'assistant', text: `⚠ ${e.message}`, proposals: [] }])
    } finally {
      setBusy(false)
    }
  }

  const pending = (inbox || []).filter((p) => p.status === 'pending' && p.origin === 'agent')
  const latest = Object.fromEntries((inbox || []).map((p) => [p.id, p]))

  return (
    <div className="flex flex-col gap-5">
      <div className="px-1">
        <h1 className="text-2xl font-bold">🤖 Помощник</h1>
        <p className="text-slate-600 mt-1">Считает точно, ничего не делает без вашего «да».</p>
      </div>

      {inbox === null ? null : pending.length > 0 && (
        <section className="space-y-3">
          <h2 className="font-bold text-lg px-1">Советы для вас</h2>
          {pending.map((p) => <ProposalCard key={p.id} p={p} notify={notify} onDone={() => { onChanged(); loadInbox() }} />)}
        </section>
      )}

      <section className="space-y-3">
        {chat.length === 0 && (
          <div className="card text-slate-700">
            Здравствуйте! Я помогу накопить на мечту, проверить кредит и не пропустить платежи. Спросите что-нибудь:
          </div>
        )}
        {chat.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'flex justify-end' : ''}>
            {m.role === 'user' ? (
              <div className="max-w-[85%] rounded-3xl rounded-br-md bg-blue-600 text-white px-4 py-3 whitespace-pre-line">{m.text}</div>
            ) : (
              <div className="space-y-3">
                <div className="max-w-[92%] rounded-3xl rounded-bl-md bg-white border border-slate-100 shadow-sm px-4 py-3 whitespace-pre-line text-slate-800">
                  {m.text}
                </div>
                {(m.proposals || []).map((p) => (
                  <ProposalCard key={`${p.id}-${latest[p.id]?.status || p.status}`} p={latest[p.id] || p} notify={notify} onDone={() => { onChanged(); loadInbox() }} />
                ))}
              </div>
            )}
          </div>
        ))}
        {busy && <div className="text-slate-500 px-2" role="status">Помощник думает…</div>}
        <div ref={endRef} />
      </section>

      <div className="flex gap-2 overflow-x-auto pb-1 -mx-4 px-4">
        {CHIPS.map((c) => (
          <button key={c} className="shrink-0 rounded-full border border-blue-200 bg-white px-4 min-h-[40px] text-sm text-blue-800 hover:bg-blue-50"
            onClick={() => send(c)} disabled={busy}>{c}</button>
        ))}
      </div>

      <form className="sticky bottom-20 flex gap-2 bg-[#eef2f7] py-2" onSubmit={(e) => { e.preventDefault(); send() }}>
        <input className="input flex-1 shadow-sm" placeholder="Напишите вопрос…" maxLength={1000} value={draft}
          onChange={(e) => setDraft(e.target.value)} aria-label="Сообщение помощнику" />
        <button className="btn-primary shrink-0 !px-4" disabled={busy || !draft.trim()} aria-label="Отправить">➤</button>
      </form>
    </div>
  )
}

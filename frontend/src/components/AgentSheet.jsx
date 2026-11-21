import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { useApp } from '../ctx'
import ProposalCard from './ProposalCard'
import { Icon, Sheet } from './ui'

// The AI agent lives in a bottom sheet over the current screen (the user never leaves their page).
export default function AgentSheet({ req, onClose, chat, setChat }) {
  const { t, lang, state, refresh, notify } = useApp()
  const [inbox, setInbox] = useState(null)
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const inboxRef = useRef(null)
  const endRef = useRef(null)
  const scrollRef = useRef(null)
  // scroll only inside the sheet (scrollIntoView would also move the page behind it)
  const scrollTo = (el) => { const box = scrollRef.current; if (box && el) box.scrollTo({ top: el.offsetTop - 8, behavior: 'smooth' }) }
  const sentFor = useRef(null)
  const open = !!req

  const loadInbox = () => api.inbox().then(setInbox).catch((e) => notify({ text: e.message, error: true }))
  useEffect(() => { if (open) loadInbox() }, [open, state?.clock, state?.proposals_pending?.length]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!open) return
    if (req.focus === 'inbox') setTimeout(() => scrollTo(inboxRef.current), 350)
    if (req.send && sentFor.current !== req.nonce) { sentFor.current = req.nonce; send(req.send) }
    if (req.draft) setDraft(req.draft)
  }, [req]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (open && req.focus !== 'inbox') { const box = scrollRef.current; box?.scrollTo({ top: box.scrollHeight, behavior: 'smooth' }) }
  }, [chat, busy]) // eslint-disable-line react-hooks/exhaustive-deps

  async function send(text) {
    const msg = (text ?? draft).trim()
    if (!msg || busy) return
    setDraft('')
    const history = chat.slice(-10).map((m) => ({ role: m.role, content: m.text.slice(0, 4000) }))
    setChat((c) => [...c, { role: 'user', text: msg }])
    setBusy(true)
    try {
      const r = await api.chat(msg, history, lang)
      setChat((c) => [...c, { role: 'assistant', text: r.reply, proposals: r.proposals || [], source: r.source }])
      refresh()
    } catch (e) {
      setChat((c) => [...c, { role: 'assistant', text: `⚠ ${e.message}`, proposals: [] }])
    } finally {
      setBusy(false)
    }
  }

  const pending = (inbox || []).filter((p) => p.status === 'pending' && p.origin === 'agent')
  const latest = Object.fromEntries((inbox || []).map((p) => [p.id, p]))

  return (
    <Sheet open={open} onClose={onClose} full label={t('agentTitle')}>
      <div className="px-5 pb-3 flex items-center gap-3 shrink-0 border-b border-line">
        <span className="w-10 h-10 rounded-full bg-gradient-to-br from-amber-300 to-brand grid place-items-center text-white">
          <Icon name="sparkle" size={20} fill strokeWidth={0} />
        </span>
        <div className="flex-1 min-w-0">
          <p className="font-bold">{t('agentTitle')}</p>
          <p className="text-xs text-muted truncate">{t('agentSub')}</p>
        </div>
        <button className="press w-10 h-10 rounded-full bg-card2 grid place-items-center" onClick={onClose} aria-label={t('close')}>
          <Icon name="close" size={20} />
        </button>
      </div>

      <div ref={scrollRef} className="relative flex-1 overflow-y-auto overflow-x-hidden px-5 py-4 space-y-4">
        <div ref={inboxRef}>
          {pending.length > 0 && (
            <section className="space-y-3 mb-2">
              <h3 className="font-bold flex items-center gap-2"><Icon name="bell" size={18} /> {t('inbox')} · {pending.length}</h3>
              {pending.map((p) => <ProposalCard key={p.id} p={p} onDone={loadInbox} />)}
            </section>
          )}
        </div>

        {chat.length === 0 && (
          <div className="rounded-card bg-card2 border border-line p-4 text-ink/90">{t('hello')}</div>
        )}
        {chat.map((m, i) => (
          <div key={i} className={`animate-rise ${m.role === 'user' ? 'flex justify-end' : ''}`}>
            {m.role === 'user' ? (
              <div className="max-w-[85%] rounded-[20px] rounded-br-md bg-brand text-white px-4 py-3 whitespace-pre-line">{m.text}</div>
            ) : (
              <div className="space-y-3">
                <div className="max-w-[94%] rounded-[20px] rounded-bl-md bg-card2 border border-line px-4 py-3 whitespace-pre-line text-ink">
                  {m.text}
                </div>
                {(m.proposals || []).map((p) => (
                  <ProposalCard key={`${p.id}-${latest[p.id]?.status || p.status}`} p={latest[p.id] || p} onDone={loadInbox} />
                ))}
              </div>
            )}
          </div>
        ))}
        {busy && (
          <div className="flex items-center gap-2 text-muted px-1" role="status">
            <span className="flex gap-1">{[0, 1, 2].map((d) => <span key={d} className="w-2 h-2 rounded-full bg-muted animate-pulse" style={{ animationDelay: `${d * 150}ms` }} />)}</span>
            {t('thinking')}
          </div>
        )}
        <div ref={endRef} />
      </div>


      <div className="shrink-0 border-t border-line px-4 pt-3 pb-5 space-y-3 bg-card overflow-hidden">
        <div className="flex gap-2 overflow-x-auto -mx-4 px-4">
          {t('chips').map((c) => (
            <button key={c} className="press shrink-0 rounded-full border border-brand/40 bg-brand/10 text-brand-light px-4 min-h-[40px] text-sm"
              onClick={() => send(c)} disabled={busy}>{c}</button>
          ))}
        </div>
        <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); send() }}>
          <input className="input flex-1 !min-h-[48px] !text-base" placeholder={t('placeholder')} maxLength={1000} value={draft}
            onChange={(e) => setDraft(e.target.value)} aria-label={t('placeholder')} />
          <button className="btn-primary shrink-0 !px-4 !min-h-[48px]" disabled={busy || !draft.trim()} aria-label={t('send')}>
            <Icon name="send" size={20} />
          </button>
        </form>
      </div>
    </Sheet>
  )
}

import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { api } from '../api'
import { useApp } from '../ctx'
import BankCard from './BankCard'
import { Icon } from './ui'

const PEEK = 30      // collapsed: how much of each card behind the main card shows
const STEP = 70      // expanded: how much of each card shows in the wallet list
const SPRING = 'transform 350ms cubic-bezier(.34,1.3,.64,1), opacity 250ms ease'
const LONG_PRESS = 380

// Hours left of a 24h cooling-off on this goal (from the demo clock).
export function coolingFor(state, goalId) {
  const st = (state.stops || []).find((x) => x.status === 'cooling' && x.source_id === goalId && x.ready_at)
  if (!st) return null
  const ms = new Date(st.ready_at) - new Date(state.clock)
  return ms > 0 ? { hoursLeft: Math.max(1, Math.ceil(ms / 3600000)) } : null
}

/** Wallet: main card in front, subcards fanned behind it; tap to expand into an overlapping list. */
export default function WalletStack() {
  const { state, t, go, notify, refresh } = useApp()
  const wrap = useRef(null)
  const [w, setW] = useState(343)
  const [open, setOpen] = useState(false)
  const [sel, setSel] = useState(null)
  const [drag, setDrag] = useState(null)       // {id, from, dy}
  const [order, setOrder] = useState(null)     // optimistic order of active goal ids
  const press = useRef(null)
  const suppressClick = useRef(false)

  useLayoutEffect(() => {
    const el = wrap.current
    if (!el) return
    const ro = new ResizeObserver(([e]) => setW(e.contentRect.width))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const cardH = w / (85.6 / 53.98)
  const max = state.limits.max_goals
  const active = state.goals.filter((g) => g.status === 'active')
  const others = state.goals.filter((g) => g.status !== 'active')
  const serverIds = active.map((g) => g.id).join()
  useEffect(() => { setOrder(null) }, [serverIds])

  const ids = order || active.map((g) => g.id)
  // live order while dragging
  let liveIds = ids
  if (drag) {
    const to = Math.max(0, Math.min(ids.length - 1, Math.round(drag.from + drag.dy / STEP)))
    liveIds = ids.filter((x) => x !== drag.id)
    liveIds.splice(to, 0, drag.id)
  }
  const byId = Object.fromEntries(state.goals.map((g) => [g.id, g]))
  const cards = [...liveIds.map((id) => byId[id]).filter(Boolean), ...others]
  const ghost = active.length < max
  const items = [...cards.map((g) => ({ type: 'goal', g })), ...(ghost ? [{ type: 'ghost' }] : [])]
  const N = items.length

  // tap outside collapses
  useEffect(() => {
    if (!open) return
    const onDown = (e) => {
      if (document.querySelector('[role="dialog"]')) return
      if (wrap.current && !wrap.current.contains(e.target)) { setOpen(false); setSel(null) }
    }
    document.addEventListener('pointerdown', onDown)
    return () => document.removeEventListener('pointerdown', onDown)
  }, [open])

  // while dragging, stop the page from scrolling (touchmove must be non-passive to be cancelable)
  useEffect(() => {
    const el = wrap.current
    if (!el) return
    const block = (e) => { if (press.current?.active) e.preventDefault() }
    el.addEventListener('touchmove', block, { passive: false })
    return () => el.removeEventListener('touchmove', block)
  }, [])

  // ---- geometry (transform-only) ----
  const extra = sel !== null ? cardH - STEP + 60 : 0
  const pos = (j) => {
    if (!open) {
      const k = j + 1
      return { y: (N - 1 - j) * PEEK, s: 1 - 0.04 * k, z: 30 - j, dim: Math.min(0.45, 0.14 * k) }
    }
    return { y: j * STEP + (sel !== null && j > sel ? extra : 0), s: 1, z: 10 + j, dim: 0 }
  }
  const mainPos = open ? { y: N * STEP + extra, z: 10 + N } : { y: N * PEEK, z: 40 }
  const height = (open ? N * STEP + extra : N * PEEK) + cardH

  // ---- long-press drag to reorder (expanded list, active goals only) ----
  function onDown(e, g, j) {
    if (!open || g.status !== 'active' || active.length < 2) return
    const startY = e.clientY
    const el = e.currentTarget
    const pid = e.pointerId
    press.current = { id: g.id, from: j, startY, active: false, timer: setTimeout(() => {
      if (!press.current) return
      press.current.active = true
      suppressClick.current = true
      // capture only once dragging starts, so ordinary taps still reach the card
      try { el.setPointerCapture?.(pid) } catch { /* pointer already gone */ }
      navigator.vibrate?.(12)
      setSel(null)
      setDrag({ id: g.id, from: j, dy: 0 })
    }, LONG_PRESS) }
  }
  function onMove(e) {
    const p = press.current
    if (!p) return
    const dy = e.clientY - p.startY
    if (!p.active) { if (Math.abs(dy) > 8) { clearTimeout(p.timer); press.current = null } return }
    setDrag((d) => d && { ...d, dy })
  }
  async function onUp() {
    const p = press.current
    press.current = null
    if (!p) return
    clearTimeout(p.timer)
    if (!p.active) return
    const finalIds = liveIds
    setDrag(null)
    if (finalIds.join() !== ids.join()) {
      setOrder(finalIds)
      try { await api.reorder(finalIds); refresh() } catch (err) { setOrder(null); notify({ text: err.message, error: true }) }
    }
    setTimeout(() => { suppressClick.current = false }, 0)
  }

  function tapItem(it, j) {
    if (suppressClick.current) return
    if (!open) { if (it.type === 'ghost' && N === 1) go('create'); else setOpen(true); return }
    if (it.type === 'ghost') { go('create'); return }
    setSel(sel === j ? null : j)
  }

  return (
    <div className="mb-2">
      {cards.length > 0 && (
        <button onClick={() => { setOpen(!open); setSel(null) }} aria-expanded={open}
          className="press w-full flex items-center justify-between rounded-btn bg-white/10 hover:bg-white/15 px-4 min-h-[46px] font-semibold text-white mb-3">
          <span className="flex items-center gap-2"><Icon name="target" size={20} />
            {open ? t('hideSubcards') : t('showSubcards')} ({active.length}/{max})</span>
          <Icon name={open ? 'chevronU' : 'chevronD'} size={20} />
        </button>
      )}

      <div ref={wrap} className="relative" style={{ height, transition: 'height 350ms cubic-bezier(.34,1.3,.64,1)' }}
        onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={onUp}>
        {items.map((it, j) => {
          const p = pos(j)
          const isDrag = drag && it.g && drag.id === it.g.id
          const y = isDrag ? drag.from * STEP + drag.dy : p.y
          return (
            <div key={it.g ? it.g.id : 'ghost'} className="absolute inset-x-0 top-0"
              style={{
                transform: `translateY(${y}px) scale(${isDrag ? 1.04 : p.s})`, transformOrigin: 'top center',
                zIndex: isDrag ? 80 : sel === j ? 70 : p.z, transition: isDrag ? 'none' : SPRING,
                touchAction: open ? 'pan-y' : 'auto',
              }}
              onPointerDown={(e) => it.g && onDown(e, it.g, j)}>
              {it.type === 'ghost'
                ? <BankCard kind="ghost" label={N === 1 ? t('addSubcard') : t('addSlot')} onClick={() => tapItem(it, j)} />
                : <BankCard goal={it.g} priority={it.g.status === 'active' ? liveIds.indexOf(it.g.id) + 1 : 0}
                    cooling={coolingFor(state, it.g.id)} tilt={open}
                    onUse={() => go('goal', { id: it.g.id })} onClick={() => tapItem(it, j)} />}
              {/* darkening for cards behind the main card */}
              {p.dim > 0 && <div className="absolute inset-0 rounded-[20px] bg-black pointer-events-none transition-opacity duration-300" style={{ opacity: p.dim }} />}
            </div>
          )
        })}

        {/* details button for the card brought forward */}
        {open && sel !== null && items[sel]?.g && (
          <button className="btn-primary absolute inset-x-0 !min-h-[46px] animate-rise" style={{ top: sel * STEP + cardH + 8, zIndex: 75 }}
            onClick={() => go('goal', { id: items[sel].g.id })}>
            {t('details')} <Icon name="chevronR" size={18} />
          </button>
        )}

        <div className="absolute inset-x-0 top-0" style={{ transform: `translateY(${mainPos.y}px)`, zIndex: mainPos.z, transition: SPRING }}>
          <BankCard kind="main" main={{ balance: state.main.main_balance, free: Math.max(0, state.main.free_to_spend) }}
            onClick={() => { if (open) { setOpen(false); setSel(null) } else if (N > 0 && cards.length) setOpen(true) }} />
        </div>
      </div>

      {open && active.length > 1 && <p className="mt-3 text-center text-sm text-white/70">{t('dragHint')}</p>}
    </div>
  )
}

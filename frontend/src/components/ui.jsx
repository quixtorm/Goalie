import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { uzs } from '../format'
import { useApp } from '../ctx'

// ---------- icons (inline SVG, stroke = currentColor) ----------
const P = {
  search: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14Zm10 17-5.2-5.2',
  sparkle: 'M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8L12 3Zm6 11 .9 2.1L21 17l-2.1.9L18 20l-.9-2.1L15 17l2.1-.9L18 14Z',
  bell: 'M6 16V11a6 6 0 1 1 12 0v5l1.5 2h-15L6 16Zm4 3a2 2 0 0 0 4 0',
  gear: 'M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6Zm7.4 3a7.4 7.4 0 0 0-.1-1.2l2-1.6-2-3.4-2.4.9a7.5 7.5 0 0 0-2-1.2L14.5 3h-5l-.4 2.5a7.5 7.5 0 0 0-2 1.2l-2.4-.9-2 3.4 2 1.6a7.4 7.4 0 0 0 0 2.4l-2 1.6 2 3.4 2.4-.9a7.5 7.5 0 0 0 2 1.2l.4 2.5h5l.4-2.5a7.5 7.5 0 0 0 2-1.2l2.4.9 2-3.4-2-1.6c.1-.4.1-.8.1-1.2Z',
  user: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 8a7 7 0 0 1 14 0',
  home: 'M4 11 12 4l8 7v9h-5v-6H9v6H4v-9Z',
  pay: 'M4 6h16v12H4V6Zm0 4h16M8 15h3',
  target: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm0 4a5 5 0 1 0 0 10 5 5 0 0 0 0-10Zm0 4a1 1 0 1 0 0 2 1 1 0 0 0 0-2Z',
  menu: 'M4 7h16M4 12h16M4 17h16',
  plus: 'M12 5v14M5 12h14',
  eye: 'M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Zm10-3a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z',
  eyeOff: 'M3 3l18 18M10.6 6.1A10 10 0 0 1 12 6c6.4 0 10 6 10 6a17 17 0 0 1-3.3 3.9M6.6 6.6C3.8 8.3 2 12 2 12s3.6 6 10 6c1.6 0 3-.4 4.2-.9M9.9 9.9a3 3 0 0 0 4.2 4.2',
  chevronR: 'M9 6l6 6-6 6', chevronD: 'M6 9l6 6 6-6', chevronU: 'M6 15l6-6 6 6', back: 'M15 6l-6 6 6 6',
  shield: 'M12 3 5 6v6c0 4.4 3 7.6 7 9 4-1.4 7-4.6 7-9V6l-7-3Z',
  calc: 'M6 3h12v18H6V3Zm3 4h6M9 11h.01M12 11h.01M15 11h.01M9 14h.01M12 14h.01M15 14h.01M9 17h.01M12 17h.01M15 17h.01',
  close: 'M6 6l12 12M18 6 6 18',
  send: 'M4 12 20 4l-6 16-3-7-7-1Z',
  check: 'M5 12l5 5L20 7',
  clock: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm0 4v5l3 2',
  globe: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm-9 9h18M12 3c2.5 2.5 3.8 5.6 3.8 9S14.5 18.5 12 21c-2.5-2.5-3.8-5.6-3.8-9S9.5 5.5 12 3Z',
  lock: 'M7 11V8a5 5 0 0 1 10 0v3M5 11h14v10H5V11Z',
  film: 'M4 5h16v14H4V5Zm4 0v14M16 5v14M4 9h4M4 15h4M16 9h4M16 15h4',
  snow: 'M12 2v20M3.3 7l17.4 10M3.3 17 20.7 7M9 3.5l3 2 3-2M9 20.5l3-2 3 2M3.6 10.5l3.2-1.4-.4-3.5M20.4 13.5l-3.2 1.4.4 3.5M3.6 13.5l3.2 1.4-.4 3.5M20.4 10.5l-3.2-1.4.4-3.5',
  waves: 'M8.5 8.5a5 5 0 0 1 0 7M12 6a8.5 8.5 0 0 1 0 12M15.5 3.5a12 12 0 0 1 0 17',
  info: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm0 8v5m0-8h.01',
  star: 'M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9L12 3Z',
  chart: 'M4 20V10M10 20V4M16 20v-7M22 20H2',
  sort: 'M7 4v16M3 8l4-4 4 4M17 20V4M13 16l4 4 4-4',
}

export function Icon({ name, size = 22, className = '', fill = false, strokeWidth = 1.8 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" className={className} aria-hidden="true"
      fill={fill ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d={P[name]} />
    </svg>
  )
}

// ---------- money (respects the "hide amounts" eye toggle) ----------
export function Money({ value, className = '' }) {
  const { hidden } = useApp()
  return <span className={`num ${className}`}>{hidden ? '••••••' : uzs(value)}</span>
}

// ---------- progress ----------
export function Progress({ value, tone = 'blue', className = '' }) {
  const color = { blue: 'bg-brand', green: 'bg-emerald-400', amber: 'bg-amber-400', white: 'bg-white' }[tone]
  return (
    <div className={`h-2.5 w-full rounded-full bg-white/10 overflow-hidden ${className}`} role="progressbar"
      aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}>
      <div className={`h-full ${color} rounded-full transition-[width] duration-700 ease-out`} style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
    </div>
  )
}

export function Ring({ value, size = 168 }) {
  const r = 70, c = 2 * Math.PI * r
  const [shown, setShown] = useState(0)
  useEffect(() => { const t = setTimeout(() => setShown(value), 50); return () => clearTimeout(t) }, [value])
  return (
    <svg width={size} height={size} viewBox="0 0 168 168" role="img" aria-label={`${value}%`}>
      <defs>
        <linearGradient id="ringg" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0" stopColor="#5AA2F0" /><stop offset="1" stopColor="#34D399" />
        </linearGradient>
      </defs>
      <circle cx="84" cy="84" r={r} stroke="rgba(255,255,255,.08)" strokeWidth="14" fill="none" />
      <circle cx="84" cy="84" r={r} stroke="url(#ringg)" strokeWidth="14" fill="none" strokeLinecap="round"
        strokeDasharray={c} strokeDashoffset={c * (1 - Math.min(100, shown) / 100)} transform="rotate(-90 84 84)"
        style={{ transition: 'stroke-dashoffset 1s cubic-bezier(.2,.8,.2,1)' }} />
      <text x="84" y="92" textAnchor="middle" className="fill-ink" style={{ font: '700 30px Inter, system-ui' }}>{value}%</text>
    </svg>
  )
}

// Colour is never the only signal: every chip has an icon/symbol + word.
export function Chip({ tone = 'slate', icon, children }) {
  const cls = {
    green: 'bg-emerald-400/10 text-emerald-300 border-emerald-400/25',
    amber: 'bg-amber-400/10 text-amber-300 border-amber-400/25',
    red: 'bg-rose-500/10 text-rose-300 border-rose-400/25',
    blue: 'bg-brand/15 text-brand-light border-brand/30',
    slate: 'bg-white/5 text-muted border-line',
  }[tone]
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-sm font-medium whitespace-nowrap ${cls}`}>
      {icon && <span aria-hidden>{icon}</span>}{children}
    </span>
  )
}

// Page scroll lock shared by all open sheets: counted, so overlapping sheets can never leave the page locked.
let openSheets = 0
function lockScroll() { if (openSheets++ === 0) document.body.style.overflow = 'hidden' }
function unlockScroll() { openSheets = Math.max(0, openSheets - 1); if (openSheets === 0) document.body.style.overflow = '' }

// ---------- bottom sheet: slide-up, swipe down / tap outside / Esc to close ----------
export function Sheet({ open, onClose, children, full = false, label, z = 50 }) {
  const [dy, setDy] = useState(0)
  const start = useRef(null)
  const closeRef = useRef(onClose)
  closeRef.current = onClose
  useEffect(() => {
    if (!open) return
    const onKey = (e) => e.key === 'Escape' && closeRef.current?.()
    window.addEventListener('keydown', onKey)
    lockScroll()
    return () => { window.removeEventListener('keydown', onKey); unlockScroll(); setDy(0) }
  }, [open])
  if (!open) return null

  const down = (e) => { start.current = e.clientY; e.currentTarget.setPointerCapture?.(e.pointerId) }
  const move = (e) => { if (start.current !== null) setDy(Math.max(0, e.clientY - start.current)) }
  const up = () => { if (dy > 110) onClose?.(); setDy(0); start.current = null }

  // Portal to <body>: a sheet opened inside a page must sit above the fixed tab bar. The page container's
  // fade-in animation creates its own stacking context, which would otherwise trap the sheet below the bar.
  return createPortal(
    <div className="fixed inset-0 flex items-end justify-center" style={{ zIndex: z }} role="dialog" aria-modal="true" aria-label={label}>
      <div className="absolute inset-0 bg-black/60 animate-fade-in" onClick={onClose} />
      <div className="relative w-full max-w-[420px] animate-sheet-up">
        <div className={`bg-card border-t border-line rounded-t-[28px] shadow-soft flex flex-col ${full ? 'h-[85vh]' : 'max-h-[88vh]'}`}
          style={{ transform: `translateY(${dy}px)`, transition: dy ? 'none' : 'transform .2s' }}>
          <div className="pt-3 pb-2 cursor-grab touch-none select-none shrink-0" onPointerDown={down} onPointerMove={move}
            onPointerUp={up} onPointerCancel={up}>
            <div className="mx-auto h-1.5 w-11 rounded-full bg-white/20" />
          </div>
          {/* min-h-0 lets tall content scroll inside the sheet instead of pushing buttons off-screen */}
          <div className="sheet-body min-h-0 flex-1 flex flex-col">{children}</div>
        </div>
      </div>
    </div>,
    document.body,
  )
}

export function ConfirmSheet({ open, title, text, confirmLabel, onConfirm, onClose, busy, tone = 'primary' }) {
  const { t } = useApp()
  return (
    <Sheet open={open} onClose={onClose} label={title} z={70}>
      <div className="flex flex-col min-h-0 flex-1">
        {/* long text scrolls; the buttons stay pinned and always visible */}
        <div className="px-6 min-h-0 overflow-y-auto overscroll-contain">
          <h2 className="text-xl font-bold mb-2">{title}</h2>
          <p className="text-muted whitespace-pre-line">{text}</p>
        </div>
        <div className="shrink-0 px-6 pt-4 pb-8 grid gap-2 border-t border-line mt-4">
          <button className={tone === 'success' ? 'btn-success' : 'btn-primary'} onClick={onConfirm} disabled={busy}>
            {busy ? t('busy') : confirmLabel}
          </button>
          <button className="btn-ghost" onClick={onClose} disabled={busy}>{t('cancel')}</button>
        </div>
      </div>
    </Sheet>
  )
}

export function Toast({ toast, onClose }) {
  useEffect(() => {
    if (!toast) return
    const t = setTimeout(onClose, toast.long ? 6000 : 3500)
    return () => clearTimeout(t)
  }, [toast, onClose])
  if (!toast) return null
  return (
    <div className="fixed bottom-28 left-1/2 -translate-x-1/2 z-[80] w-[calc(100%-32px)] max-w-[388px] animate-rise" role="status">
      <div className={`${toast.error ? 'bg-rose-600' : 'bg-card2 border border-line'} text-ink rounded-btn px-4 py-3 shadow-soft flex gap-3 items-start`}>
        <span aria-hidden>{toast.error ? '⚠' : '✓'}</span>
        <span className="flex-1 whitespace-pre-line">{toast.text}</span>
      </div>
    </div>
  )
}

export function Skeleton() {
  return (
    <div className="space-y-4 pt-2" role="status" aria-label="loading">
      <div className="skeleton h-6 w-40" />
      <div className="skeleton h-10 w-64" />
      <div className="skeleton h-12" />
      <div className="skeleton h-48" />
      <div className="grid grid-cols-4 gap-3">{[0, 1, 2, 3].map((i) => <div key={i} className="skeleton h-20" />)}</div>
      <div className="skeleton h-28" />
    </div>
  )
}

export function ErrorBox({ text, onRetry }) {
  const { t } = useApp()
  return (
    <div className="card text-center mt-6">
      <p className="text-rose-300 font-medium">⚠ {text}</p>
      {onRetry && <button className="btn-ghost mt-4" onClick={onRetry}>{t('retry')}</button>}
    </div>
  )
}

// Income type chip: Зарплата / Перевод / Другое (only salary counts for the plan)
export function TypeChip({ type }) {
  const { t } = useApp()
  if (!type) return null
  const cls = {
    SALARY: 'bg-emerald-400/15 text-emerald-300 border-emerald-400/30',
    TRANSFER: 'bg-violet-400/15 text-violet-200 border-violet-400/30',
    OTHER: 'bg-white/10 text-muted border-line',
  }[type] || 'bg-white/10 text-muted border-line'
  return <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold ${cls}`}>{t(`type_${type}`)}</span>
}

// Plain-language note shown on every plan panel.
export function SalaryOnlyNote({ worstAnnual }) {
  const { t } = useApp()
  return (
    <div className="mt-3 rounded-[14px] bg-emerald-400/[0.07] border border-emerald-400/20 p-3 text-sm">
      <p className="flex gap-2 text-ink/90"><Icon name="info" size={18} className="shrink-0 text-emerald-300 mt-0.5" />{t('salaryOnly')}</p>
      {worstAnnual != null && (
        <p className="mt-1.5 pl-[26px] text-muted">{t('worstAnnual')}: <Money value={worstAnnual} className="text-ink font-semibold" /></p>
      )}
    </div>
  )
}

export function Row({ label, children, strong }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-3 border-b border-line last:border-0">
      <span className="text-muted">{label}</span>
      <span className={`num text-right ${strong ? 'font-bold text-ink' : 'font-medium text-ink/90'}`}>{children}</span>
    </div>
  )
}

export function BackButton({ onClick }) {
  const { t } = useApp()
  return (
    <button className="press inline-flex items-center gap-1 min-h-[44px] -ml-1 text-muted hover:text-ink" onClick={onClick}>
      <Icon name="back" size={20} /> {t('back')}
    </button>
  )
}

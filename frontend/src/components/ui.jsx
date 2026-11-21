import { useEffect } from 'react'

export function Progress({ value, tone = 'blue' }) {
  const color = { blue: 'bg-blue-600', green: 'bg-emerald-500', amber: 'bg-amber-500' }[tone]
  return (
    <div className="h-3 w-full rounded-full bg-slate-100 overflow-hidden" role="progressbar"
      aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}>
      <div className={`h-full ${color} rounded-full transition-all duration-500`} style={{ width: `${Math.min(100, value)}%` }} />
    </div>
  )
}

// Colour is never the only signal: every chip has an icon + word.
export function Chip({ tone = 'slate', icon, children }) {
  const cls = {
    green: 'bg-emerald-50 text-emerald-800 border-emerald-200',
    amber: 'bg-amber-50 text-amber-900 border-amber-200',
    red: 'bg-rose-50 text-rose-800 border-rose-200',
    blue: 'bg-blue-50 text-blue-800 border-blue-200',
    slate: 'bg-slate-50 text-slate-700 border-slate-200',
  }[tone]
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-sm font-medium ${cls}`}>
      {icon && <span aria-hidden>{icon}</span>}{children}
    </span>
  )
}

export function Modal({ open, onClose, title, children }) {
  useEffect(() => {
    if (!open) return
    const onKey = (e) => e.key === 'Escape' && onClose?.()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-slate-900/40 p-0 sm:p-4"
      onClick={onClose} role="dialog" aria-modal="true" aria-label={title}>
      <div className="w-full max-w-[420px] rounded-t-3xl sm:rounded-3xl bg-white p-6 pb-8 shadow-xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}>
        {title && <h2 className="text-xl font-bold mb-3">{title}</h2>}
        {children}
      </div>
    </div>
  )
}

export function ConfirmModal({ open, title, text, confirmLabel, onConfirm, onClose, busy, tone = 'primary' }) {
  return (
    <Modal open={open} onClose={onClose} title={title}>
      <p className="text-base text-slate-700 whitespace-pre-line">{text}</p>
      <div className="mt-6 grid gap-2">
        <button className={tone === 'success' ? 'btn-success' : 'btn-primary'} onClick={onConfirm} disabled={busy}>
          {busy ? 'Секунду…' : confirmLabel}
        </button>
        <button className="btn-soft" onClick={onClose} disabled={busy}>Отмена</button>
      </div>
    </Modal>
  )
}

export function Toast({ toast, onClose }) {
  useEffect(() => {
    if (!toast) return
    const t = setTimeout(onClose, 4000)
    return () => clearTimeout(t)
  }, [toast, onClose])
  if (!toast) return null
  const tone = toast.error ? 'bg-rose-600' : 'bg-slate-900'
  return (
    <div className="fixed bottom-24 left-1/2 -translate-x-1/2 z-[60] w-[calc(100%-32px)] max-w-[388px]" role="status">
      <div className={`${tone} text-white rounded-2xl px-4 py-3 shadow-lg text-base flex gap-3 items-start`}>
        <span aria-hidden>{toast.error ? '⚠' : '✓'}</span>
        <span className="flex-1">{toast.text}</span>
      </div>
    </div>
  )
}

export function Loading({ text = 'Загружаем…' }) {
  return <div className="py-16 text-center text-slate-500" role="status">{text}</div>
}

export function ErrorBox({ text, onRetry }) {
  return (
    <div className="card text-center">
      <p className="text-rose-700 font-medium">⚠ {text}</p>
      {onRetry && <button className="btn-soft mt-4" onClick={onRetry}>Попробовать снова</button>}
    </div>
  )
}

export function Row({ label, value, strong }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-2.5 border-b border-slate-100 last:border-0">
      <span className="text-slate-600">{label}</span>
      <span className={`num text-right ${strong ? 'font-bold text-slate-900' : 'font-medium text-slate-800'}`}>{value}</span>
    </div>
  )
}

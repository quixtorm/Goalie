import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { useApp } from '../ctx'
import { Icon, Sheet } from './ui'

// Small PIN sheet, shown ONLY before actions that release protected money (use, early close,
// "proceed anyway", credit application). The server issues a 5-minute token; 3 wrong PINs -> 60 s lock.
export default function StepUpSheet({ req, onDone, onCancel }) {
  const { t } = useApp()
  const [pin, setPin] = useState('')
  const [error, setError] = useState(null)
  const [lockedFor, setLockedFor] = useState(0)
  const [busy, setBusy] = useState(false)
  const input = useRef(null)

  useEffect(() => { if (req) { setPin(''); setError(null); setTimeout(() => input.current?.focus(), 350) } }, [req])
  useEffect(() => {
    if (lockedFor <= 0) return
    const tm = setTimeout(() => setLockedFor((s) => s - 1), 1000)
    return () => clearTimeout(tm)
  }, [lockedFor])

  async function submit(value) {
    setBusy(true)
    try {
      const r = await api.stepUp(value)
      onDone(r)
    } catch (e) {
      setPin('')
      if (e.status === 423) { setLockedFor(e.data?.retry_after || 60); setError(null) } else setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  function type(v) {
    const d = v.replace(/\D/g, '').slice(0, 4)
    setPin(d)
    setError(null)
    if (d.length === 4 && !busy && lockedFor <= 0) submit(d)
  }

  const keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '', '0', '⌫']
  return (
    <Sheet open={!!req} onClose={onCancel} label={t('pinTitle')} z={90}>
      <div className="px-6 pb-8 text-center">
        <div className="mx-auto w-12 h-12 rounded-full bg-brand/15 text-brand-light grid place-items-center mb-2"><Icon name="lock" /></div>
        <h2 className="text-xl font-bold">{t('pinTitle')}</h2>
        <p className="text-muted text-sm mt-1">{t('pinSub')}</p>
        <input ref={input} className="sr-only" inputMode="numeric" autoComplete="one-time-code" aria-label={t('pinTitle')}
          value={pin} onChange={(e) => type(e.target.value)} disabled={lockedFor > 0} />
        <div className="mt-5 flex justify-center gap-4" aria-hidden onClick={() => input.current?.focus()}>
          {[0, 1, 2, 3].map((i) => (
            <span key={i} className={`w-4 h-4 rounded-full border-2 ${i < pin.length ? 'bg-brand-light border-brand-light' : 'border-white/30'}`} />
          ))}
        </div>
        <p className="min-h-[24px] mt-3 text-sm" role="alert">
          {lockedFor > 0 ? <span className="text-amber-300">{t('pinLocked', lockedFor)}</span>
            : error ? <span className="text-rose-300">⚠ {error}</span>
              : busy ? <span className="text-muted">{t('busy')}</span> : <span className="text-muted">{t('pinHint')}</span>}
        </p>
        <div className="mt-3 grid grid-cols-3 gap-2 max-w-[280px] mx-auto">
          {keys.map((k, i) => k === '' ? <span key={i} /> : (
            <button key={i} className="press h-14 rounded-2xl bg-card2 border border-line text-2xl font-semibold disabled:opacity-40"
              disabled={busy || lockedFor > 0} aria-label={k === '⌫' ? t('pinErase') : k}
              onClick={() => type(k === '⌫' ? pin.slice(0, -1) : pin + k)}>{k}</button>
          ))}
        </div>
        <button className="btn-link mt-3" onClick={onCancel}>{t('cancel')}</button>
      </div>
    </Sheet>
  )
}

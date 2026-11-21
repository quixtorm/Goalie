import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useApp } from '../ctx'
import { uzs } from '../format'
import { Icon, Money, Progress } from './ui'

const STEP_MS = 550   // one waterfall line every STEP_MS
const FLY_MS = 650    // amount chip flight into its card
const CLOSE_MS = 3000 // auto-close after the last amount has landed

const reduced = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

/** "Goalie split the salary": shows the server's waterfall (`flow.breakdown`) line by line. Each amount flies
 *  into its card in the home stack (data-fly=target_id) and the line's progress bar grows from the server's
 *  progress_before to progress_after. All numbers come from /demo/salary; nothing is computed here.
 *  Auto-closes 3 s after the last line lands, or on tap. */
export default function SalarySheet({ flow, onLanded, onClose }) {
  const { t, hidden } = useApp()
  const [shown, setShown] = useState(0)
  const [grown, setGrown] = useState(0)
  const amountRefs = useRef([])
  const closeRef = useRef(onClose)
  closeRef.current = onClose
  const landedRef = useRef(onLanded)
  landedRef.current = onLanded
  const lines = flow?.breakdown || []

  // reveal lines one by one, then refresh the app state (cards' progress grows), then auto-close
  useEffect(() => {
    if (!flow) return
    const timers = []
    lines.forEach((_, i) => timers.push(setTimeout(() => setShown(i + 1), 350 + i * STEP_MS)))
    const landed = 350 + lines.length * STEP_MS + FLY_MS
    timers.push(setTimeout(() => landedRef.current?.(), landed - FLY_MS / 2))
    timers.push(setTimeout(() => closeRef.current?.(), landed + CLOSE_MS))
    const onKey = (e) => e.key === 'Escape' && closeRef.current?.()
    window.addEventListener('keydown', onKey)
    return () => { timers.forEach(clearTimeout); window.removeEventListener('keydown', onKey) }
  }, [flow]) // eslint-disable-line react-hooks/exhaustive-deps

  // when a line appears: grow its bar and fly its amount into the matching card
  useEffect(() => {
    if (!shown) return
    const i = shown - 1
    const g = setTimeout(() => setGrown(shown), 80)
    const line = lines[i]
    const from = amountRefs.current[i]
    const target = document.querySelector(`[data-fly="${line?.target_id}"]`)
    if (!line || !from || !target || reduced()) return () => clearTimeout(g)
    const a = from.getBoundingClientRect()
    const b = target.getBoundingClientRect()
    const chip = document.createElement('div')
    chip.className = 'fixed z-[95] pointer-events-none rounded-full bg-emerald-400 text-[#06281b] font-bold text-sm px-3 py-1 num shadow-glow'
    chip.textContent = hidden ? '••••' : `+${uzs(line.amount)}`
    chip.style.left = `${a.left}px`
    chip.style.top = `${a.top}px`
    document.body.appendChild(chip)
    const dx = b.left + b.width / 2 - a.left - chip.offsetWidth / 2
    const dy = Math.max(0, b.top) + 14 - a.top
    const anim = chip.animate([
      { transform: 'translate(0,0) scale(1)', opacity: 1 },
      { transform: `translate(${dx * 0.5}px,${dy * 0.55 - 40}px) scale(1.1)`, opacity: 1, offset: 0.55 },
      { transform: `translate(${dx}px,${dy}px) scale(.55)`, opacity: 0 },
    ], { duration: FLY_MS, easing: 'cubic-bezier(.3,.7,.4,1)' })
    anim.onfinish = () => {
      chip.remove()
      target.animate([{ filter: 'brightness(1)' }, { filter: 'brightness(1.6)' }, { filter: 'brightness(1)' }],
        { duration: 420, easing: 'ease-out' })
    }
    return () => { clearTimeout(g); anim.cancel(); chip.remove() }
  }, [shown]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!flow) return null
  const shortfalls = flow.shortfalls || []

  return createPortal(
    <div className="fixed inset-0 z-[90] flex items-end justify-center" role="dialog" aria-modal="true" aria-label={t('bdTitle')}
      onClick={() => onClose?.()}>
      {/* light dim only: the card stack above must stay visible while amounts fly into it */}
      <div className="absolute inset-0 bg-black/25 animate-fade-in" />
      <div className="relative w-full max-w-[420px] animate-sheet-up cursor-pointer">
        <div className="bg-card border-t border-line rounded-t-[28px] shadow-soft px-5 pt-3 pb-6">
          <div className="mx-auto h-1.5 w-11 rounded-full bg-white/20 mb-3" />
          <div className="flex items-center gap-3">
            <span className="w-10 h-10 shrink-0 rounded-full bg-emerald-400/15 text-emerald-300 grid place-items-center">
              <Icon name="sparkle" fill strokeWidth={0} size={20} />
            </span>
            <div className="min-w-0">
              <p className="font-bold text-lg leading-tight">{t('bdTitle')}</p>
              <p className="text-muted text-sm">{t('bdIn')}: <Money value={flow.salary} className="text-emerald-300 font-semibold" /></p>
            </div>
          </div>

          <ol className="mt-4 space-y-2.5">
            {lines.map((l, i) => i < shown && (
              <li key={`${l.type}-${l.target_id}`} className="animate-rise rounded-[14px] bg-card2 border border-line px-3 py-2.5">
                <div className="flex items-center justify-between gap-3">
                  <span className="flex items-center gap-2 min-w-0">
                    <span className="w-7 h-7 shrink-0 rounded-full bg-white/10 grid place-items-center text-sm">
                      {l.type === 'obligation' ? '🛡' : l.type === 'goal' ? l.priority : <Icon name="pay" size={16} />}
                    </span>
                    <span className="min-w-0">
                      <span className="block font-semibold truncate">{l.label}</span>
                      <span className="block text-xs text-muted">
                        {l.type === 'obligation' ? t('bdObl') : l.type === 'goal' ? t('bdGoal', l.priority, l.percent) : t('bdMain')}
                      </span>
                    </span>
                  </span>
                  <span ref={(el) => { amountRefs.current[i] = el }} className="shrink-0 font-bold text-emerald-300">
                    +<Money value={l.amount} />
                  </span>
                </div>
                {l.type !== 'main' && (
                  <Progress className="mt-2 !h-1.5" tone={l.type === 'obligation' ? 'amber' : 'green'}
                    value={grown > i ? l.progress_after : l.progress_before} />
                )}
              </li>
            ))}
          </ol>

          {shortfalls.length > 0 && shown >= lines.length && (
            <div className="mt-3 space-y-1 animate-rise">
              {shortfalls.map((s) => (
                <p key={s.id} className="text-sm text-amber-200">⚠ {t('salaryShort', s.name, uzs(s.shortfall))}</p>
              ))}
            </div>
          )}
          <p className="mt-4 text-center text-xs text-muted">{t('bdTap')}</p>
        </div>
      </div>
    </div>,
    document.body,
  )
}

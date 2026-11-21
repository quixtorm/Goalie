import { useRef } from 'react'
import { useApp } from '../ctx'
import { amountParts, dateShort } from '../format'
import { Icon } from './ui'

// Premium palettes by priority. Deep enough for white text (contrast >= 4.5:1 at the darkest text areas).
export const PALETTES = {
  1: { bg: 'linear-gradient(135deg,#053B2F 0%,#047857 52%,#0F766E 100%)', tint: '#06483A', glow: '52,211,153' },
  2: { bg: 'linear-gradient(135deg,#2E0A5C 0%,#5B21B6 50%,#3730A3 100%)', tint: '#3A1475', glow: '167,139,250' },
  3: { bg: 'linear-gradient(135deg,#7C2D12 0%,#B45309 48%,#C2410C 100%)', tint: '#7A3110', glow: '251,191,36' },
  main: { bg: 'linear-gradient(135deg,#0A1640 0%,#1E3A8A 52%,#2563EB 100%)', tint: '#0F2463', glow: '96,165,250' },
  done: { bg: 'linear-gradient(135deg,#052E16 0%,#166534 50%,#4D7C0F 100%)', tint: '#0B3B1E', glow: '134,239,172' },
}
export const paletteFor = (priority) => PALETTES[priority] || PALETTES[3]

const NOISE = "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='3' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 .55 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>\")"

const canTilt = () => typeof window !== 'undefined' && window.matchMedia?.('(hover: hover) and (pointer: fine)').matches

// Small 3D tilt on desktop only (max 6deg), transform-only so it stays at 60fps.
function useTilt(enabled) {
  const ref = useRef(null)
  if (!enabled) return { ref, handlers: {} }
  return {
    ref,
    handlers: {
      onPointerMove: (e) => {
        if (e.pointerType !== 'mouse' || !canTilt() || !ref.current) return
        const r = ref.current.getBoundingClientRect()
        const x = (e.clientX - r.left) / r.width - 0.5
        const y = (e.clientY - r.top) / r.height - 0.5
        ref.current.style.transform = `perspective(900px) rotateX(${(-y * 12).toFixed(2)}deg) rotateY(${(x * 12).toFixed(2)}deg)`
      },
      onPointerLeave: () => { if (ref.current) ref.current.style.transform = '' },
    },
  }
}

function Chip() {
  return (
    <svg viewBox="0 0 40 30" className="w-full h-auto drop-shadow" aria-hidden>
      <defs>
        <linearGradient id="chipg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#F8E3A3" /><stop offset=".45" stopColor="#D6A84A" /><stop offset="1" stopColor="#9C7424" />
        </linearGradient>
      </defs>
      <rect x="1" y="1" width="38" height="28" rx="6" fill="url(#chipg)" stroke="#7a5a1c" strokeOpacity=".5" />
      <path d="M1 10h11a3 3 0 0 1 3 3v4a3 3 0 0 1-3 3H1M39 10H28a3 3 0 0 0-3 3v4a3 3 0 0 0 3 3h11M15 1v9M25 1v9M15 29v-9M25 29v-9"
        fill="none" stroke="#6b4e16" strokeOpacity=".55" strokeWidth="1.2" />
    </svg>
  )
}

function NetworkMark() {
  return (
    <div className="relative flex items-center" style={{ width: '13cqw', height: '8cqw' }} aria-hidden>
      <span className="absolute left-0 rounded-full bg-white/80" style={{ width: '8cqw', height: '8cqw' }} />
      <span className="absolute right-0 rounded-full bg-white/45 mix-blend-screen" style={{ width: '8cqw', height: '8cqw' }} />
      <span className="absolute inset-0 grid place-items-center font-black text-[#0b1530]/80 tracking-tighter" style={{ fontSize: '3.6cqw' }}>G</span>
    </div>
  )
}

/**
 * One card component for the main card, goal subcards and the "add" ghost slot.
 *  kind: 'goal' | 'main' | 'ghost'
 *  goal: goal view from /state (name, saved, amount, percent, expiry, progress, status)
 *  priority: shown badge (overrides goal.priority, used for live drag preview)
 *  cooling: { hoursLeft } when a purchase from this goal is on 24h cooling-off
 */
export default function BankCard({ kind = 'goal', goal, priority, main, cooling, onUse, onClick, label, tilt = true, className = '', style }) {
  const { t, lang, hidden } = useApp()
  const { ref, handlers } = useTilt(tilt && kind !== 'ghost')

  if (kind === 'ghost') {
    return (
      <button onClick={onClick} className={`press relative w-full rounded-[20px] border-2 border-dashed border-white/30 bg-[#181B22] hover:bg-[#1F232B] text-white/85 shadow-[0_12px_30px_-12px_rgba(0,0,0,.7)] ${className}`}
        style={{ aspectRatio: '85.6 / 53.98', containerType: 'inline-size', ...style }} aria-label={label || t('addSubcard')}>
        <span className="absolute inset-x-0 top-0 flex items-center gap-2 font-semibold" style={{ padding: '3.4cqw 4.6cqw', fontSize: '4.2cqw' }}>
          <Icon name="plus" size={18} /> {label || t('addSubcard')}
        </span>
        <span className="absolute inset-0 grid place-items-center">
          <span className="grid place-items-center rounded-full bg-white/10 border border-white/20" style={{ width: '14cqw', height: '14cqw' }}>
            <Icon name="plus" size={26} />
          </span>
        </span>
      </button>
    )
  }

  const isMain = kind === 'main'
  const prio = priority ?? goal?.priority
  const progress = isMain ? null : Math.min(100, goal?.progress ?? 0)
  const completed = !isMain && (goal?.status === 'completed' || (goal?.amount > 0 && goal?.saved >= goal?.amount))
  const p = isMain ? PALETTES.main : (completed && !prio) ? PALETTES.done : paletteFor(prio || 3)
  const near = !isMain && !completed && progress >= 90
  const title = isMain ? t('cardMain') : (goal?.name || t('newGoal'))
  const watermark = (isMain ? 'GOALIE' : (goal?.name || '•••')).toUpperCase()
  const amount = isMain ? main?.balance : goal?.saved
  const parts = amountParts(amount)

  const glow = completed
    ? `0 0 0 2px rgba(110,231,183,.9), 0 0 28px 4px rgba(52,211,153,.45), 0 22px 40px -14px rgba(0,0,0,.7)`
    : near
      ? `0 0 26px 2px rgba(${p.glow},.45), 0 22px 40px -14px rgba(0,0,0,.7)`
      : '0 22px 40px -14px rgba(0,0,0,.75), 0 4px 10px rgba(0,0,0,.25)'

  return (
    <div className={`relative w-full ${className}`} style={{ containerType: 'inline-size', ...style }}>
      <div ref={ref} {...handlers} onClick={onClick}
        className={`press relative w-full rounded-[20px] overflow-hidden text-white select-none transition-transform duration-150 ${onClick ? 'cursor-pointer' : ''}`}
        style={{ aspectRatio: '85.6 / 53.98', background: p.bg, boxShadow: glow, willChange: 'transform' }}
        role={onClick ? 'button' : undefined} tabIndex={onClick ? 0 : undefined}
        onKeyDown={onClick ? (e) => (e.key === 'Enter' || e.key === ' ') && onClick(e) : undefined}
        aria-label={onClick ? title : undefined}>
        {/* grain */}
        <div className="absolute inset-0 opacity-[0.10] mix-blend-overlay pointer-events-none" style={{ backgroundImage: NOISE }} />
        {/* glossy diagonal highlight */}
        <div className="absolute inset-0 pointer-events-none" style={{ background: 'linear-gradient(115deg, rgba(255,255,255,.14) 0%, rgba(255,255,255,.04) 32%, transparent 48%)' }} />
        {/* bottom shade keeps small text readable */}
        <div className="absolute inset-x-0 bottom-0 h-1/2 pointer-events-none" style={{ background: 'linear-gradient(to top, rgba(0,0,0,.28), transparent)' }} />

        {/* giant cropped watermark */}
        <div className="absolute pointer-events-none font-black leading-none whitespace-nowrap text-white/25 tracking-tight"
          style={{ top: '9cqw', left: '-1.5cqw', fontSize: '26cqw' }} aria-hidden>{watermark}</div>

        {/* top row: priority badge + title, status icon */}
        <div className="absolute inset-x-0 top-0 flex items-center gap-[2cqw]" style={{ padding: '3.2cqw 4.4cqw' }}>
          {!isMain && prio > 0 && (
            <span className="shrink-0 rounded-full bg-white/20 border border-white/30 backdrop-blur-sm font-bold" style={{ fontSize: '3.4cqw', padding: '0.5cqw 2.2cqw' }}>#{prio}</span>
          )}
          {isMain && <span className="shrink-0 rounded-full bg-white/20 border border-white/30 font-bold" style={{ fontSize: '3.2cqw', padding: '0.5cqw 2.2cqw' }}>UZS</span>}
          <span className="flex-1 min-w-0 truncate font-bold" style={{ fontSize: '4.4cqw' }}>{title}</span>
          {!isMain && (
            <span className="shrink-0 grid place-items-center rounded-full bg-black/20" style={{ width: '7cqw', height: '7cqw' }}
              aria-label={completed ? 'completed' : cooling ? 'cooling' : 'locked'}>
              <Icon name={completed ? 'check' : cooling ? 'snow' : 'lock'} size={14} strokeWidth={2.2} />
            </span>
          )}
        </div>

        {/* EMV chip + contactless */}
        <div className="absolute flex items-center gap-[2cqw]" style={{ left: '5.5cqw', top: '30cqw' }}>
          <div style={{ width: '10.5cqw' }}><Chip /></div>
          <Icon name="waves" size={18} className="text-white/80 rotate-0" />
        </div>

        {/* amount */}
        <div className="absolute font-semibold tracking-tight num" style={{ left: '5.5cqw', top: '38.5cqw', fontSize: '7.4cqw', lineHeight: 1 }}>
          {hidden ? '••••••' : <>{parts.int}<span style={{ fontSize: '4.4cqw' }}>{parts.dec}</span> <span style={{ fontSize: '4.6cqw' }}>so'm</span></>}
        </div>

        {/* bottom-left info */}
        <div className="absolute text-white/90" style={{ left: '5.5cqw', bottom: '5.2cqw', fontSize: '3.3cqw', lineHeight: 1.35 }}>
          {isMain ? (
            <>
              <div className="text-white/70">{t('freeToSpend')}</div>
              <div className="font-semibold num">{hidden ? '••••••' : `${amountParts(main?.free).int} so'm`}</div>
            </>
          ) : (
            <>
              <div>{goal?.expiry ? t('untilShort', dateShort(goal.expiry)) : '—'}</div>
              <div className="text-white/75">{t('pctIncomeShort', goal?.percent ?? 0)}</div>
            </>
          )}
        </div>

        {/* network mark */}
        <div className="absolute" style={{ right: '5cqw', bottom: '5.6cqw' }}><NetworkMark /></div>

        {/* completed CTA */}
        {completed && onUse && (
          <button onClick={(e) => { e.stopPropagation(); onUse() }}
            className="absolute rounded-full bg-emerald-300 text-emerald-950 font-bold shadow-lg press"
            style={{ right: '5cqw', top: '36cqw', fontSize: '3.6cqw', padding: '1.4cqw 3.6cqw' }}>
            {t('useChip')}
          </button>
        )}

        {/* progress line along the bottom edge */}
        {!isMain && (
          <>
            <div className="absolute inset-x-0 bottom-0 bg-white/15" style={{ height: '1.1cqw' }}>
              <div className={`h-full ${completed ? 'bg-emerald-300' : 'bg-lime-300'} transition-[width] duration-700`} style={{ width: `${progress}%` }} />
            </div>
            <div className="absolute font-bold text-white/90 num" style={{ right: '5cqw', bottom: '1.8cqw', fontSize: '2.8cqw' }}>{progress}%</div>
          </>
        )}

        {/* cooling-off frost */}
        {cooling && (
          // frost starts below the top row so the badge + name stay readable (also in the stacked strip)
          <div className="absolute inset-x-0 bottom-0 grid place-items-center bg-white/10 backdrop-blur-[3px]" style={{ top: '13cqw' }}>
            <div className="flex flex-col items-center gap-[1cqw] text-white drop-shadow">
              <Icon name="snow" size={34} />
              <span className="font-semibold" style={{ fontSize: '4cqw' }}>{t('coolingLeft', cooling.hoursLeft)}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

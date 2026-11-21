import { useApp } from '../ctx'
import { Icon } from './ui'

// Sticky header: the AI agent is reachable from every screen through the search field, sparkle or bell.
export default function Header() {
  const { t, state, openAgent, go } = useApp()
  const count = (state?.proposals_pending || []).filter((p) => p.origin === 'agent').length
  const round = 'press shrink-0 w-10 h-10 rounded-full grid place-items-center bg-white/15 hover:bg-white/25 text-white'
  return (
    <header className="sticky top-0 z-40 bg-gradient-to-r from-brand-dark via-[#164A9E] to-brand px-3 pt-4 pb-3">
      <div className="flex items-center gap-2">
        <button className={round} onClick={() => go('more')} aria-label={t('profile')}><Icon name="user" size={20} /></button>
        <button className="press flex-1 min-w-0 flex items-center gap-2 rounded-full bg-white/15 hover:bg-white/20 pl-3 pr-3 min-h-[44px] text-left text-white/90"
          onClick={() => openAgent({ focus: 'chat' })} aria-label={t('search')}>
          <Icon name="sparkle" size={20} fill strokeWidth={0} className="shrink-0 text-amber-200" />
          <span className="truncate text-[14px]">{t('search')}</span>
        </button>
        <button className={`${round} relative`} onClick={() => openAgent({ focus: 'inbox' })}
          aria-label={`${t('inbox')}: ${count}`}>
          <Icon name="bell" size={20} />
          {count > 0 && (
            <span className="absolute -top-0.5 -right-0.5 min-w-5 h-5 px-1 rounded-full bg-amber-400 text-[#1b1300] text-xs font-bold grid place-items-center">
              {count}
            </span>
          )}
        </button>
        <button className={round} onClick={() => go('more')} aria-label={t('more')}><Icon name="gear" size={20} /></button>
      </div>
    </header>
  )
}

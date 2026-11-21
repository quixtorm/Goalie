import { useApp } from '../ctx'
import { Icon } from './ui'

const TABS = [
  { key: 'home', icon: 'home', label: 'tabHome' },
  { key: 'payments', icon: 'pay', label: 'tabPayments' },
  { key: 'goals', icon: 'target', label: 'tabGoals' },
  { key: 'more', icon: 'menu', label: 'tabMore' },
]

export default function TabBar({ active }) {
  const { t, go } = useApp()
  return (
    <nav className="fixed bottom-3 left-1/2 -translate-x-1/2 z-40 w-[calc(100%-24px)] max-w-[396px] rounded-[24px] border border-line bg-card/90 backdrop-blur-md shadow-soft grid grid-cols-4 p-1.5">
      {TABS.map((tab) => {
        const on = active === tab.key
        return (
          <button key={tab.key} onClick={() => go(tab.key)} aria-current={on ? 'page' : undefined}
            className={`press flex flex-col items-center justify-center gap-0.5 min-h-[58px] rounded-[18px] text-[13px] font-medium transition-colors ${on ? 'bg-white/10 text-ink' : 'text-muted hover:text-ink'}`}>
            <Icon name={tab.icon} size={24} className={on ? 'text-brand-light' : ''} />
            {t(tab.label)}
          </button>
        )
      })}
    </nav>
  )
}

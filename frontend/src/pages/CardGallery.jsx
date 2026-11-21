import { useApp } from '../ctx'
import BankCard from '../components/BankCard'
import { BackButton } from '../components/ui'

// Storybook-like page: every card state on one screen (mock data, display only).
const base = { amount: 8_000_000, percent: 10, expiry: '2027-07-01', status: 'active', disciplined: true }
const SAMPLES = [
  { key: 'stLocked', goal: { ...base, name: 'Telefon', priority: 1, saved: 3_837_500, progress: 48 } },
  { key: 'stNear', goal: { ...base, name: 'Mashina', priority: 2, saved: 46_000_000, amount: 50_000_000, percent: 22, progress: 92, expiry: '2029-11-01' } },
  { key: 'stCompleted', goal: { ...base, name: 'Sayohat', priority: 3, saved: 5_000_000, amount: 5_000_000, progress: 100, status: 'completed' } },
  { key: 'stCooling', goal: { ...base, name: 'Telefon', priority: 1, saved: 3_837_500, progress: 48 }, cooling: { hoursLeft: 23 } },
]

export default function CardGallery() {
  const { t, go } = useApp()
  return (
    <div className="space-y-6 pt-4 pb-6">
      <BackButton onClick={() => go('more')} />
      <div>
        <h1 className="text-2xl font-bold">{t('gallery')}</h1>
        <p className="text-muted text-sm mt-1">{t('galleryHint')}</p>
      </div>
      <section className="space-y-2">
        <p className="text-sm text-muted">{t('cardMain')}</p>
        <BankCard kind="main" main={{ balance: 14_898_750, free: 14_898_750 }} />
      </section>
      {SAMPLES.map((s) => (
        <section key={s.key} className="space-y-2">
          <p className="text-sm text-muted">#{s.goal.priority} · {t(s.key)}</p>
          <BankCard goal={s.goal} cooling={s.cooling} onUse={s.goal.status === 'completed' ? () => {} : undefined} />
        </section>
      ))}
      <section className="space-y-2">
        <p className="text-sm text-muted">{t('stGhost')}</p>
        <BankCard kind="ghost" />
      </section>
    </div>
  )
}

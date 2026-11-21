import { useApp } from '../ctx'
import DemoPanel from '../components/DemoPanel'
import { Icon } from '../components/ui'
import { LANGS } from '../i18n'

export default function More() {
  const { state, t, lang, setLang, hidden, setHidden, go } = useApp()
  return (
    <div className="space-y-5 pt-4">
      <section className="card flex items-center gap-4">
        <span className="w-14 h-14 rounded-full bg-gradient-to-br from-brand to-brand-dark grid place-items-center text-white"><Icon name="user" size={28} /></span>
        <div>
          <p className="font-bold text-lg">{t('profile')}</p>
          <p className="text-muted text-sm">Goalie · UZS</p>
        </div>
      </section>

      <section className="card space-y-4">
        <div className="space-y-3">
          <span className="flex items-center gap-2 font-semibold"><Icon name="globe" size={20} /> {t('language')}</span>
          <div className="grid grid-cols-3 rounded-full bg-card2 border border-line p-1" role="radiogroup" aria-label={t('language')}>
            {LANGS.map(([k, l]) => (
              <button key={k} role="radio" aria-checked={lang === k} onClick={() => setLang(k)}
                className={`press rounded-full px-2 min-h-[40px] text-sm font-semibold ${lang === k ? 'bg-brand text-white' : 'text-muted'}`}>{l}</button>
            ))}
          </div>
        </div>
        <div className="flex items-center justify-between gap-3">
          <span className="flex items-center gap-2 font-semibold"><Icon name={hidden ? 'eyeOff' : 'eye'} size={20} /> {hidden ? t('show') : t('hide')}</span>
          <button role="switch" aria-checked={hidden} onClick={() => setHidden(!hidden)}
            className={`relative w-14 h-8 rounded-full transition-colors ${hidden ? 'bg-brand' : 'bg-white/15'}`}>
            <span className={`absolute top-1 w-6 h-6 rounded-full bg-white transition-all ${hidden ? 'left-7' : 'left-1'}`} />
          </button>
        </div>
      </section>

      <section className="card !p-4 flex gap-3">
        <Icon name="lock" className="shrink-0 text-emerald-300 mt-0.5" />
        <div>
          <p className="font-semibold">{t('security')}</p>
          <p className="text-muted text-sm mt-0.5">{t('securityText')}</p>
        </div>
      </section>

      {state.demo_mode && (
        <button className="press w-full card !p-4 flex items-center gap-3 text-left hover:bg-white/5" onClick={() => go('cards')}>
          <span className="w-11 h-11 rounded-[14px] bg-card2 grid place-items-center"><Icon name="pay" size={22} /></span>
          <span className="flex-1">
            <span className="block font-semibold">{t('gallery')}</span>
            <span className="text-muted text-sm">{t('galleryHint')}</span>
          </span>
          <Icon name="chevronR" size={20} className="text-muted" />
        </button>
      )}
      {state.demo_mode && <DemoPanel />}
    </div>
  )
}

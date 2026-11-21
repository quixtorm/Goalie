// Display only. The frontend never calculates money — it formats numbers the API returned.
const MONTHS = {
  ru: ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'],
  uz: ['yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun', 'iyul', 'avgust', 'sentabr', 'oktabr', 'noyabr', 'dekabr'],
  en: ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'],
}

export function uzs(n) {
  if (n === null || n === undefined) return '—'
  const s = Math.abs(Math.round(n)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
  return `${n < 0 ? '−' : ''}${s} so'm`
}

function pluralRu(n, one, few, many) {
  const a = Math.abs(n) % 100, b = a % 10
  if (b === 1 && a !== 11) return one
  if (b >= 2 && b <= 4 && (a < 12 || a > 14)) return few
  return many
}

const pluralEn = (n, one, many) => `${n} ${Math.abs(n) === 1 ? one : many}`
export const months = (n, lang = 'ru') =>
  lang === 'uz' ? `${n} oy` : lang === 'en' ? pluralEn(n, 'month', 'months') : `${n} ${pluralRu(n, 'месяц', 'месяца', 'месяцев')}`
export const days = (n, lang = 'ru') =>
  lang === 'uz' ? `${n} kun` : lang === 'en' ? pluralEn(n, 'day', 'days') : `${n} ${pluralRu(n, 'день', 'дня', 'дней')}`

export function date(iso, lang = 'ru', withYear = true) {
  if (!iso) return '—'
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number)
  const mon = MONTHS[lang][m - 1]
  if (lang === 'uz') return `${d}-${mon}${withYear ? ` ${y}` : ''}`
  if (lang === 'en') return `${mon} ${d}${withYear ? `, ${y}` : ''}`
  return `${d} ${mon}${withYear ? ` ${y}` : ''}`
}

export function dueText(n, lang = 'ru') {
  if (lang === 'uz') {
    if (n < 0) return "muddati o'tgan"
    if (n === 0) return 'bugun'
    if (n === 1) return 'ertaga'
    return `${n} kundan keyin`
  }
  if (lang === 'en') {
    if (n < 0) return 'overdue'
    if (n === 0) return 'today'
    if (n === 1) return 'tomorrow'
    return `in ${days(n, lang)}`
  }
  if (n < 0) return 'просрочено'
  if (n === 0) return 'сегодня'
  if (n === 1) return 'завтра'
  return `через ${days(n, lang)}`
}

// "3 837 500,00 so'm" split so the decimals can be drawn smaller (card style)
export function amountParts(n) {
  const v = Math.round(n || 0)
  return { int: `${v < 0 ? '−' : ''}${Math.abs(v).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ')}`, dec: ',00' }
}

// 1.07.2027
export function dateShort(iso) {
  if (!iso) return '—'
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number)
  return `${d}.${String(m).padStart(2, '0')}.${y}`
}

export const digitsOnly = (s) => Number(String(s).replace(/\D/g, '').slice(0, 13)) || 0
export const groupDigits = (n) => (n ? String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ' ') : '')

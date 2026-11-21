// Display only. The frontend never calculates money — it formats numbers the API returned.
const MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа',
  'сентября', 'октября', 'ноября', 'декабря']

export function uzs(n) {
  if (n === null || n === undefined) return '—'
  const s = Math.abs(Math.round(n)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
  return `${n < 0 ? '−' : ''}${s} so'm`
}

export function plural(n, one, few, many) {
  const a = Math.abs(n) % 100, b = a % 10
  if (b === 1 && a !== 11) return one
  if (b >= 2 && b <= 4 && (a < 12 || a > 14)) return few
  return many
}

export const months = (n) => `${n} ${plural(n, 'месяц', 'месяца', 'месяцев')}`
export const days = (n) => `${n} ${plural(n, 'день', 'дня', 'дней')}`

export function date(iso, withYear = true) {
  if (!iso) return '—'
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number)
  return `${d} ${MONTHS[m - 1]}${withYear ? ` ${y}` : ''}`
}

export function dueText(daysLeft) {
  if (daysLeft < 0) return 'просрочено'
  if (daysLeft === 0) return 'сегодня'
  if (daysLeft === 1) return 'завтра'
  return `через ${days(daysLeft)}`
}

export const digitsOnly = (s) => Number(String(s).replace(/\D/g, '').slice(0, 13)) || 0
export const groupDigits = (n) => (n ? String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ' ') : '')

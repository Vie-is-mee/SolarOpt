const fmt = (n: number, digits: number) => n.toLocaleString('vi-VN', {maximumFractionDigits: digits})

/** Money that reads at a glance: 850.000 đ · 21,9 triệu đ · 2,5 tỷ đ. Precision follows the magnitude. */
export function vnd(n: number, unit = 'đ') {
  const a = Math.abs(n), u = unit ? ' ' + unit : ''
  if (a >= 1e9) return `${fmt(n / 1e9, a >= 1e11 ? 1 : 2)} tỷ${u}`
  if (a >= 1e6) return `${fmt(n / 1e6, a >= 1e8 ? 0 : a >= 1e7 ? 1 : 2)} triệu${u}`
  return fmt(n, 0) + u
}

/** Full amount with thousands separators, for tooltips and exact entry. */
export const grouped = (n: number) => fmt(n, 0)

/** Digits typed into a money box ("21.924.000 đ" -> 21924000); empty -> null. */
export function parseDigits(text: string) {
  const digits = text.replace(/\D/g, '')
  return digits ? Number(digits) : null
}

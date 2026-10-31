import {useEffect, useRef, useState} from 'react'
import {grouped, parseDigits, vnd} from '../format'

/** Money box: digits are grouped while typing (21.924.000) and the badge reads the amount
 * in millions / billions (21,9 triệu đ) so long numbers stay readable. */
export function MoneyInput({label, value, onChange, unit = 'đ', help, placeholder, min = 0}: {
  label: string; value: number | null; onChange: (v: number | null) => void; unit?: string; help?: string; placeholder?: string; min?: number
}) {
  const ref = useRef<HTMLInputElement>(null), caret = useRef<number | null>(null)
  const [text, setText] = useState(value == null ? '' : grouped(value))
  useEffect(() => { if (document.activeElement !== ref.current) setText(value == null ? '' : grouped(value)) }, [value])
  useEffect(() => {
    // Keep the caret after the same number of digits once separators are re-inserted.
    const el = ref.current, digits = caret.current
    if (!el || digits == null) return
    let pos = 0, seen = 0
    while (pos < text.length && seen < digits) { if (/\d/.test(text[pos])) seen++; pos++ }
    el.setSelectionRange(pos, pos); caret.current = null
  }, [text])
  function edit(raw: string, at: number | null) {
    const v = parseDigits(raw)
    caret.current = at == null ? null : raw.slice(0, at).replace(/\D/g, '').length
    setText(v == null ? '' : grouped(v))
    onChange(v == null ? null : Math.max(min, v))
  }
  const badge = value != null && Math.abs(value) >= 1e6 ? vnd(value, unit) : unit
  return <label className="field money-field">
    <span>{label}</span>
    <div className="input-wrap"><input ref={ref} aria-label={label} inputMode="numeric" autoComplete="off" value={text} placeholder={placeholder ?? 'Chưa nhập'}
      onChange={e => edit(e.target.value, e.target.selectionStart)} onBlur={() => setText(value == null ? '' : grouped(value))}/><small title={value != null ? grouped(value) + ' ' + unit : undefined}>{badge}</small></div>
    {help && <em>{help}</em>}
  </label>
}

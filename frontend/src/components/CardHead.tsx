import type {ReactNode} from 'react'
import {Icon} from './Icon'

/** Same heading as App's Card: icon tile, title, one-line subtitle, optional action on the right. */
export function CardHead({icon, title, sub, action}: {icon: string; title: string; sub?: string; action?: ReactNode}) {
  return <div className="card-heading"><div className="card-title"><span className="card-icon"><Icon name={icon} size={18}/></span><div><h3>{title}</h3>{sub && <p>{sub}</p>}</div></div>{action}</div>
}

/** Missing inputs as a compact chip list instead of one long sentence. */
export function MissingList({title, items}: {title: string; items: string[]}) {
  return <div className="missing-list" role="status"><strong>{title} <span>{items.length} mục</span></strong><ul>{items.map(i => <li key={i}>{i}</li>)}</ul></div>
}

// Freehand pen: turns a pointer stroke into a smooth polygon with a bounded number of vertices.
type P = {x: number; y: number}
const dist = (a: P, b: P) => Math.hypot(a.x - b.x, a.y - b.y)

function segDist(p: P, a: P, b: P) {
  const dx = b.x - a.x, dy = b.y - a.y, len = dx * dx + dy * dy
  if (!len) return dist(p, a)
  const t = Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / len))
  return dist(p, {x: a.x + t * dx, y: a.y + t * dy})
}

/** Ramer–Douglas–Peucker: drop points closer than `tolerance` to the simplified line. */
export function simplify(points: P[], tolerance: number): P[] {
  if (points.length < 3) return points.slice()
  let index = 0, max = 0
  const a = points[0], b = points[points.length - 1]
  for (let i = 1; i < points.length - 1; i++) { const d = segDist(points[i], a, b); if (d > max) { max = d; index = i } }
  if (max <= tolerance) return [a, b]
  return [...simplify(points.slice(0, index + 1), tolerance).slice(0, -1), ...simplify(points.slice(index), tolerance)]
}

/** Chaikin corner cutting on an open stroke (end points kept) — removes hand jitter. */
export function chaikin(points: P[], iterations = 2): P[] {
  let out = points
  for (let k = 0; k < iterations && out.length > 2; k++) {
    const next: P[] = [out[0]]
    for (let i = 0; i < out.length - 1; i++) {
      const a = out[i], b = out[i + 1]
      next.push({x: .75 * a.x + .25 * b.x, y: .75 * a.y + .25 * b.y}, {x: .25 * a.x + .75 * b.x, y: .25 * a.y + .75 * b.y})
    }
    next.push(out[out.length - 1]); out = next
  }
  return out
}

/** Stroke -> smooth vertices: light simplify, smooth, then simplify again, raising the tolerance
 * until at most `maxPoints` remain. `px` is one screen pixel in drawing units. */
export function smoothStroke(stroke: P[], px: number, maxPoints: number): P[] {
  if (stroke.length < 3) return stroke.slice()
  const smooth = chaikin(simplify(stroke, px * 1.5), 2)
  let tolerance = px * 1.2, out = simplify(smooth, tolerance)
  while (out.length > maxPoints && tolerance < px * 400) { tolerance *= 1.4; out = simplify(smooth, tolerance) }
  return out
}

/** Total length of a stroke. */
export const strokeLength = (s: P[]) => s.reduce((sum, p, i) => i ? sum + dist(s[i - 1], p) : 0, 0)

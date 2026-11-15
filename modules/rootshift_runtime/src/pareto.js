// Exact Pareto filtering. Objectives stay in their own units — no composite score.
// spec: [{key, direction:'min'|'max', epsilon?}]. null/undefined = unknown => worst possible on that axis
// (an unknown can never make an option look better).
function val(item, o) {
  const v = item.objectives?.[o.key];
  if (v === null || v === undefined || Number.isNaN(v)) return o.direction === 'max' ? -Infinity : Infinity;
  return v;
}
/** a dominates b: no worse on every objective and strictly better (beyond epsilon) on at least one. */
export function dominates(a, b, spec) {
  let strictly = false;
  for (const o of spec) {
    const eps = o.epsilon ?? 1e-9;
    const va = val(a, o), vb = val(b, o);
    if (va === vb) continue; // handles Infinity ties
    const better = o.direction === 'max' ? va > vb + eps : va < vb - eps;
    const wors = o.direction === 'max' ? va < vb - eps : va > vb + eps;
    if (wors) return false;
    if (better) strictly = true;
  }
  return strictly;
}
export function paretoFront(items, spec) {
  const frontier = [], dominated = [];
  for (const it of items) {
    const by = items.filter((o) => o !== it && dominates(o, it, spec));
    if (by.length) dominated.push({ id: it.id, dominatedBy: by.map((x) => x.id) });
    else frontier.push(it.id);
  }
  return { frontier, dominated };
}
/** Per-objective values for one dominating/dominated pair, for the evidence trace. */
export function dominanceProof(a, b, spec) {
  return spec.map((o) => ({ objective: o.key, direction: o.direction, dominator: a.objectives?.[o.key] ?? null, dominated: b.objectives?.[o.key] ?? null }));
}

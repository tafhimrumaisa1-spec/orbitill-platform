// Pure UTC date helpers + sowing-window resolution. No dependencies.
export const MS_DAY = 86400000;
export const parseDate = (iso) => { const [y, m, d] = iso.split('-').map(Number); return new Date(Date.UTC(y, m - 1, d)); };
export const isoDate = (dt) => dt.toISOString().slice(0, 10);
export const addDays = (dt, n) => new Date(dt.getTime() + n * MS_DAY);
export const diffDays = (a, b) => Math.round((a.getTime() - b.getTime()) / MS_DAY); // a - b
const mdToDate = (md, year) => { const [m, d] = md.split('-').map(Number); return new Date(Date.UTC(year, m - 1, d)); };

/** Window = {start:'MM-DD', end:'MM-DD'}; end < start means it wraps the new year. */
export function windowInstance(win, year) {
  const start = mdToDate(win.start, year);
  const end = mdToDate(win.end, win.end < win.start ? year + 1 : year);
  return { start, end };
}

/**
 * Where can a crop be sown if the earliest the field is free is `earliest`?
 * ok=true  -> sow = max(earliest, window opening); waitedDays = fallow wait for the window to open.
 * ok=false -> the window was missed; lateByDays is measured against the most recent window close.
 */
export function resolveWindow(win, earliest, horizonEnd) {
  const y0 = earliest.getUTCFullYear();
  const inst = [];
  for (let y = y0 - 1; y <= y0 + 1; y++) inst.push(windowInstance(win, y));
  inst.sort((a, b) => a.start - b.start);
  const next = inst.find((i) => i.end >= earliest);
  const prev = [...inst].reverse().find((i) => i.end < earliest);
  if (next && next.start <= horizonEnd) {
    const sow = next.start > earliest ? next.start : earliest;
    return { ok: true, sow, window: next, slackDays: diffDays(next.end, sow), waitedDays: diffDays(sow, earliest) };
  }
  return { ok: false, sow: earliest, window: prev || null, lateByDays: prev ? diffDays(earliest, prev.end) : null, nextOpens: next ? next.start : null };
}

/** Days of [start, endExclusive) falling in each calendar month, keyed 'YYYY-MM'. */
export function daysByMonth(start, endExclusive) {
  const out = {};
  for (let t = start.getTime(); t < endExclusive.getTime(); t += MS_DAY) {
    const k = new Date(t).toISOString().slice(0, 7);
    out[k] = (out[k] || 0) + 1;
  }
  return out;
}
export const daysInMonth = (key) => { const [y, m] = key.split('-').map(Number); return new Date(Date.UTC(y, m, 0)).getUTCDate(); };

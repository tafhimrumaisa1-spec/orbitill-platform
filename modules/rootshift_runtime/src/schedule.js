// Sequence scheduling + candidate generation. Exact enumeration (tiny search space) — see METHODOLOGY.md.
import { parseDate, addDays, diffDays, resolveWindow, isoDate } from './calendar.js';

export const MODEL_VERSION = 'rootshift-0.1.0';
export const candidateId = (ids) => ids.join('>');

/** Plan one slot: earliest feasible sowing at or after the window opens. Never throws; violations are reported by SoilBrain. */
export function planSlot(crop, earliestFree, horizonEnd, durationDays) {
  const resolution = resolveWindow(crop.window, earliestFree, horizonEnd);
  const sow = resolution.sow;
  const dur = durationDays ?? crop.durationDays;
  return { crop, sow, harvest: addDays(sow, dur), durationDays: dur, resolution, fixed: false };
}

/** Fixed current-season slot from farmer-reported planting. Already-happened facts are not "violations"; they get a soft note. */
export function currentSlot(farm, pack, delayDays = 0) {
  const cc = farm.currentCrop;
  const crop = pack.crops[cc.cropId];
  if (!crop) return { error: 'unknown_current_crop' };
  const planted = addDays(parseDate(cc.plantedOn), delayDays);
  const dur = cc.durationDays ?? crop.durationDays;
  const r = resolveWindow(crop.window, planted, parseDate(farm.horizon.end));
  const inside = r.ok && r.waitedDays === 0;
  const resolution = inside ? r : { ok: true, sow: planted, window: r.window, slackDays: null, waitedDays: 0, outsideWindow: true };
  return { crop, sow: planted, harvest: addDays(planted, dur), durationDays: dur, resolution, fixed: true };
}

/** Build dated slots for an ordered crop list. Returns {slots, structural:[{code,params}]} */
export function scheduleSequence(cropIds, farm, pack, { delayDays = 0 } = {}) {
  const horizonEnd = parseDate(farm.horizon.end), horizonStart = parseDate(farm.horizon.start);
  const turn = pack.region.turnaroundDays;
  const slots = [], structural = [];
  let ids = [...cropIds];
  if (farm.currentCrop) {
    if (ids[0] !== farm.currentCrop.cropId) structural.push({ code: 'must_start_with_current_crop', params: { expected: farm.currentCrop.cropId, got: ids[0] } });
    const s = currentSlot(farm, pack, delayDays);
    if (s.error) return { slots, structural: [{ code: s.error, params: {} }] };
    slots.push(s); ids = ids.slice(1);
  }
  for (const id of ids) {
    const crop = pack.crops[id];
    if (!crop) { structural.push({ code: 'unknown_crop_in_pack', params: { crop: id } }); continue; }
    const prev = slots[slots.length - 1];
    const earliest = prev ? addDays(prev.harvest, turn) : horizonStart;
    slots.push(planSlot(crop, earliest, horizonEnd));
  }
  for (const s of slots) if (s.harvest > horizonEnd) structural.push({ code: 'exceeds_horizon', params: { crop: s.crop.id, harvest: isoDate(s.harvest), horizonEnd: farm.horizon.end, overByDays: diffDays(s.harvest, horizonEnd) } });
  return { slots, structural };
}

/** Enumerate every maximal date-feasible sequence (<= maxCrops, no repeats of a crop within the horizon). */
export function enumerateSequences(farm, pack, { maxCrops = 3, delayDays = 0 } = {}) {
  const horizonEnd = parseDate(farm.horizon.end), horizonStart = parseDate(farm.horizon.start);
  const turn = pack.region.turnaroundDays;
  const out = [];
  const crops = Object.values(pack.crops);
  const dfs = (slots) => {
    let extended = false;
    if (slots.length < maxCrops) {
      const prev = slots[slots.length - 1];
      for (const c of crops) {
        if (slots.some((s) => s.crop.id === c.id)) continue;
        if (c.isCover && !prev) continue;
        const slot = planSlot(c, prev ? addDays(prev.harvest, turn) : horizonStart, horizonEnd);
        if (!slot.resolution.ok || slot.harvest > horizonEnd) continue;
        extended = true; dfs([...slots, slot]);
      }
    }
    if (!extended && slots.length) out.push(slots.map((s) => s.crop.id));
  };
  if (farm.currentCrop) {
    const s = currentSlot(farm, pack, delayDays);
    if (!s.error) dfs([s]);
  } else dfs([]);
  return out;
}

/** Union of: farmer baseline, region templates, reference fallow, and all maximal enumerated sequences. */
export function generateRotationCandidates(farm, pack, opts = {}) {
  const seen = new Map();
  const add = (ids, kind, label) => { const id = candidateId(ids); if (!seen.has(id)) seen.set(id, { id, cropIds: ids, kind, label }); else if (kind === 'baseline') seen.get(id).kind = 'baseline'; };
  const base = farm.baselineRotation ?? pack.defaultBaseline;
  add(base, 'baseline', 'Current rotation');
  for (const t of pack.templates) add(t, 'template', 'Region template');
  if (pack.referenceFallow?.length) add(pack.referenceFallow, 'reference_fallow', 'Single crop, then fallow (reference)');
  for (const s of enumerateSequences(farm, pack, opts)) add(s, 'enumerated', 'Enumerated feasible sequence');
  const list = [...seen.values()];
  for (const c of list) c.isBaseline = c.id === candidateId(base);
  return list;
}

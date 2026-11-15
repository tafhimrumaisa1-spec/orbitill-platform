// FIXTURE implementations of services owned by other agents. RootShift core only depends on the
// service SHAPES below; swap these for the real modules at integration. Every response carries
// `provider: 'fixture:<agent>'` so the UI/evidence layer can show live-vs-fixture status.
import { parseDate, addDays, diffDays, resolveWindow, daysByMonth, daysInMonth } from '../calendar.js';

// ---------- Agent 05 (SoilBrain): crop/season rule checks ----------
export const soilBrainFixture = {
  provider: 'fixture:agent05-soilbrain',
  /** @returns {{status:'ok'|'violation'|'conditional', hard:Array, soft:Array, missing:string[]}} */
  evaluateCropFeasibility({ crop, sow, resolution, harvest, farm, region, previousCropId, packs }) {
    const hard = [], soft = [], missing = [];
    if (!crop.regionIds.includes(region.id)) {
      hard.push({ code: 'crop_not_valid_in_region', params: { crop: crop.id, region: region.id, validIn: crop.regionIds } });
    }
    if (!resolution.ok) {
      hard.push({ code: 'sowing_window_missed', params: { crop: crop.id, earliestFree: sow.toISOString().slice(0, 10), lateByDays: resolution.lateByDays, windowEnd: resolution.window?.end?.toISOString().slice(0, 10) ?? null } });
    } else if (resolution.slackDays <= 7) {
      soft.push({ code: 'late_in_window', params: { crop: crop.id, slackDays: resolution.slackDays } });
    }
    if (previousCropId) {
      const prev = packs[region.pack]?.crops[previousCropId];
      if (prev && prev.family === crop.family && !crop.rice && !prev.rice) {
        soft.push({ code: 'same_family_consecutive', params: { crop: crop.id, previous: previousCropId, family: crop.family } });
      }
    }
    if (crop.needsTexture && !farm.soil?.texture) missing.push('soil_texture');
    return { status: hard.length ? 'violation' : missing.length ? 'conditional' : 'ok', hard, soft, missing };
  },
};

// ---------- Agent 04 (EarthSync): environmental series ----------
export const earthSyncFixture = {
  provider: 'fixture:agent04-earthsync',
  /** Returns null when no climate series exists for the region -> RootShift must refuse a confident answer. */
  getEnvironmentalSeries({ region, packs, simulateMissing = false }) {
    if (simulateMissing) return null;
    const pack = packs[region.pack];
    if (!pack?.climate) return null;
    return {
      kind: 'monthly_climatology', rainMm: pack.climate.rainMm, et0MmDay: pack.climate.et0MmDay,
      observationType: 'hypothetical scenario', // fixture stand-in, NOT an observation
      evidenceId: region.iso === 'BD' ? 'ev:fixture-climate-bd' : 'ev:fixture-us',
      intendedSource: 'ev:nasa-power', native: 'POWER ~0.5 deg daily grid (not wired)',
    };
  },
};

// ---------- Agent 06 (AquaSense): irrigation water balance ----------
const peffScs = (p) => (p <= 250 ? (p * (125 - 0.2 * p)) / 125 : 125 + 0.1 * p);
const peffFor = (crop, p) => (crop.rice ? 0.8 * p : peffScs(p));

export const aquaSenseFixture = {
  provider: 'fixture:agent06-aquasense',
  /**
   * Monthly water balance with capped carry-over storage.
   * Demand = ETc (Kc*ET0) [+ percolation + land-prep for flooded rice]. Irrigation need = unmet demand.
   * If an annual allowance is given, need is rationed pro-rata across slots and a relative deficit is returned.
   */
  evaluateWaterBalance({ slots, climate, scenario = {}, irrigationAvailableMm, soilWaterAtSowingMm = null }) {
    if (!climate) return { status: 'no_climate', perSlot: [], totalNeedMm: null };
    const rainMult = scenario.rainfallMultiplier ?? 1;
    const rain = climate.rainMm.map((r) => r * rainMult);
    const perSlot = slots.map((s) => {
      const crop = s.crop;
      const months = daysByMonth(s.sow, s.harvest);
      let storage = crop.rice ? 0 : (soilWaterAtSowingMm ?? 0);
      let etc = 0, perc = 0, need = 0, rainEff = 0;
      // land preparation met by effective rain in the 15 days before transplanting (flooded rice only)
      let prep = 0;
      if (crop.rice) {
        const pre = daysByMonth(addDays(s.sow, -15), s.sow);
        let prepRain = 0;
        for (const [k, d] of Object.entries(pre)) prepRain += (peffFor(crop, rain[Number(k.slice(5)) - 1]) / daysInMonth(k)) * d;
        prep = crop.landPrepMm;
        need += Math.max(0, prep - prepRain);
        rainEff += Math.min(prep, prepRain);
      }
      for (const [k, d] of Object.entries(months)) {
        const m = Number(k.slice(5)) - 1;
        const e = crop.kc * climate.et0MmDay[m] * d;
        const p = crop.rice ? crop.percMmPerDay * d : 0;
        const pe = (peffFor(crop, rain[m]) * d) / daysInMonth(k);
        const demand = e + p;
        const avail = storage + pe;
        if (avail >= demand) storage = Math.min(crop.storageCapMm ?? 0, avail - demand);
        else { need += demand - avail; storage = 0; }
        etc += e; perc += p; rainEff += pe;
      }
      const gross = etc + perc + prep;
      return { cropId: crop.id, etcMm: +etc.toFixed(1), percolationMm: +perc.toFixed(1), landPrepMm: prep, effectiveRainMm: +rainEff.toFixed(1), irrigationNeedMm: +need.toFixed(1), grossDemandMm: +gross.toFixed(1) };
    });
    const totalNeedMm = +perSlot.reduce((a, s) => a + s.irrigationNeedMm, 0).toFixed(1);
    let status = 'ok', scale = 1;
    if (irrigationAvailableMm === null || irrigationAvailableMm === undefined) status = 'allowance_unknown';
    else if (totalNeedMm > irrigationAvailableMm) { status = 'constrained'; scale = totalNeedMm > 0 ? irrigationAvailableMm / totalNeedMm : 1; }
    const out = perSlot.map((s) => {
      if (status === 'allowance_unknown') {
        return { ...s, allocatedMm: null, shortfallMm: null, relativeDeficit: null };
      }
      const allocated = +(s.irrigationNeedMm * scale).toFixed(1);
      const shortfall = +(s.irrigationNeedMm - allocated).toFixed(1);
      return { ...s, allocatedMm: allocated, shortfallMm: shortfall, relativeDeficit: s.grossDemandMm > 0 ? Math.min(1, shortfall / s.grossDemandMm) : 0 };
    });
    const shortfallMm = status === 'allowance_unknown' ? null : +out.reduce((a, s) => a + s.shortfallMm, 0).toFixed(1);
    return { status, perSlot: out, totalNeedMm, allowanceMm: irrigationAvailableMm ?? null, shortfallMm, method: 'ETc=Kc*ET0 (FAO-56 season-average Kc); SCS/80% effective rain; monthly balance; pro-rata rationing' };
  },
};

// ---------- Agent 08 (AgriEconomics): indicative margins ----------
export const agriEconomicsFixture = {
  provider: 'fixture:agent08-agrieconomics',
  /** FAO-33 linear response Ya/Ym = 1 - Ky*(relative deficit). Margin per ha, in pack currency. */
  calculateEconomics({ slots, water, pack, scenario = {} }) {
    const e = pack.economics, pm = scenario.priceMultiplier ?? 1;
    const perSlot = slots.map((s, i) => {
      const c = e.crops[s.crop.id];
      const w = water?.perSlot?.[i];
      if (!c) return { cropId: s.crop.id, missing: ['economics_row'] };
      if (w && w.relativeDeficit === null) return { cropId: s.crop.id, missing: ['irrigation_allowance'] };
      const yf = w ? Math.max(0, 1 - s.crop.ky * w.relativeDeficit) : 1;
      const revFull = c.yieldTHa * 1000 * c.priceBdtKg * pm;
      const irrCostLimited = (w?.allocatedMm ?? 0) * e.irrigationCostPerMmHa;
      const irrCostFull = (w?.irrigationNeedMm ?? 0) * e.irrigationCostPerMmHa;
      return {
        cropId: s.crop.id, yieldFactor: +yf.toFixed(3),
        revenuePerHa: Math.round(revFull * yf), costPerHa: Math.round(c.costBdtHa + irrCostLimited),
        marginWaterLimitedPerHa: Math.round(revFull * yf - c.costBdtHa - irrCostLimited),
        marginUnconstrainedPerHa: Math.round(revFull - c.costBdtHa - irrCostFull),
      };
    });
    const missing = perSlot.flatMap((p) => p.missing ?? []);
    const sum = (k) => (missing.length ? null : perSlot.reduce((a, p) => a + p[k], 0));
    return { currency: e.currency, status: e.status, evidence: e.evidence, perSlot, totalMarginWaterLimitedPerHa: sum('marginWaterLimitedPerHa'), totalMarginUnconstrainedPerHa: sum('marginUnconstrainedPerHa'), missing, method: 'yield x price - non-irrigation cost - pumped irrigation (cost per mm); FAO-33 linear yield response' };
  },
};

export const defaultServices = { soilBrain: soilBrainFixture, earthSync: earthSyncFixture, aquaSense: aquaSenseFixture, agriEconomics: agriEconomicsFixture };

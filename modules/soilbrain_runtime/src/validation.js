export function isValidIsoDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value ?? '')) return false;
  const [year, month, day] = value.split('-').map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day;
}

export function isValidMonthDay(value) {
  if (!/^\d{2}-\d{2}$/.test(value ?? '')) return false;
  return isValidIsoDate(`2000-${value}`);
}

export function validateInput(input) {
  const errors = [];
  if (!input || typeof input !== 'object') return ['input must be an object'];
  if (!input.regionId) errors.push('regionId is required');
  if (!input.cropId) errors.push('cropId is required');
  if (!isValidIsoDate(input.proposedSowingDate)) errors.push('proposedSowingDate must be a real ISO date (YYYY-MM-DD)');
  const ph = input.soil?.ph?.value;
  if (ph !== undefined && (!Number.isFinite(ph) || ph < 0 || ph > 14)) errors.push('soil.ph.value must be finite and between 0 and 14');
  const salinity = input.soil?.salinityDsM?.value;
  if (salinity !== undefined && (!Number.isFinite(salinity) || salinity < 0)) errors.push('soil.salinityDsM.value must be a finite non-negative number');
  return errors;
}

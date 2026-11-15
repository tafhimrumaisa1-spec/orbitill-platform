// Presentation layer only. The scientific model remains in planner.js and the API.
const byId = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = value => Number.isFinite(value) ? new Intl.NumberFormat('en', {maximumFractionDigits:1}).format(value) : 'Unavailable';
const rain = byId('rainfall'), water = byId('allowance');
function syncScenario(){byId('overview-rainfall').textContent = `${rain.value}% rainfall`;byId('overview-allowance').textContent = `${water.value} mm seasonal irrigation allowance`;}
rain.addEventListener('input',syncScenario);water.addEventListener('input',syncScenario);syncScenario();
function updateFieldOverview(data){
  byId('overview-status').textContent='Comparison ready';
  byId('overview-pathways').innerHTML = data.results.map((item,i)=>`<article class="overview-pathway"><div><span>PATHWAY ${i+1} · ${esc(item.label)}</span><strong>${esc(item.rotation)}</strong><small>${esc(item.status)}</small></div><div><strong>${fmt(item.irrigation_gross_mm)} mm</strong><small>modeled irrigation · not actual use</small></div></article>`).join('');
}
window.addEventListener('orbitill:model-ready',event=>updateFieldOverview(event.detail));
if(window.__orbitillLastComparison)updateFieldOverview(window.__orbitillLastComparison);
window.addEventListener('orbitill:model-error',()=>{byId('overview-status').textContent='Model unavailable';byId('overview-pathways').textContent='The scientific API could not be reached. No substitute results are shown.';});

// Only the declared Barind research region is supported by this Command Center.
const selectedRegion=new URLSearchParams(location.search).get('region');
if(selectedRegion && selectedRegion!=='BD-RAJ-BARIND') {
  location.replace('start.html#choose-region');
}

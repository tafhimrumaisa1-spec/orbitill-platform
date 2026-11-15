const rainfall = document.querySelector('#rainfall');
const allowance = document.querySelector('#allowance');
const runButton = document.querySelector('#run-model');
const results = document.querySelector('#results');
const runId = document.querySelector('#run-id');
const runState = document.querySelector('#run-state');
const evidenceDetails = document.querySelector('#evidence-details');
const dialog = document.querySelector('#evidence-dialog');
const dialogContent = document.querySelector('#dialog-content');
let latest = null;

document.querySelector('[data-back]').addEventListener('click', () => history.length > 1 ? history.back() : location.assign('bangladesh.html'));
document.querySelector('[data-close]').addEventListener('click', () => dialog.close());
dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
rainfall.addEventListener('input', updateOutputs);
allowance.addEventListener('input', updateOutputs);
runButton.addEventListener('click', runComparison);
updateOutputs();
runComparison();

function updateOutputs(){
  document.querySelector('#rain-output').textContent = `${rainfall.value}%`;
  document.querySelector('#water-output').textContent = `${allowance.value} mm`;
}

async function runComparison(){
  runButton.disabled = true;
  runState.innerHTML = '<i></i> Recomputing from NASA evidence';
  results.innerHTML = '<div class="loading-card">Running all three pathways with the same changed assumptions…</div>';
  try{
    const response = await fetch('/api/demo/barind/compare', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({rainfall_multiplier:Number(rainfall.value)/100, irrigation_allowance_mm:Number(allowance.value)})
    });
    const data = await response.json();
    if(!response.ok) throw new Error(data.message || 'The model request was refused.');
    latest = data;
    render(data);
  }catch(error){
    latest = null;
    runState.textContent = 'Model unavailable';
    runId.textContent = 'No result';
    results.innerHTML = `<div class="error-card"><strong>The scientific service is not running.</strong><p>${escapeHtml(error.message)}</p><p>Start the ORBITILL integration server; this page will not substitute precomputed numbers.</p></div>`;
    evidenceDetails.innerHTML = '<p>No evidence record is available because no model run completed.</p>';
  }finally{runButton.disabled=false;}
}

function render(data){
  runState.innerHTML = `<i></i> ${data.scenario.kind === 'hypothetical_stress_test' ? 'Hypothetical scenario complete' : 'Historical analogue complete'}`;
  runId.textContent = data.model_run_id;
  results.innerHTML = data.results.map((item,index) => `
    <article class="result-card ${index===0?'is-current':''}">
      <header><span>${escapeHtml(item.label)} · pathway ${String(index+1).padStart(2,'0')}</span><span class="status-pill">${escapeHtml(item.status)}</span></header>
      <h3>${escapeHtml(item.rotation)}</h3>
      <div class="metric"><span>Policy-simulated irrigation</span><strong>${number(item.irrigation_gross_mm)} mm</strong><small>gross seasonal depth · not observed use</small></div>
      <div class="metric"><span>NASA POWER rainfall in crop window</span><strong>${number(item.rain_mm)} mm</strong><small>${escapeHtml(item.planting_date)} → ${escapeHtml(item.season_end || 'unavailable')}</small></div>
      <footer><p>Calendar: ${escapeHtml(calendarLabel(item.calendar_status))}. A lower number does not establish suitability, yield or profit.</p><button class="evidence-open" type="button" data-result="${index}">Why this result?</button></footer>
    </article>`).join('');
  document.querySelectorAll('[data-result]').forEach(button => button.addEventListener('click', () => openEvidence(data.results[Number(button.dataset.result)])));
  evidenceDetails.innerHTML = `<p><b>Source:</b> ${escapeHtml(data.evidence.provider)}<br><b>Observed period:</b> ${escapeHtml(data.evidence.observed_period)}<br><b>Variables:</b> ${data.evidence.variables.map(escapeHtml).join(', ')}<br><b>Spatial support:</b> ${escapeHtml(data.evidence.native_support)}</p><p><a href="${data.evidence.source_url}" target="_blank" rel="noopener">Open NASA POWER ↗</a></p><p><b>Run:</b> <code>${escapeHtml(data.model_run_id)}</code></p>`;
}

function openEvidence(item){
  if(!latest) return;
  dialogContent.innerHTML = `<p class="section-number">WHY THIS RESULT?</p><h2 id="dialog-title">${escapeHtml(item.rotation)}</h2><dl><dt>Status</dt><dd>${escapeHtml(item.status)}</dd><dt>Model run</dt><dd><code>${escapeHtml(item.model_run_id)}</code></dd><dt>NASA evidence</dt><dd>${item.evidence_ids.map(escapeHtml).join(', ')}</dd><dt>Planting assumption</dt><dd>${escapeHtml(item.planting_date)}</dd><dt>Calendar basis</dt><dd>${escapeHtml(item.calendar_source)} · ${escapeHtml(item.calendar_status)}</dd><dt>Water policy</dt><dd>${escapeHtml(item.irrigation_policy)}</dd><dt>Potential crop ET</dt><dd>${number(item.potential_crop_et_mm)} mm</dd><dt>Rainfall</dt><dd>${number(item.rain_mm)} mm</dd><dt>Simulated irrigation</dt><dd>${number(item.irrigation_gross_mm)} mm</dd></dl><h3>Shared demonstration assumptions</h3><ul>${latest.assumptions.map(value=>`<li>${escapeHtml(value)}</li>`).join('')}</ul><h3>Limitations</h3><ul>${latest.limitations.map(value=>`<li>${escapeHtml(value)}</li>`).join('')}</ul>`;
  dialog.showModal();
}

function number(value){return Number.isFinite(value)?new Intl.NumberFormat('en',{maximumFractionDigits:1}).format(value):'Unavailable';}
function calendarLabel(value){return value==='published_reference_analogue'?'published regional analogue—not locally validated':'unverified planning assumption';}
function escapeHtml(value){return String(value??'').replace(/[&<>"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[char]));}

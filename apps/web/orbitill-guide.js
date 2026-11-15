/* ORBITILL contextual, cross-page tours. Presentation only: never changes science or API state. */
(()=>{
'use strict';
const KEY='orbitill-guide-v2'; const SEEN='orbitill-guide-invite-seen-v2';
const loc=location.pathname;const on=(suffix)=>loc.endsWith(suffix);const atHome=on('/')||on('/index.html');
const routes={home:'/',start:'/start.html',map:'/terralens/index.html',planner:'/planner.html?region=BD-RAJ-BARIND',science:'/explore.html?view=how-it-works'};
const walkthroughs={
  farmer:[
    {page:'start',anchor:'#choose-region',title:'Select a supported research region',description:'Start with Barind for the working agricultural Command Center. Other regions have exploration and evidence-readiness views only, not validated farm-level crop recommendations.'},
    {page:'map',anchor:'#pilot-list',title:'First, choose your research region',description:'TerraLens lets you explore locations. Select Barind for the supported crop-water demonstration. A map point does not establish an individual farm boundary.'},
    {page:'map',anchor:'#farmer-link',title:'Open Barind Command Center from TerraLens',description:'Review the selected region and evidence readiness. For this demonstration, choose the Barind research pilot; not every location has validated crop models.'},
    {page:'planner',anchor:'#command-center',title:'Your agricultural Command Center',description:'Start with one research region and a guided sequence: understand conditions, compare crop-water pathways, test assumptions and verify evidence.'},
    {page:'planner',anchor:'#field-overview',title:'See your field research overview',description:'This dashboard summarizes NASA weather coverage, scenario assumptions, model readiness and three calculated crop pathways. These are NOT measurements of your personal land.'},
    {page:'planner',anchor:'#soilbrain-panel',title:'Check soil evidence and water assumptions',description:'SoilBrain is partially integrated, with unverified field soil parameters. AquaSense uses the declared conditions to model water demand.'},
    {page:'planner',anchor:'#scenario-heading',title:'Test a different season',description:'Change rainfall or irrigation allowance, then recompute the same three pathways. This is a sensitivity experiment, not a weather forecast.'},
    {page:'planner',anchor:'#results',title:'Compare actual calculation outputs',description:'These values come directly from the scientific API. Lower modeled water use does not establish a better crop, profit or yield.'},
    {page:'planner',anchor:'#evidence',title:'Check the evidence before deciding',description:'See NASA POWER sources, model assumptions, crop-calendar limitations and unique run identifiers. Local validation is necessary before acting.'}
  ],
  visitor:[
    {page:'home',anchor:'#top',title:'Meet ORBITILL',description:'ORBITILL explores the water and environmental consequences of agricultural pathways, not generic one-click crop prescriptions.'},
    {page:'home',anchor:'#challenge',title:'The systems problem',description:'Crops, water, soil, seasonality and uncertainty interact. The site presents the broader challenge behind agricultural resilience.'},
    {page:'home',anchor:'#how-it-works',title:'How the scientific workflow connects',description:'Learn how environmental observations, crop-water models and evidence records support a conditional comparison. Not every named module is operational.'},
    {page:'map',anchor:'#pilot-list',title:'Explore regional capability in TerraLens',description:'The map has global exploration, administrative boundary and data capability information, with Barind as the working crop comparison pilot.'},
    {page:'planner',anchor:'#field-overview',title:'See the live Barind dashboard',description:'Observe NASA POWER provenance, shared assumptions and three real model-calculated crop-water pathways.'},
    {page:'planner',anchor:'#scenario-heading',title:'Try a reproducible experiment',description:'Adjust rainfall and irrigation inputs and recompute. Watch the model-run ID and numbers change with your assumptions.'},
    {page:'planner',anchor:'#evidence',title:'Inspect scientific traceability',description:'Review the evidence chain, source, time period, data limitations and conditional model assumptions. This is a research prototype, not a field-validated decision service.'}
  ]
};
const el=(tag,className,text)=>{const node=document.createElement(tag);if(className)node.className=className;if(text!==undefined)node.textContent=text;return node;};
const launcher=el('button','or-guide-launcher','✧ Explore ORBITILL');launcher.type='button';launcher.setAttribute('aria-label','Open the ORBITILL guided tours');
const card=el('section','or-guide-card');card.hidden=true;card.setAttribute('role','dialog');card.setAttribute('aria-label','ORBITILL guided tour');
const invite=el('div','or-guide-invite');invite.hidden=true;
let active=null,previousFocus=null,highlight=null;
const save=(v)=>{try{sessionStorage.setItem(KEY,JSON.stringify(v))}catch{}};
const load=()=>{try{const o=JSON.parse(sessionStorage.getItem(KEY)||'null');return o&&walkthroughs[o.mode]&&Number.isInteger(o.step)?o:null}catch{return null}};
const hideHighlight=()=>{if(highlight)highlight.classList.remove('or-guide-target');highlight=null};
const close=(clear=true)=>{card.hidden=true;hideHighlight();active=null;if(clear)save(null);previousFocus?.focus?.()};
const currentPage=()=>on('/planner.html')?'planner':on('/start.html')?'start':loc.includes('/terralens/')?'map':(atHome?'home':'other');
function buildCard(){card.replaceChildren();const x=el('button','or-guide-close','×');x.type='button';x.setAttribute('aria-label','Close tour');x.onclick=()=>close();card.append(x);}
function chooser(){close();previousFocus=document.activeElement;buildCard();card.append(el('span','or-guide-overline','CHOOSE YOUR PATH'));card.append(el('h2','', 'How would you like to explore?'));card.append(el('p','', 'A guided journey through the real product, tailored to what you want to learn.'));const choices=el('div','or-guide-choices');for(const [mode,name,description] of [['farmer','I am exploring as a farmer','Select a region, explore TerraLens, then enter the Command Center to investigate real water comparisons.'],['visitor','I am a visitor, researcher or NASA judge','See the mission, engineering approach, working model and evidence across the site.']]){const b=el('button','or-guide-choice',name);b.type='button';const small=el('small','',description);b.append(small);b.onclick=()=>{try{localStorage.setItem(SEEN,'1')}catch{}start(mode,0)};choices.append(b)}card.append(choices);card.hidden=false;card.querySelector('.or-guide-close').focus()}
function start(mode,step){active={mode,step};save(active);renderStep()}
function navigate(step){if(!active)return;const items=walkthroughs[active.mode];if(step<0||step>=items.length){close();return}active.step=step;save(active);renderStep()}
function renderStep(){const items=walkthroughs[active.mode],item=items[active.step];if(!item){close();return}hideHighlight();const page=currentPage();if(page!==item.page){const destination=new URL(routes[item.page],location.origin);destination.hash=item.anchor;location.assign(destination.href);return}
 buildCard();card.append(el('span','or-guide-overline',`${active.mode==='farmer'?'FARMER':'VISITOR'} TOUR · STEP ${active.step+1} / ${items.length}`));card.append(el('h2','',item.title));card.append(el('p','',item.description));const target=document.querySelector(item.anchor);if(target){highlight=target;target.classList.add('or-guide-target');target.scrollIntoView({block:'center',behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'})}else card.append(el('p','or-guide-fallback','This feature cannot be highlighted on the current page; the explanation still applies.'));
 const controls=el('div','or-guide-controls');const back=el('button','', '← Back');back.type='button';back.disabled=active.step===0;back.onclick=()=>navigate(active.step-1);const skip=el('button','', 'Skip');skip.type='button';skip.onclick=()=>close();const next=el('button','or-guide-forward',active.step===items.length-1?'Finish ✓':'Next →');next.type='button';next.onclick=()=>navigate(active.step+1);controls.append(back,skip,next);card.append(controls);card.hidden=false;next.focus();}
launcher.onclick=chooser;document.querySelectorAll('[data-orbitill-tour-open]').forEach(b=>b.addEventListener('click',chooser));
document.addEventListener('keydown',event=>{if(card.hidden)return;if(event.key==='Escape'){event.preventDefault();close()}if(event.key==='Tab'){const buttons=[...card.querySelectorAll('button:not([disabled])')];const i=buttons.indexOf(document.activeElement);if(event.shiftKey&&i===0){event.preventDefault();buttons.at(-1).focus()}else if(!event.shiftKey&&i===buttons.length-1){event.preventDefault();buttons[0].focus()}}});
document.body.append(launcher,card,invite);
const saved=load();if(saved){active=saved;renderStep()}else if(currentPage()==='home'||currentPage()==='start'||currentPage()==='planner'||currentPage()==='map'){
 let seen=true;try{seen=Boolean(localStorage.getItem(SEEN))}catch{};
 if(!seen){setTimeout(()=>{if(!card.hidden)return;invite.textContent='New here? Take a quick guided tour of ORBITILL.';const go=el('button','','Explore');go.onclick=()=>{invite.hidden=true;chooser()};const dismiss=el('button','or-guide-dismiss','Not now');dismiss.onclick=()=>{invite.hidden=true;try{localStorage.setItem(SEEN,'1')}catch{}};invite.append(go,dismiss);invite.hidden=false},2600)}
}
})();
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
const editorialRoutes=[['The Challenge','explore.html#challenge'],['How It Works','explore.html#how-it-works'],['Field Stories','explore.html#field-stories'],['The Evidence','explore.html#evidence']];
document.querySelectorAll('.story-nav a').forEach((link,index)=>{if(editorialRoutes[index]){link.textContent=editorialRoutes[index][0];link.href=editorialRoutes[index][1];}});
document.querySelector('.back-button')?.addEventListener('click', () => history.length > 1 ? history.back() : location.assign('index.html'));

const revealObserver = new IntersectionObserver(entries => entries.forEach(entry => {
  if (entry.isIntersecting) { entry.target.classList.add('is-visible'); revealObserver.unobserve(entry.target); }
}), {threshold:.1});
document.querySelectorAll('.reveal').forEach(element => revealObserver.observe(element));

const themeCopy = {
  cover:'Cover between cash crops changes when living roots are present. The outcome remains dependent on weather, soils and management.',
  water:'Rainfall and dissolved nutrients can move through tile drainage, but ORBITILL does not infer nitrate loss from precipitation alone.',
  feasibility:'A practice must fit establishment, termination, equipment, labor, markets and the farm’s priorities—not only an environmental goal.'
};
document.querySelectorAll('[data-theme]').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('[data-theme]').forEach(item => item.classList.toggle('is-active', item === button));
  document.querySelector('#theme-copy').textContent = themeCopy[button.dataset.theme];
}));

const pathways = {
  continue:['Continue','The corn–soybean baseline is the comparator. No outcome is shown until compatible field inputs and a consistent planning horizon are supplied.'],
  adapt:['Adapt','Cereal rye is a management addition between cash crops. Establishment, termination, operational cost and sequence fit must be evaluated explicitly.'],
  diversify:['Diversify','A small-grain addition changes the cash-crop sequence. It remains conditional on a supported local calendar, markets, equipment and farmer priorities.']
};
document.querySelectorAll('[data-path]').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('[data-path]').forEach(item => { const active=item===button; item.classList.toggle('is-active',active); item.setAttribute('aria-selected',String(active)); });
  const [label,copy]=pathways[button.dataset.path]; document.querySelector('#path-note b').textContent=`Selected / ${label}`; document.querySelector('#path-note p').textContent=copy;
}));

const scenarios = {
  wet:['When spring arrives wetter','Investigate field access, drainage context, planting timing and establishment risk.','Needs: weather series · soil drainage · crop calendar · field operations'],
  dry:['When the growing season turns drier','Investigate rainfall deficit, soil-water assumptions and crop-stage demand.','Needs: NASA weather series · soil water capacity · crop stages · water model'],
  cost:['When inputs become more expensive','Test whether seed, termination, fuel and labor assumptions change the feasible pathways.','Needs: sourced local costs · declared currency · farmer priorities · sensitivity range'],
  timing:['When the planting window narrows','Test which crop and cover-crop sequences still fit without overlapping operations.','Needs: verified crop calendars · duration · turnaround time · field operations']
};
document.querySelectorAll('[data-scenario]').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('[data-scenario]').forEach(item => item.classList.toggle('is-active',item===button));
  const [heading,copy,needs]=scenarios[button.dataset.scenario]; document.querySelector('#scenario-heading').textContent=heading; document.querySelector('#scenario-copy').textContent=copy; document.querySelector('#scenario-needs').textContent=needs;
}));

if (!reducedMotion) {
  const image=document.querySelector('.us-hero-image'); let ticking=false;
  addEventListener('scroll',()=>{ if(ticking||scrollY>innerHeight*1.2)return; ticking=true; requestAnimationFrame(()=>{image.style.transform=`scale(1.03) translateY(${scrollY*.035}px)`;ticking=false;});},{passive:true});
}

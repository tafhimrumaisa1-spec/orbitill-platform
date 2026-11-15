const outlet = document.querySelector('#editorial-content');
const navLinks = [...document.querySelectorAll('[data-route]')];
const routes = {
  challenge: { title:'The Challenge', mount: target => OrbitillChallenge.mount(target,{onNavigate:navigate}) },
  'how-it-works': { title:'How It Works', mount: target => OrbitillHowItWorks.mount(target,{onNavigate:navigate}) },
  'field-stories': { title:'Field Stories', mount: target => OrbitillFieldStories.mount(target,{onNavigate:navigate}) },
  evidence: { title:'The Evidence', mount: target => OrbitillEvidence.mount(target,{onNavigate:navigate}) }
};

document.querySelector('.back-button').addEventListener('click',()=>history.length>1?history.back():location.assign('index.html'));
addEventListener('hashchange',renderRoute);
renderRoute();

function currentRoute(){
  const requested=location.hash.slice(1);
  return routes[requested]?requested:'challenge';
}

function renderRoute(){
  const key=currentRoute();
  if(location.hash!==`#${key}`) history.replaceState(null,'',`#${key}`);
  const entry=routes[key];
  const component=entry.mount(outlet);
  navLinks.forEach(link=>{
    const active=link.dataset.route===key;
    link.toggleAttribute('aria-current',active);
    if(active) link.setAttribute('aria-current','page');
  });
  document.title=`${entry.title} · ORBITILL`;
  if(key==='how-it-works'){
    patchHowItWorks(component);
    outlet.append(buildEcosystem());
  }
  if(key==='evidence') patchEvidence(component);
  scrollTo({top:0,behavior:'instant'});
  outlet.focus({preventScroll:true});
}

function navigate(destination){
  const map={
    'the-challenge':'challenge',challenge:'challenge','how-it-works':'how-it-works',
    'field-stories':'field-stories','the-evidence':'evidence',evidence:'evidence'
  };
  if(destination==='experience'){location.assign('planner.html');return;}
  if(destination==='global'){location.assign('index.html');return;}
  if(map[destination]) location.hash=map[destination];
}

function patchHowItWorks(component){
  requestAnimationFrame(()=>{
    const cards=[...component.shadowRoot.querySelectorAll('.data-card')];
    const power=cards.find(card=>card.querySelector('h3')?.textContent.trim()==='Climate baseline');
    const footer=power?.querySelector('footer');
    if(footer) footer.innerHTML='Integrated for Barind and Iowa through verified offline daily bundles · <a href="https://power.larc.nasa.gov/docs/services/api/temporal/daily/" target="_blank" rel="noopener noreferrer">API documentation ↗</a>';
  });
}

function patchEvidence(component){
  const apply=()=>{
    for(const dataset of component.shadowRoot.querySelectorAll('.dataset')){
      const name=dataset.querySelector('h3')?.textContent.trim();
      const status=dataset.querySelector('.status');
      if(name==='NASA POWER'&&status){status.textContent='Integrated · verified offline Barind and Iowa bundles';status.classList.add('status-reviewed');}
      if(name==='FAO Irrigation & Drainage Paper 56'&&status){status.textContent='Implemented reference method · code-tested, not field-validated';status.classList.add('status-reviewed');}
    }
    const reviewed={
      EarthSync:'Integrated with verified POWER bundles; platform lineage tests pass; not independently field-validated',
      TerraLens:'Integrated region explorer; 175 routing, geometry, API and provenance tests pass; boundaries are cartographic, not cadastral',
      SoilBrain:'Integrated and evidence-gated; complete Barind rules remain conditional',
      AquaSense:'Integrated in Barind water demonstration; physical and platform tests pass; not field-calibrated',
      RootShift:'Integrated for three conditional water pathways; broader economics remain unavailable',
      FutureFields:'Module tests pass; rainfall/allowance recomputation integrated, local economics pending'
    };
    component.shadowRoot.querySelectorAll('#ev-validation tbody tr').forEach(row=>{
      const name=row.querySelector('strong')?.textContent.trim();
      if(reviewed[name]) row.lastElementChild.textContent=reviewed[name];
    });
  };
  requestAnimationFrame(apply);
  component.shadowRoot.addEventListener('click',()=>setTimeout(apply,0));
  component.shadowRoot.addEventListener('input',()=>setTimeout(apply,0));
}

function buildEcosystem(){
  const section=document.createElement('section');
  section.className='intelligence-ecosystem';
  const technologies=[
    ['01','TerraLens','Routes place and capability before analysis.'],
    ['02','EarthSync','Preserves environmental observations, units and provenance.'],
    ['03','SoilBrain','Gates crop and soil rules by regional evidence.'],
    ['04','AquaSense','Calculates conditional crop-water implications.'],
    ['05','RootShift','Compares the current pathway with alternatives.'],
    ['06','FutureFields','Recomputes declared hypothetical changes.'],
    ['07','EvidenceLayer','Connects results to sources, assumptions and limits.'],
    ['08','FieldPilot','Explains supported results; conversational runtime is not included in this release.']
  ];
  section.innerHTML=`<div><p class="eco-kicker">THE INTELLIGENCE ECOSYSTEM / EIGHT DISTINCT RESPONSIBILITIES</p><h2>One decision journey.<br><em>Eight inspectable technologies.</em></h2><div class="ecosystem-grid">${technologies.map(([number,name,copy])=>`<article><span>${number} / SYSTEM</span><h3>${name}</h3><p>${copy}</p></article>`).join('')}</div><p class="ecosystem-note">Module presence does not mean universal readiness. TerraLens now gates geography and capability before the integrated EarthSync, AquaSense and conditional RootShift comparison; SoilBrain remains evidence-gated, and FieldPilot's runnable conversational delivery was not received.</p></div>`;
  return section;
}

const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const editorialRoutes=[['The Challenge','explore.html#challenge'],['How It Works','explore.html#how-it-works'],['Field Stories','explore.html#field-stories'],['The Evidence','explore.html#evidence']];
document.querySelectorAll('.story-nav a').forEach((link,index)=>{if(editorialRoutes[index]){link.textContent=editorialRoutes[index][0];link.href=editorialRoutes[index][1];}});

// Product calls-to-action enter the working research demonstration. Story
// chapter links remain local to this editorial page.
['.experience-link','.hero-copy .glass-link','.rootshift-footer a','.return-actions a:first-child','.ending-copy a[href="#rootshift"]']
  .forEach(selector => document.querySelector(selector)?.setAttribute('href', 'planner.html'));
document.querySelector('.evidence-button')?.setAttribute('href', 'planner.html#evidence');
document.querySelector('.ending-copy a[href="#evidence"]')?.setAttribute('href', 'planner.html#evidence');
document.querySelector('.return-actions a:last-child')?.setAttribute('href','terralens/index.html');

document.querySelector('.back-button')?.addEventListener('click', () => {
  if (history.length > 1) history.back();
  else location.hash = '#top';
});

const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add('is-visible');
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.13 });
document.querySelectorAll('.reveal').forEach((element) => revealObserver.observe(element));

const navLinks = [...document.querySelectorAll('.story-nav a')];
const watchedSections = navLinks.map((link) => document.querySelector(link.getAttribute('href'))).filter(Boolean);
const sectionObserver = new IntersectionObserver((entries) => {
  const active = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
  if (!active) return;
  navLinks.forEach((link) => link.classList.toggle('is-active', link.getAttribute('href') === `#${active.target.id}`));
}, { rootMargin: '-25% 0px -60% 0px', threshold: [0, .25, .6] });
watchedSections.forEach((section) => sectionObserver.observe(section));

document.querySelectorAll('.future-tab').forEach((button) => {
  button.addEventListener('click', () => {
    document.querySelectorAll('.future-tab').forEach((item) => {
      const selected = item === button;
      item.classList.toggle('is-active', selected);
      item.setAttribute('aria-selected', String(selected));
    });
  });
});

const scenarioCopy = {
  rain: ['Rainfall assumption selected', 'The production experience will send this changed rainfall assumption through the scientific model and show recomputed tradeoffs—not a visual slider trick.'],
  water: ['Irrigation-access assumption selected', 'The production experience will apply the changed season allowance across the compatible rotation and recalculate water constraints.'],
  cost: ['Input-cost assumption selected', 'The production experience will recalculate compatible economics using the declared currency, source basis and uncertainty.'],
};
document.querySelectorAll('.scenario-chip').forEach((button) => {
  button.addEventListener('click', () => {
    document.querySelectorAll('.scenario-chip').forEach((item) => item.classList.toggle('is-active', item === button));
    const [title, explanation] = scenarioCopy[button.dataset.scenario];
    document.querySelector('#scenario-question').textContent = title;
    document.querySelector('#scenario-explanation').textContent = explanation;
  });
});

const toast = document.querySelector('.toast');
let toastTimer;
function showToast(message) {
  toast.textContent = message;
  toast.classList.add('is-visible');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('is-visible'), 2800);
}
document.querySelectorAll('[data-coming], [data-destination]').forEach((link) => {
  link.addEventListener('click', (event) => {
    const destination = link.dataset.coming || link.dataset.destination;
    if (link.dataset.coming) event.preventDefault();
    showToast(`${destination} experience is the next regional chapter.`);
  });
});

if (!reducedMotion) {
  const heroImage = document.querySelector('.hero-image');
  let ticking = false;
  window.addEventListener('scroll', () => {
    if (ticking || scrollY > innerHeight * 1.2) return;
    ticking = true;
    requestAnimationFrame(() => {
      heroImage.style.transform = `scale(1.035) translateY(${scrollY * .045}px)`;
      ticking = false;
    });
  }, { passive: true });
}

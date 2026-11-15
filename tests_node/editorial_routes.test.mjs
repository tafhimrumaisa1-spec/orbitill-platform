import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const read = path => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');

test('editorial router exposes all four top-bar destinations and real experience route', () => {
  const html = read('apps/web/explore.html');
  const router = read('apps/web/editorial-router.js');
  for (const route of ['challenge','how-it-works','field-stories','evidence']) {
    assert.match(html, new RegExp(`data-route="${route}"`));
    assert.match(router, new RegExp(`["']?${route.replace('-','\\-')}`));
  }
  assert.match(router, /planner\.html/);
});

test('How It Works names all eight ORBITILL technologies', () => {
  const router = read('apps/web/editorial-router.js');
  for (const name of ['TerraLens','EarthSync','SoilBrain','AquaSense','RootShift','FutureFields','EvidenceLayer','FieldPilot']) {
    assert.match(router, new RegExp(name));
  }
});

test('audited status language distinguishes integrated and unavailable capabilities', () => {
  const router = read('apps/web/editorial-router.js');
  assert.match(router, /NASA POWER/);
  assert.match(router, /verified offline/);
  assert.match(router, /TerraLens:'Integrated region explorer; 175 routing, geometry, API and provenance tests pass/);
  assert.match(router, /conversational runtime is not included/);
});

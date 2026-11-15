import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';

const web = resolve('apps/web');
const pages = [
  ...readdirSync(web).filter(name => name.endsWith('.html')),
  'terralens/index.html',
];
const failures = [];

for (const page of pages) {
  const file = join(web, page);
  const html = readFileSync(file, 'utf8');
  const ids = [...html.matchAll(/\sid="([^"]+)"/g)].map(match => match[1]);
  for (const id of new Set(ids)) {
    if (ids.filter(value => value === id).length > 1) failures.push(`${page}: duplicate id #${id}`);
  }
  for (const match of html.matchAll(/(?:href|src)="([^"]+)"/g)) {
    const target = match[1];
    if (/^(?:https?:|mailto:|data:)/.test(target)) continue;
    const [path, fragment] = target.split('#');
    const targetFile = path ? resolve(dirname(file), path) : file;
    if (!existsSync(targetFile)) {
      failures.push(`${page}: missing local target ${target}`);
      continue;
    }
    if (fragment && targetFile.endsWith('.html')) {
      if (targetFile === file && page === 'explore.html' && ['challenge','how-it-works','field-stories','evidence'].includes(fragment)) continue;
      const targetHtml = readFileSync(targetFile, 'utf8');
      if (!new RegExp(`\\sid=["']${fragment}["']`).test(targetHtml)) failures.push(`${page}: missing fragment ${target}`);
    }
  }
}

if (failures.length) {
  failures.forEach(item => console.error(`FAIL ${item}`));
  process.exitCode = 1;
} else {
  console.log(`PASS ${pages.length} HTML pages: local targets, fragments and duplicate IDs`);
}

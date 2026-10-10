const test = require('node:test');
const assert = require('node:assert/strict');
const { applySystem } = require('../static/js/appearance.js');
test('system preference follows the OS while explicit choices remain stable', () => {
  const document = { documentElement: { dataset: { mode: 'system', theme: 'light' } } };
  let changed;
  const media = { matches: true, addEventListener(name, callback) { changed = callback; } };
  applySystem(document, media);
  assert.equal(document.documentElement.dataset.theme, 'dark');
  media.matches = false;
  changed();
  assert.equal(document.documentElement.dataset.theme, 'light');
  document.documentElement.dataset.mode = 'dark';
  document.documentElement.dataset.theme = 'dark';
  applySystem(document, media);
  assert.equal(document.documentElement.dataset.theme, 'dark');
});

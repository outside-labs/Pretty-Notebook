const test = require('node:test');
const assert = require('node:assert/strict');
const { initialize } = require('../static/js/site-navigation.js');
function fixture(narrow) {
  const handlers = {};
  const button = { hidden: true, attributes: {}, addEventListener(name, callback) { handlers[name] = callback; },
    setAttribute(name, value) { this.attributes[name] = value; }, focus() { this.focused = true; } };
  const panel = { hidden: false };
  const nav = { querySelector(selector) { return selector === '.nav-toggle' ? button : panel; },
    addEventListener(name, callback) { handlers[name] = callback; } };
  const media = { matches: narrow, addEventListener(name, callback) { handlers.resize = callback; } };
  initialize(nav, media);
  return { handlers, button, panel, media };
}
test('mobile disclosure announces state, Escape closes and restores focus', () => {
  const { handlers, button, panel } = fixture(true);
  assert.equal(panel.hidden, true);
  assert.equal(button.hidden, false);
  assert.equal(button.attributes['aria-expanded'], 'false');
  handlers.click();
  assert.equal(panel.hidden, false);
  assert.equal(button.attributes['aria-expanded'], 'true');
  let prevented = false;
  handlers.keydown({ key: 'Escape', target: {}, preventDefault() { prevented = true; } });
  assert.equal(panel.hidden, true);
  assert.equal(button.focused, true);
  assert.equal(prevented, true);
});
test('desktop links remain visible and resize resets the mobile panel', () => {
  const { handlers, button, panel, media } = fixture(false);
  assert.equal(panel.hidden, false);
  assert.equal(button.hidden, true);
  media.matches = true;
  handlers.resize();
  assert.equal(panel.hidden, true);
  handlers.click();
  media.matches = false;
  handlers.resize();
  assert.equal(panel.hidden, false);
  assert.equal(button.hidden, true);
});
test('Escape closes native dropdowns before the surrounding disclosure', () => {
  const { handlers, panel } = fixture(true);
  handlers.click();
  let focused = false;
  const details = { open: true, querySelector() { return { focus() { focused = true; } }; } };
  handlers.keydown({ key: 'Escape', target: { closest() { return details; } }, preventDefault() {} });
  assert.equal(details.open, false);
  assert.equal(focused, true);
  assert.equal(panel.hidden, false);
});

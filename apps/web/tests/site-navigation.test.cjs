const test = require('node:test');
const assert = require('node:assert/strict');
const { initialize } = require('../static/js/site-navigation.js');
function fixture(open = false) {
  const handlers = {};
  const summary = { focus() { this.focused = true; } };
  const menu = { open, querySelector() { return summary; } };
  const nav = { querySelector() { return menu; },
    addEventListener(name, callback) { handlers[name] = callback; } };
  initialize(nav);
  return { handlers, menu, summary };
}
test('native disclosure keeps its initial state without viewport-dependent resets', () => {
  assert.equal(fixture().menu.open, false);
  assert.equal(fixture(true).menu.open, true);
});
test('Escape closes the open menu and returns focus to its summary', () => {
  const { handlers, menu, summary } = fixture(true);
  let prevented = false;
  handlers.keydown({ key: 'Escape', target: {}, preventDefault() { prevented = true; } });
  assert.equal(menu.open, false);
  assert.equal(summary.focused, true);
  assert.equal(prevented, true);
});
test('Escape closes nested appearance dropdowns before the surrounding menu', () => {
  const { handlers, menu } = fixture(true);
  let focused = false;
  const details = { open: true, querySelector() { return { focus() { focused = true; } }; } };
  handlers.keydown({ key: 'Escape', target: { closest() { return details; } }, preventDefault() {} });
  assert.equal(details.open, false);
  assert.equal(focused, true);
  assert.equal(menu.open, true);
});
test('closed menus and unrelated keys do not consume keyboard events', () => {
  const { handlers, menu } = fixture();
  const unexpected = () => assert.fail('Unhandled key was consumed');
  handlers.keydown({ key: 'Escape', target: {}, preventDefault: unexpected });
  menu.open = true;
  handlers.keydown({ key: 'Enter', target: {}, preventDefault: unexpected });
  assert.equal(menu.open, true);
});

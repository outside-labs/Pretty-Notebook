const test = require('node:test');
const assert = require('node:assert/strict');
const { configuration, applyPreview, accentTextColor, copyConfiguration, initialize } = require('../static/js/appearance-preferences.js');

test('theme families have the expected mode and independently chosen preferences', () => {
  const fields = Object.fromEntries(Object.entries({ theme: 'midnight', font: 'serif', density: 'compact', accent: '#ffee88', radius: '12' }).map(([key, value]) => [key, { value }]));
  for (const [theme, mode] of Object.entries({ forest: 'light', paper: 'light', dark: 'dark', midnight: 'dark' })) {
    fields.theme.value = theme;
    assert.deepEqual(configuration(fields, false), { palette: theme, mode, font: 'serif', density: 'compact', accent: '#ffee88', radius: 12 });
    assert.equal(configuration(fields, true).accent, null);
  }
});

test('preview switches clear custom accents and leave document preferences alone', () => {
  const properties = new Map();
  const preview = { dataset: {}, style: { setProperty: (key, value) => properties.set(key, value), removeProperty: key => properties.delete(key) } };
  applyPreview(preview, { palette: 'dark', mode: 'dark', font: 'mono', density: 'compact', radius: 20, accent: '#ffee88' });
  assert.deepEqual(preview.dataset, { previewPalette: 'dark', previewMode: 'dark', font: 'mono', density: 'compact' });
  assert.equal(properties.get('--radius-md'), '20px');
  assert.equal(properties.get('--color-on-primary'), '#000000');
  applyPreview(preview, { palette: 'paper', mode: 'light', font: 'sans', density: 'comfortable', radius: 0, accent: null });
  assert.equal(properties.has('--color-primary'), false);
  assert.equal(properties.has('--color-on-primary'), false);
  assert.equal(properties.get('--radius-md'), '0px');
  assert.equal(accentTextColor('#111111'), '#ffffff');
  assert.equal(accentTextColor('#FFFFFF'), '#000000');
});

test('copy uses the clipboard or offers selectable JSON when unavailable or denied', async () => {
  const value = { palette: 'forest', mode: 'light', font: 'serif', density: 'compact', radius: 10, accent: null };
  const status = {};
  let copied;
  await copyConfiguration(value, { writeText: async text => { copied = text; } }, null, status);
  assert.deepEqual(JSON.parse(copied), value);
  assert.equal(status.textContent, 'Configuration copied.');
  for (const clipboard of [null, { writeText: async () => { throw new Error('denied'); } }]) {
    let focused = false, selected = false;
    const fallback = { parentElement: { hidden: true }, focus: () => { focused = true; }, select: () => { selected = true; } };
    await copyConfiguration(value, clipboard, fallback, status);
    assert.deepEqual(JSON.parse(fallback.value), value);
    assert.equal(fallback.parentElement.hidden, false);
    assert.ok(focused && selected);
  }
});

test('page controls wire live changes, theme accent reset, copy fallback and sample editing', async () => {
  function element(extra = {}) {
    const listeners = {};
    return { hidden: true, listeners, addEventListener: (name, handler) => { listeners[name] = handler; }, ...extra };
  }
  const fields = Object.fromEntries(Object.entries({ theme: 'paper', font: 'serif', density: 'comfortable', accent: '#275d3e', radius: '6' }).map(([name, value]) => [name, element({ name, value, dataset: { defaultAccent: 'true' } })]));
  const defaultInput = element({ disabled: true });
  const reset = element();
  const properties = new Map();
  const title = element({ focus() { this.focused = true; } });
  const body = element();
  const edit = element();
  const newNote = element();
  const previewNodes = { '[data-preview-title]': title, '[data-preview-body]': body, '[data-preview-edit]': edit, '[data-preview-new]': newNote };
  const preview = element({ dataset: {}, style: { setProperty: (key, value) => properties.set(key, value), removeProperty: key => properties.delete(key) }, querySelector: selector => previewNodes[selector] });
  const form = element({ querySelector: selector => selector === '[data-accent-default]' ? defaultInput : selector === '[data-accent-reset]' ? reset : fields[selector.match(/name="(\w+)"/)[1]] });
  const fallback = element({ parentElement: { hidden: true }, focus() {}, select() {} });
  const status = element();
  const output = element();
  const copy = element();
  const documentNodes = { '[data-appearance-form]': form, '[data-appearance-preview]': preview, '[data-appearance-status]': status, '[data-configuration-text]': fallback, '[data-radius-output]': output, '[data-copy-appearance]': copy };
  const originalStyle = globalThis.getComputedStyle;
  globalThis.getComputedStyle = () => ({ getPropertyValue: () => '#275d3e' });
  try {
    initialize({ querySelector: selector => documentNodes[selector] });
    assert.equal(defaultInput.disabled, false);
    assert.equal(fields.accent.name, '');
    assert.equal(copy.hidden, false);
    fields.theme.value = 'midnight';
    fields.font.value = 'mono';
    fields.density.value = 'compact';
    fields.radius.value = '14';
    form.listeners.change({ target: fields.theme });
    assert.equal(preview.dataset.previewMode, 'dark');
    assert.equal(preview.dataset.font, 'mono');
    assert.equal(preview.dataset.density, 'compact');
    assert.equal(output.value, 14);
    fields.accent.value = '#ffee88';
    form.listeners.input({ target: fields.accent });
    assert.equal(fields.accent.name, 'accent');
    assert.equal(defaultInput.disabled, true);
    assert.equal(properties.get('--color-on-primary'), '#000000');
    reset.listeners.click();
    assert.equal(properties.has('--color-primary'), false);
    assert.equal(defaultInput.disabled, false);
    await copy.listeners.click();
    assert.equal(JSON.parse(fallback.value).palette, 'midnight');
    assert.equal(JSON.parse(fallback.value).accent, null);
    edit.listeners.click();
    assert.equal(title.contentEditable, 'true');
    assert.equal(title.focused, true);
    newNote.listeners.click();
    assert.equal(title.textContent, 'Untitled note');
    assert.equal(body.textContent, 'Write your next idea here.');
  } finally {
    globalThis.getComputedStyle = originalStyle;
  }
});

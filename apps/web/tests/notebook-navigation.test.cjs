const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname, "../static/js/notebook-navigation.js"), "utf8");

function click({ referrer = "", prefix = "/notes", length = 2, broken = false, inaccessible = false, event = {} } = {}) {
  let callback;
  let backed = 0;
  let prevented = false;
  const link = { dataset: { rootPath: prefix }, addEventListener: (name, handler) => { callback = handler; } };
  const history = { back: () => { if (broken) throw new Error("Blocked"); backed++; } };
  Object.defineProperty(history, "length", { get: () => { if (inaccessible) throw new Error("Blocked"); return length; } });
  const document = { referrer, querySelectorAll: () => [link] };
  const window = { history, location: { href: "https://example.test/notes/page" } };
  vm.runInNewContext(source, { document, window, URL });
  callback({ button: 0, preventDefault: () => { prevented = true; }, ...event });
  return { backed, prevented };
}

test("Back uses ordinary browser history after an internal visit", () => {
  assert.deepEqual(click({ referrer: "https://example.test/notes/n?directory=guides" }), { backed: 1, prevented: true });
  assert.deepEqual(click({ prefix: "", referrer: "https://example.test/" }), { backed: 1, prevented: true });
});

for (const referrer of ["", "not a URL", "https://outside.test/notes/a", "https://example.test/other",
                        "https://example.test/notes-extra/a", "https://example.test/outside?next=/notes/a",
                        "https://example.test/notes/../outside", "https://example.test/notes/%2e%2e/outside",
                        "https://example.test/notes/%2foutside", "https://example.test/notes/page"]) {
  test(`direct, external, or invalid entry retains the server index fallback: ${referrer}`, () => {
    assert.deepEqual(click({ referrer }), { backed: 0, prevented: false });
  });
}

test("missing prior history and blocked history APIs retain normal anchor behavior", () => {
  const referrer = "https://example.test/notes/a";
  for (const option of [{ length: 1 }, { broken: true }, { inaccessible: true }]) {
    assert.deepEqual(click({ referrer, ...option }), { backed: 0, prevented: false });
  }
});

test("modified, non-primary, and already handled clicks retain browser native behavior", () => {
  for (const event of [{ button: 1 }, { ctrlKey: true }, { metaKey: true }, { shiftKey: true }, { altKey: true }, { defaultPrevented: true }]) {
    assert.deepEqual(click({ referrer: "https://example.test/notes/a", event }), { backed: 0, prevented: false });
  }
});

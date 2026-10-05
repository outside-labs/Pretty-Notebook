const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");
const loader = fs.readFileSync(path.join(__dirname, "../static/js/code-tools.js"), "utf8");

class Element {
  constructor(tag, text = "", classes = []) {
    this.tagName = tag.toUpperCase();
    this.text = text;
    this.classes = new Set(classes);
    const names = this.classes;
    this.classList = { contains: name => names.has(name), add: name => names.add(name), [Symbol.iterator]: () => names.values() };
    this.children = [];
    this.parentElement = null;
    this.attributes = {};
    this.listeners = {};
    this.disabled = false;
  }
  get textContent() { return this.text + this.children.map(child => child.textContent).join(""); }
  set textContent(value) { this.text = value; this.children = []; }
  get className() { return [...this.classes].join(" "); }
  set className(value) { this.classes.clear(); value.split(" ").forEach(name => this.classes.add(name)); }
  appendChild(child) { child.remove(); child.parentElement = this; this.children.push(child); return child; }
  append(...children) { children.forEach(child => this.appendChild(child)); }
  before(node) {
    const parent = this.parentElement;
    node.parentElement = parent;
    parent.children.splice(parent.children.indexOf(this), 0, node);
  }
  remove() { if (this.parentElement) this.parentElement.children = this.parentElement.children.filter(child => child !== this); }
  matches(selector) { return selector === "pre > code" && this.tagName === "CODE" && this.parentElement?.tagName === "PRE"; }
  closest(selector) { return selector === ".mermaid" && this.classes.has("mermaid") ? this : this.parentElement?.closest(selector); }
  setAttribute(name, value) { this.attributes[name] = value; }
  addEventListener(name, callback) { this.listeners[name] = callback; }
  click() { return this.listeners.click(); }
}

function block(source, language = "python", classes = []) {
  const pre = new Element("pre");
  pre.appendChild(new Element("code", source, [...classes, ...(language ? ["language-" + language] : [])]));
  return pre;
}

function descendants(node) {
  return node.children.flatMap(child => [child, ...descendants(child)]);
}

function browser(nodes, { highlighting = "on", blocked = false, clipboard = "ok", highlightFailure = false, mutate = false, delayed = false } = {}) {
  const root = new Element("article");
  root.append(...nodes);
  const head = new Element("head");
  const assets = [];
  const copied = [];
  const highlighted = [];
  const events = {};
  let finishLoad;
  const window = { addEventListener: (name, callback) => { events[name] = callback; } };
  const hljs = {
    getLanguage: name => ["python", "text", "py"].includes(name),
    highlightElement: code => {
      highlighted.push(code);
      code.classList.add("hljs");
      if (mutate || highlightFailure) code.textContent = "changed by highlighter";
      if (highlightFailure) throw new Error("Highlight failed");
    },
  };
  head.appendChild = element => {
    assets.push(element);
    if (element.tagName === "SCRIPT") {
      finishLoad = () => {
        if (blocked) element.onerror();
        else { window.hljs = hljs; element.onload(); }
      };
      if (!delayed) Promise.resolve().then(finishLoad);
    }
  };
  const document = {
    readyState: "complete", head,
    currentScript: { dataset: { highlight: highlighting, highlightSrc: "/reviewed/highlight.js", highlightIntegrity: "sha384-script",
                              highlightStyle: "/reviewed/highlight.css", highlightStyleIntegrity: "sha384-style" } },
    querySelector: () => root,
    createElement: tag => new Element(tag),
    getElementById: id => descendants(root).find(node => node.id === id) || null,
    createTreeWalker: () => { const all = descendants(root); return { nextNode: () => all.shift() || null }; },
    addEventListener: (name, callback) => { events[name] = callback; },
  };
  const navigator = clipboard === "missing" ? {} : { clipboard: { writeText: async source => {
    if (clipboard === "failed") throw new Error("Clipboard denied");
    copied.push(source);
  } } };
  vm.runInNewContext(loader, { document, window, navigator, NodeFilter: { SHOW_ELEMENT: 1 } });
  return { root, assets, copied, highlighted, events, window, finishLoad: () => finishLoad(),
           buttons: () => descendants(root).filter(node => node.tagName === "BUTTON"),
           statuses: () => descendants(root).filter(node => node.attributes.role === "status") };
}

test("copy preserves tabs, indentation, Unicode, syntax, and trailing newlines after highlighting", async () => {
  const source = '  first\t☃\n\t[[note]] #tag <b>& text\n\n';
  const pre = block(source);
  const page = browser([pre], { mutate: true });
  await page.window.pnbpCodeTools.render();
  await page.buttons()[0].click();
  assert.deepEqual(page.copied, [source]);
  assert.equal(pre.children[0].textContent, source);
  assert.equal(page.statuses()[0].textContent, "Code copied.");
  assert.equal(page.statuses()[0].attributes["aria-live"], "polite");
  assert.equal(page.buttons()[0].attributes["aria-describedby"], page.statuses()[0].id);
  assert.equal(pre.tabIndex, 0);
  assert.equal(pre.attributes.role, "region");
  assert.equal(page.assets.length, 2);
  assert.equal(page.assets[0].integrity, "sha384-style");
  assert.equal(page.assets[1].integrity, "sha384-script");
  assert.equal(page.assets[1].crossOrigin, "anonymous");
});

test("plain pages, inline code, and Mermaid never request highlighting", async () => {
  const diagram = block("graph TD; A-->B", "mermaid");
  const pre = new Element("pre", "graph TD", ["mermaid"]);
  const page = browser([new Element("p", "Plain"), new Element("code", "Inline"), diagram, pre]);
  await page.window.pnbpCodeTools.render();
  assert.equal(page.assets.length, 0);
  assert.equal(page.buttons().length, 0);
});

test("unlabelled, empty, opt-out, and oversized code stay copyable without loading Highlight.js", async () => {
  const sources = ["plain\ttext\n", "", "opt-out\n", "x".repeat(100001) + "\n"];
  const page = browser([block(sources[0], ""), block(sources[1]), block(sources[2], "python", ["nohighlight"]), block(sources[3])]);
  await page.window.pnbpCodeTools.render();
  for (const button of page.buttons()) await button.click();
  assert.equal(page.assets.length, 0);
  assert.deepEqual(page.copied, sources);
  const parentOptOut = block("parent opt-out\n");
  parentOptOut.classList.add("no-highlight");
  const parentPage = browser([parentOptOut]);
  await parentPage.window.pnbpCodeTools.render();
  assert.equal(parentPage.assets.length, 0);
});

test("site-wide highlighting opt-out keeps controls and exact source", async () => {
  const source = "print(1)\n";
  const page = browser([block(source)], { highlighting: "off" });
  await page.window.pnbpCodeTools.render();
  await page.buttons()[0].click();
  assert.equal(page.assets.length, 0);
  assert.deepEqual(page.copied, [source]);
});

test("unknown language labels remain literal text and source is not guessed", async () => {
  const name = '<img/src=x/onerror=alert(1)>';
  const pre = block("unknown\n", name);
  const page = browser([pre]);
  await page.window.pnbpCodeTools.render();
  const label = descendants(page.root).find(node => node.classList.contains("code-label"));
  assert.equal(label.textContent, name);
  assert.equal(label.children.length, 0);
  assert.equal(page.highlighted.length, 0);
  await page.buttons()[0].click();
  assert.deepEqual(page.copied, ["unknown\n"]);
});

for (const failure of ["blocked", "highlightFailure"]) {
  test(`${failure} leaves readable source and working copy controls`, async () => {
    const source = "print('☃')\n";
    const pre = block(source);
    const page = browser([pre], { [failure]: true });
    await page.window.pnbpCodeTools.render();
    assert.equal(pre.children[0].textContent, source);
    await page.buttons()[0].click();
    assert.deepEqual(page.copied, [source]);
  });
}

for (const clipboard of ["missing", "failed"]) {
  test(`${clipboard} clipboard announces a manual-copy fallback and re-enables the button`, async () => {
    const page = browser([block("code\n")], { clipboard });
    await page.window.pnbpCodeTools.render();
    await page.buttons()[0].click();
    assert.equal(page.statuses()[0].textContent, "Copy unavailable. Select the code and copy it.");
    assert.equal(page.statuses()[0].className, "code-status");
    assert.equal(page.buttons()[0].disabled, false);
    assert.equal(page.copied.length, 0);
  });
}

test("navigation reuses controls and refreshes the snapshot after an actual edit", async () => {
  const pre = block("first\n");
  const page = browser([pre]);
  await page.window.pnbpCodeTools.render();
  page.events.pageshow();
  await page.window.pnbpCodeTools.render();
  assert.equal(page.buttons().length, 1);
  assert.equal(page.assets.length, 2);
  assert.equal(page.highlighted.length, 1);
  pre.children[0].textContent = "second\t☃\n";
  page.events["pnbp:content"]();
  await page.window.pnbpCodeTools.render();
  await page.buttons()[0].click();
  assert.deepEqual(page.copied, ["second\t☃\n"]);
  assert.equal(page.buttons().length, 1);
});

test("content changed during runtime loading becomes the new copy snapshot", async () => {
  const pre = block("first\n");
  const page = browser([pre], { delayed: true });
  pre.children[0].textContent = "changed\t☃\n";
  page.finishLoad();
  await page.window.pnbpCodeTools.render();
  await page.buttons()[0].click();
  assert.deepEqual(page.copied, ["changed\t☃\n"]);
  assert.equal(pre.children[0].textContent, "changed\t☃\n");
});

test("enhancement is bounded and leaves excess code readable", async () => {
  const nodes = Array.from({ length: 101 }, () => block("code\n"));
  const page = browser(nodes, { highlighting: "off" });
  await page.window.pnbpCodeTools.render();
  assert.equal(page.buttons().length, 100);
  assert.equal(nodes[100].children[0].textContent, "code\n");
  const far = browser([...Array.from({ length: 10001 }, () => new Element("p")), block("code\n")]);
  await far.window.pnbpCodeTools.render();
  assert.equal(far.buttons().length, 0);
});

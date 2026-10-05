const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");
const loader = fs.readFileSync(path.join(__dirname, "../static/js/diagram-loader.js"), "utf8");

class Element {
  constructor(tag, text = "", classes = []) {
    this.tagName = tag.toUpperCase();
    this.text = text;
    this.classes = new Set(classes);
    this.classList = { add: (name) => this.classes.add(name) };
    this.children = [];
    this.parentElement = null;
    this.dataset = {};
    this.attributes = {};
  }
  get textContent() { return this.text + this.children.map((child) => child.textContent).join(""); }
  set textContent(value) { this.text = value; this.children = []; }
  set innerHTML(value) {
    this.text = "";
    this.children = [];
    if (value.startsWith("<svg")) this.appendChild(new Element("svg"));
  }
  appendChild(child) { child.parentElement = this; this.children.push(child); return child; }
  replaceChildren(...children) { this.text = ""; this.children = []; children.forEach((child) => this.appendChild(child)); }
  setAttribute(key, value) { this.attributes[key] = value; }
  hasAttribute(key) { return key in this.attributes; }
  matches(selector) {
    return selector === ".mermaid" ? this.classes.has("mermaid") :
      selector === "code.language-mermaid" ? this.tagName === "CODE" && this.classes.has("language-mermaid") :
      selector === "svg" && this.tagName === "SVG";
  }
  closest(selector) { return this.matches(selector) ? this : this.parentElement?.closest(selector); }
  querySelector(selector) {
    for (const child of this.children) {
      if (selector === "pre code" && child.tagName === "PRE") {
        const code = child.children.find((node) => node.tagName === "CODE");
        if (code) return code;
      }
      if (child.matches(selector)) return child;
      const nested = child.querySelector(selector);
      if (nested) return nested;
    }
    return null;
  }
  remove() { if (this.parentElement) this.parentElement.children = this.parentElement.children.filter((child) => child !== this); }
}

function browser(nodes = [], { blocked = false, theme = "default", renderFailure = false } = {}) {
  const root = new Element("article");
  nodes.forEach((node) => root.appendChild(node));
  const scripts = [];
  const rendered = [];
  const configurations = [];
  const events = {};
  const mermaid = {
    initialize: (options) => configurations.push(options),
    parse: async (source, options) => { assert.equal(options.suppressErrors, true); return source !== "malformed"; },
    render: async (id, source) => {
      if (renderFailure) throw new Error("render failed");
      rendered.push({ id, source });
      return { svg: "<svg></svg>" };
    },
  };
  const window = { addEventListener: (name, callback) => { events[name] = callback; } };
  const document = {
    readyState: "complete",
    currentScript: { dataset: { mermaidSrc: "/reviewed/mermaid.js", mermaidIntegrity: "sha384-reviewed", mermaidTheme: theme } },
    querySelector: () => root,
    createElement: (tag) => new Element(tag),
    getElementById: () => null,
    addEventListener: (name, callback) => { events[name] = callback; },
    createTreeWalker: () => {
      const all = [];
      const collect = (node) => node.children.forEach((child) => { all.push(child); collect(child); });
      collect(root);
      return { nextNode: () => all.shift() || null };
    },
    head: { appendChild: (script) => {
      scripts.push(script);
      Promise.resolve().then(() => {
        if (blocked) script.onerror();
        else { window.mermaid = mermaid; script.onload(); }
      });
    } },
  };
  vm.runInNewContext(loader, { window, document, NodeFilter: { SHOW_ELEMENT: 1 } });
  return { root, window, document, scripts, rendered, configurations, events };
}

test("plain legacy content and ordinary code never request Mermaid", async () => {
  const pre = new Element("pre");
  pre.appendChild(new Element("code", "graph TD; A-->B", ["language-python"]));
  const page = browser([new Element("p", "Plain"), pre]);
  await page.window.pnbpDiagrams.render();
  assert.equal(page.scripts.length, 0);
  assert.equal(page.rendered.length, 0);
});

test("diagrams load one reviewed asset and repeated navigation does not render twice", async () => {
  const node = new Element("pre", "graph TD; A-->B", ["mermaid"]);
  const page = browser([node]);
  await Promise.all([page.window.pnbpDiagrams.render(), page.window.pnbpDiagrams.render()]);
  page.events.pageshow();
  page.events["pnbp:content"]();
  await page.window.pnbpDiagrams.render();
  assert.equal(page.scripts.length, 1);
  assert.equal(page.scripts[0].src, "/reviewed/mermaid.js");
  assert.equal(page.scripts[0].integrity, "sha384-reviewed");
  assert.equal(page.scripts[0].crossOrigin, "anonymous");
  assert.equal(page.rendered.length, 1);
  assert.equal(node.dataset.diagramState, "rendered");
  assert.equal(node.querySelector("svg").attributes.role, "img");
  const options = page.configurations[0];
  assert.equal(options.securityLevel, "strict");
  assert.equal(options.startOnLoad, false);
  assert.equal(options.maxTextSize, 50000);
  assert.equal(options.maxEdges, 500);
  assert.ok(options.secure.includes("securityLevel") && options.secure.includes("theme"));
});

test("legacy language fences render once and theme changes reuse original source", async () => {
  const pre = new Element("pre");
  pre.appendChild(new Element("code", "graph TD; A-->B", ["language-mermaid"]));
  const page = browser([pre]);
  await page.window.pnbpDiagrams.render();
  assert.equal(page.window.pnbpDiagrams.setTheme("unreviewed"), false);
  assert.equal(page.window.pnbpDiagrams.setTheme("dark"), true);
  await page.window.pnbpDiagrams.render();
  assert.equal(page.scripts.length, 1);
  assert.equal(page.rendered.length, 2);
  assert.equal(page.rendered[1].source, "graph TD; A-->B");
  assert.equal(page.configurations.at(-1).theme, "dark");
  pre.textContent = "graph TD; Changed-->Source";
  page.events["pnbp:content"]();
  await page.window.pnbpDiagrams.render();
  assert.equal(page.rendered.at(-1).source, "graph TD; Changed-->Source");
});

test("oversized diagrams stay as source without loading the library", async () => {
  const source = "x".repeat(50001);
  const node = new Element("pre", source, ["mermaid"]);
  const page = browser([node]);
  await page.window.pnbpDiagrams.render();
  assert.equal(page.scripts.length, 0);
  assert.equal(node.dataset.diagramState, "source");
  assert.equal(node.querySelector("pre code").textContent, source);
});

for (const mode of ["malformed", "blocked", "renderFailure"]) {
  test(`${mode} keeps source readable and unrelated navigation intact`, async () => {
    const source = mode === "malformed" ? "malformed" : "graph TD; A-->B";
    const node = new Element("pre", source, ["mermaid"]);
    const navigation = new Element("a", "Home");
    const page = browser([navigation, node], { blocked: mode === "blocked", renderFailure: mode === "renderFailure" });
    await page.window.pnbpDiagrams.render();
    assert.equal(node.querySelector("pre code").textContent, source);
    assert.equal(node.dataset.diagramState, "source");
    assert.equal(navigation.textContent, "Home");
    await page.window.pnbpDiagrams.render();
    assert.equal(page.scripts.length, 1);
  });
}

test("legacy detection and rendering have finite node and diagram limits", async () => {
  const nodes = Array.from({ length: 40 }, () => new Element("pre", "graph TD; A-->B", ["mermaid"]));
  const page = browser(nodes);
  await page.window.pnbpDiagrams.render();
  assert.equal(page.rendered.length, 32);
  assert.equal(nodes[39].textContent, "graph TD; A-->B");
  const large = browser([...Array.from({ length: 10001 }, () => new Element("p")), new Element("pre", "graph TD; A-->B", ["mermaid"])]);
  await large.window.pnbpDiagrams.render();
  assert.equal(large.scripts.length, 0);
});

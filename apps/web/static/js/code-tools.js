/* Preserve code text while adding local copy controls and optional highlighting. */
(() => {
  "use strict";
  const options = document.currentScript.dataset;
  function preferredStyle(style) {
    const mode = document.documentElement?.dataset?.theme === "dark" ? "Dark" : "Light";
    style.href = options["highlightStyle" + mode] || options.highlightStyle;
    style.integrity = options["highlightIntegrity" + mode] || options.highlightStyleIntegrity;
  }
  if (window.pnbpCodeTools) { window.pnbpCodeTools.render(); return; }
  const states = new WeakMap();
  let libraryPromise = null;
  let running = null;
  let requested = false;
  let counter = 0;

  function language(code) {
    return [...code.classList].find(name => name.startsWith("language-"))?.slice(9) || "";
  }

  function enhance(code) {
    const previous = states.get(code);
    if (previous) {
      if (code.textContent !== previous.display || language(code) !== previous.language) {
        previous.source = code.textContent;
        previous.display = code.textContent;
        previous.language = language(code);
        previous.label.textContent = previous.language.slice(0, 100);
        previous.status.textContent = "";
        previous.highlighted = false;
      }
      return previous;
    }
    const pre = code.parentElement;
    const frame = document.createElement("div");
    const toolbar = document.createElement("div");
    const label = document.createElement("span");
    const button = document.createElement("button");
    const status = document.createElement("span");
    const state = { source: code.textContent, display: code.textContent, language: language(code), label, status, highlighted: false };
    frame.className = "code-block";
    toolbar.className = "code-toolbar";
    label.className = "code-label";
    label.textContent = state.language.slice(0, 100);
    button.className = "button button-secondary";
    button.type = "button";
    button.textContent = "Copy code";
    do { status.id = `pnbp-code-status-${++counter}`; }
    while (document.getElementById(status.id));
    status.className = "visually-hidden";
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    status.setAttribute("aria-atomic", "true");
    button.setAttribute("aria-describedby", status.id);
    pre.tabIndex = 0;
    pre.setAttribute("role", "region");
    pre.setAttribute("aria-label", "Code block");
    button.addEventListener("click", async () => {
      status.textContent = "";
      status.className = "code-status";
      button.disabled = true;
      try {
        if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
        await navigator.clipboard.writeText(state.source);
        status.textContent = "Code copied.";
      } catch {
        status.textContent = "Copy unavailable. Select the code and copy it.";
      } finally {
        button.disabled = false;
      }
    });
    toolbar.append(label, button, status);
    pre.before(frame);
    frame.append(toolbar, pre);
    states.set(code, state);
    return state;
  }

  function library() {
    if (window.hljs) return Promise.resolve(window.hljs);
    if (!libraryPromise) {
      const style = document.createElement("link");
      style.rel = "stylesheet";
      preferredStyle(style);
      document.addEventListener("pnbp:appearance", () => preferredStyle(style));
      style.crossOrigin = "anonymous";
      document.head.appendChild(style);
      libraryPromise = new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = options.highlightSrc;
        script.integrity = options.highlightIntegrity;
        script.crossOrigin = "anonymous";
        script.onload = () => window.hljs ? resolve(window.hljs) : reject(new Error("Highlight runtime unavailable"));
        script.onerror = () => { script.remove(); reject(new Error("Highlight asset unavailable")); };
        document.head.appendChild(script);
      });
    }
    return libraryPromise;
  }

  function canHighlight(code, state) {
    const optedOut = [code, code.parentElement].some(node =>
      node.classList.contains("nohighlight") || node.classList.contains("no-highlight"));
    return options.highlight === "on" && !state.highlighted && state.language && state.source.trim() &&
      !optedOut && state.source.length <= 100000 && !code.closest(".mermaid") && state.language !== "mermaid";
  }

  async function draw() {
    const root = document.querySelector("[data-publication]");
    if (!root) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
    const pending = [];
    let node;
    let visits = 0;
    let blocks = 0;
    let total = 0;
    while ((node = walker.nextNode()) && ++visits <= 10000 && blocks < 100) {
      if (!node.matches("pre > code") || node.closest(".mermaid") || node.classList.contains("language-mermaid")) continue;
      blocks++;
      const state = enhance(node);
      if (!canHighlight(node, state) || total + state.source.length > 500000) continue;
      total += state.source.length;
      pending.push([node, state]);
    }
    if (!pending.length) return;
    let hljs;
    try { hljs = await library(); }
    catch { return; }
    total = 0;
    for (const [code, state] of pending) {
      // Content can change while the optional runtime is still loading.
      enhance(code);
      if (!canHighlight(code, state) || total + state.source.length > 500000) continue;
      total += state.source.length;
      try {
        if (!hljs.getLanguage(state.language)) continue;
        hljs.highlightElement(code);
        // Copy always uses the snapshot. Keep the visible text exact as well.
        if (code.textContent !== state.source) code.textContent = state.source;
      } catch {
        code.textContent = state.source;
      }
      state.display = code.textContent;
      state.highlighted = true;
    }
  }

  function render() {
    requested = true;
    if (!running) {
      running = (async () => {
        while (requested) { requested = false; await draw(); }
      })().finally(() => { running = null; });
    }
    return running;
  }
  window.pnbpCodeTools = { render };
  window.addEventListener("pageshow", render);
  document.addEventListener("pnbp:content", render);
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", render, { once: true });
  else render();
})();

/* Load reviewed Mermaid assets only for bounded published diagram sources. */
(() => {
  "use strict";
  const settings = document.currentScript.dataset;
  const themes = new Set(["default", "dark", "forest", "neutral", "base"]);
  const options = {
    source: settings.mermaidSrc,
    integrity: settings.mermaidIntegrity,
    theme: themes.has(settings.mermaidTheme) ? settings.mermaidTheme : "default",
  };
  if (window.pnbpDiagrams) {
    window.pnbpDiagrams.setTheme(options.theme);
    window.pnbpDiagrams.render();
    return;
  }
  const states = new WeakMap();
  const maxDiagrams = 32;
  const maxText = 50000;
  const maxTotalText = 100000;
  let libraryPromise = null;
  let running = null;
  let requested = false;
  let counter = 0;

  function sources() {
    const root = document.querySelector("[data-publication]");
    if (!root) return [];
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
    const found = [];
    let node;
    let visits = 0;
    while ((node = walker.nextNode()) && ++visits <= 10000 && found.length < maxDiagrams) {
      if (!(node.matches(".mermaid") || node.matches("code.language-mermaid")) ||
          node.closest("svg") || node.parentElement?.closest(".mermaid")) continue;
      const target = node.tagName === "CODE" && node.parentElement?.tagName === "PRE" ? node.parentElement : node;
      target.classList.add("mermaid");
      const previous = states.get(target);
      const intact = target.dataset.diagramState === "rendered" && target.querySelector("svg") ||
        target.dataset.diagramState === "source" && target.querySelector("pre code")?.textContent === previous?.source;
      if (!previous || !intact) states.set(target, { source: target.textContent, theme: null });
      found.push(target);
    }
    return found;
  }

  function fallback(node, theme) {
    const state = states.get(node);
    const pre = document.createElement("pre");
    const code = document.createElement("code");
    const message = document.createElement("p");
    code.textContent = state.source;
    pre.appendChild(code);
    message.textContent = "Diagram unavailable; source shown.";
    message.setAttribute("role", "status");
    node.replaceChildren(message, pre);
    node.dataset.diagramState = "source";
    node.setAttribute("aria-busy", "false");
    state.theme = theme;
  }

  function library() {
    if (window.mermaid) return Promise.resolve(window.mermaid);
    if (!libraryPromise) {
      libraryPromise = new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = options.source;
        script.integrity = options.integrity;
        script.crossOrigin = "anonymous";
        script.onload = () => window.mermaid ? resolve(window.mermaid) : reject(new Error("Diagram runtime unavailable"));
        script.onerror = () => { script.remove(); reject(new Error("Diagram asset unavailable")); };
        document.head.appendChild(script);
      });
    }
    return libraryPromise;
  }

  async function draw() {
    const theme = options.theme;
    const pending = [];
    let total = 0;
    for (const node of sources()) {
      const state = states.get(node);
      if (state.theme === theme) continue;
      total += state.source.length;
      if (!state.source.trim() || state.source.length > maxText || total > maxTotalText) {
        fallback(node, theme);
      } else {
        node.setAttribute("aria-busy", "true");
        pending.push(node);
      }
    }
    if (!pending.length) return;
    let mermaid;
    try {
      mermaid = await library();
      mermaid.initialize({
        startOnLoad: false, securityLevel: "strict", theme,
        maxTextSize: maxText, maxEdges: 500, suppressErrorRendering: true,
        secure: ["secure", "securityLevel", "startOnLoad", "maxTextSize", "maxEdges", "suppressErrorRendering", "theme"],
      });
    } catch {
      for (const node of pending) fallback(node, theme);
      return;
    }
    for (const node of pending) {
      const state = states.get(node);
      let id;
      do { id = `pnbp-diagram-${++counter}`; }
      while (document.getElementById(id) || document.getElementById("d" + id));
      try {
        if (!await mermaid.parse(state.source, { suppressErrors: true })) throw new Error("Invalid diagram");
        const { svg } = await mermaid.render(id, state.source);
        node.innerHTML = svg;
        const image = node.querySelector("svg");
        if (!image) throw new Error("Missing rendered diagram");
        image.setAttribute("role", "img");
        if (!image.hasAttribute("aria-label") && !image.hasAttribute("aria-labelledby")) image.setAttribute("aria-label", "Diagram");
        node.dataset.diagramState = "rendered";
        node.setAttribute("aria-busy", "false");
        state.theme = theme;
      } catch {
        document.getElementById(id)?.remove();
        document.getElementById("d" + id)?.remove();
        fallback(node, theme);
      }
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

  function setTheme(theme) {
    if (!themes.has(theme)) return false;
    options.theme = theme;
    render();
    return true;
  }

  window.pnbpDiagrams = { render, setTheme };
  window.addEventListener("pageshow", render);
  document.addEventListener("pnbp:content", render);
  document.addEventListener("pnbp:theme", (event) => setTheme(event.detail?.theme));
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", render, { once: true });
  else render();
})();

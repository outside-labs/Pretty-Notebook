/* Apply system mode before content is painted; explicit choices use cookies. */
(function (root) {
  "use strict";
  if (typeof module !== "undefined") module.exports = { applySystem, syncToggle };
  function syncToggle(document) {
    const button = document.querySelector?.('[data-theme-toggle]');
    if (!button) return;
    const dark = document.documentElement.dataset.theme === "dark";
    button.value = dark ? "lightmode" : "darkmode";
    const label = dark ? "Light theme" : "Dark theme";
    button.setAttribute("aria-label", label);
    button.querySelector('[data-theme-label]').textContent = label;
  }
  function applySystem(document, media) {
    if (document.documentElement.dataset.mode !== "system") return;
    const apply = () => {
      document.documentElement.dataset.theme = media.matches ? "dark" : "light";
      syncToggle(document);
      if (document.dispatchEvent) document.dispatchEvent(new CustomEvent("pnbp:appearance"));
    };
    apply();
    if (media.addEventListener) media.addEventListener("change", apply);
  }
  if (root.document && root.matchMedia) applySystem(root.document, root.matchMedia("(prefers-color-scheme: dark)"));
  if (root.document) root.document.addEventListener("DOMContentLoaded", () => syncToggle(root.document));
})(typeof window === "undefined" ? globalThis : window);

/* Apply system mode before content is painted; explicit choices use cookies. */
(function (root) {
  "use strict";
  if (typeof module !== "undefined") module.exports = { applySystem };
  function applySystem(document, media) {
    if (document.documentElement.dataset.mode !== "system") return;
    const apply = () => {
      document.documentElement.dataset.theme = media.matches ? "dark" : "light";
      if (document.dispatchEvent) document.dispatchEvent(new CustomEvent("pnbp:appearance"));
    };
    apply();
    if (media.addEventListener) media.addEventListener("change", apply);
  }
  if (root.document && root.matchMedia) applySystem(root.document, root.matchMedia("(prefers-color-scheme: dark)"));
})(typeof window === "undefined" ? globalThis : window);

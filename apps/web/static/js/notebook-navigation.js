/* Use browser Back for an internal visit, retaining the known index fallback. */
(() => {
  "use strict";
  document.querySelectorAll("[data-notebook-back]").forEach(link => {
    link.addEventListener("click", event => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      try {
        if (!document.referrer || window.history.length <= 1) return;
        const previous = new URL(document.referrer);
        const current = new URL(window.location.href);
        const prefix = link.dataset.rootPath || "";
        if (previous.origin !== current.origin || previous.href === current.href ||
            previous.pathname.includes("%") || previous.pathname.includes("\\") ||
            (prefix && !previous.pathname.startsWith(prefix + "/"))) return;
        window.history.back();
        event.preventDefault();
      } catch {
        // A blocked history API or invalid referrer leaves the normal link intact.
      }
    });
  });
})();

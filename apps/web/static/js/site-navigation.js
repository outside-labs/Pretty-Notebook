/* Native disclosure works at every width; Escape restores focus to its summary. */
(function (root) {
  "use strict";
  function initialize(nav) {
    const menu = nav.querySelector('.site-menu');
    if (!menu) return;
    nav.addEventListener('keydown', event => {
      if (event.key !== 'Escape') return;
      const details = event.target.closest?.('details[open]');
      if (details) {
        details.open = false;
        details.querySelector('summary')?.focus();
      } else if (menu.open) {
        menu.open = false;
        menu.querySelector('summary')?.focus();
      } else return;
      event.preventDefault();
    });
  }
  if (typeof module !== 'undefined') module.exports = { initialize };
  if (root.document) {
    root.document.querySelectorAll('.site-nav').forEach(initialize);
  }
})(typeof window === 'undefined' ? globalThis : window);

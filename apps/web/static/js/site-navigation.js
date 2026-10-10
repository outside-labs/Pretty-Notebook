/* Progressive disclosure: links remain visible when JavaScript is unavailable. */
(function (root) {
  "use strict";
  function initialize(nav, media) {
    const button = nav.querySelector('.nav-toggle');
    const panel = nav.querySelector('.nav-panel');
    if (!button || !panel) return;
    let expanded = false;
    function render() {
      button.hidden = !media.matches;
      panel.hidden = media.matches && !expanded;
      button.setAttribute('aria-expanded', String(!panel.hidden));
    }
    button.addEventListener('click', () => { expanded = !expanded; render(); });
    nav.addEventListener('keydown', event => {
      if (event.key !== 'Escape') return;
      const details = event.target.closest?.('details[open]');
      if (details) {
        details.open = false;
        details.querySelector('summary')?.focus();
      } else if (media.matches && expanded) {
        expanded = false;
        render();
        button.focus();
      } else return;
      event.preventDefault();
    });
    if (media.addEventListener) media.addEventListener('change', () => { expanded = false; render(); });
    render();
  }
  if (typeof module !== 'undefined') module.exports = { initialize };
  if (root.document && root.matchMedia) {
    root.document.querySelectorAll('[data-nav-breakpoint]').forEach(nav => {
      initialize(nav, root.matchMedia('(max-width: ' + nav.dataset.navBreakpoint + 'px)'));
    });
  }
})(typeof window === 'undefined' ? globalThis : window);

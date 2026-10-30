/* UI enhancements; compiler data and algorithms remain in app.js and the API. */
(() => {
  'use strict';
  const root = document.documentElement;
  const themeButton = document.getElementById('btn-theme');
  const systemTheme = matchMedia('(prefers-color-scheme: light)');
  let explicitTheme = false;
  try { explicitTheme = ['light', 'dark'].includes(localStorage.getItem('studio-theme')); } catch (_) {}
  function applyTheme(theme) {
    root.dataset.theme = theme;
    themeButton.textContent = theme === 'dark' ? '☀ Light' : '☾ Dark';
    themeButton.setAttribute('aria-label', `Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`);
    themeButton.title = `Current theme: ${theme}`;
    document.dispatchEvent(new Event('studio:theme'));
  }
  themeButton.addEventListener('click', () => {
    explicitTheme = true;
    const theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    try { localStorage.setItem('studio-theme', theme); } catch (_) {}
    applyTheme(theme);
  });
  systemTheme.addEventListener('change', () => {
    if (!explicitTheme) applyTheme(systemTheme.matches ? 'light' : 'dark');
  });
  applyTheme(root.dataset.theme);

  // Make existing filter controls operable with a keyboard.
  document.querySelectorAll('.filter-chip').forEach((chip) => {
    chip.setAttribute('role', 'button');
    chip.tabIndex = 0;
    chip.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); chip.click(); }
    });
  });
  document.querySelectorAll('input[placeholder]').forEach((input) => {
    if (!input.labels?.length && !input.hasAttribute('aria-label')) input.setAttribute('aria-label', input.placeholder);
  });

  // Reveals are observed once; no continuous scroll or pointer work.
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(({target, isIntersecting}) => {
      if (!isIntersecting) return;
      target.classList.add('reveal-visible');
      observer.unobserve(target);
    });
  }, {threshold: 0.08});
  const observeCards = () => document.querySelectorAll('.sample-card:not([data-reveal])').forEach((card, index) => {
    card.dataset.reveal = 'true';
    card.style.setProperty('--reveal-delay', `${Math.min(index % 3 * 55, 110)}ms`);
    observer.observe(card);
  });
  const samples = document.getElementById('samples-grid');
  new MutationObserver(observeCards).observe(samples, {childList: true});
  observeCards();

  // Escape, focus containment and focus restoration for the comparison dialog.
  const modal = document.getElementById('diff-modal');
  const trigger = document.getElementById('btn-open-diff-modal');
  const close = () => {
    modal.classList.remove('active');
    trigger.focus();
  };
  trigger.addEventListener('click', () => document.getElementById('diff-editor-a').focus());
  modal.querySelector('.modal-close-btn').addEventListener('click', close);
  modal.addEventListener('click', (event) => { if (event.target === modal) close(); });
  modal.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') { event.preventDefault(); close(); }
    if (event.key !== 'Tab') return;
    const items = [...modal.querySelectorAll('button:not(:disabled), textarea, [tabindex="0"]')];
    const first = items[0], last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });
})();

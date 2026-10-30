/* Apply preferences before paint. No storage access is required to use the app. */
(() => {
  let theme;
  let motion;
  try {
    theme = localStorage.getItem('studio-theme');
    motion = localStorage.getItem('studio-motion');
  } catch (_) { /* Private contexts can block storage. */ }
  document.documentElement.dataset.theme = ['light', 'dark'].includes(theme)
    ? theme : (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
  document.documentElement.dataset.motion = motion === 'off' || matchMedia('(prefers-reduced-motion: reduce)').matches ? 'off' : 'on';
})();

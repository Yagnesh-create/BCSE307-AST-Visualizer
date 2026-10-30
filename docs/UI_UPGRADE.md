# Compiler Studio UI upgrade

The existing Flask API and Python compiler algorithms are unchanged. Playground, Sample Library, and Validation Suite remain the primary sections. Learn and About remain removed as requested.

## Themes and motion

The header Light/Dark button switches the entire studio, including AST node palettes, tables, diagnostics, statistics, comparison modal, and embedded HTML output. Theme preference is saved in localStorage; a first visit follows the operating-system color preference. `theme.js` applies it before styles load to avoid a wrong-theme first paint. Storage restrictions do not prevent using either theme.

Sample cards reveal as they enter view. Navigation, dialogs, AST nodes, and compilation metrics use short animations. Node and token counters use actual compilation results. The Motion button and the system reduced-motion preference disable motion.

## Interaction improvements

- Keyboard-operable filter controls and hierarchical node selection.
- Correct node details for collapsible AST cards, plus visible SVG selection.
- Comparison dialog has labels, focus containment, Escape dismissal, and return focus.
- Narrow-screen sample cards, wrapped pipeline stages, stacked comparison fields, and scrollable editor status text.
- Theme-aware SVG export and HTML output preview.

## Files

- `templates/index.html`: theme assets, toggle, semantic dialog labels.
- `static/js/theme.js`: first-paint preferences.
- `static/js/experience.js`: theme control, reveals, accessible filters and modal behavior.
- `static/js/app.js`: real-data counters, AST palettes, node lookup fix, themed exports/preview.
- `static/css/experience.css`: shared theme tokens, visual polish and responsive refinements.

## Validation

- All three JavaScript files pass `node --check`.
- Page, health, samples, and new static assets return HTTP 200.
- Valid compilation, syntax-error reporting, and AST comparison pass API smoke checks.
- Existing suite: 39/39 passed, including a browser-triggered run.
- Browser: dark/light switching, light preference across reload, comparison and Escape dismissal, correct hierarchical Param selection, and no captured console errors.
- Responsive check at 390px: page width matches viewport; no page-level horizontal overflow. Desktop inspected at the browser's default 1280px width.

Preview is local at http://127.0.0.1:5000/. Run `python server.py` from the project directory after installing `requirements.txt`. External web fonts retain local fallback fonts when offline. This is not an exhaustive audit of every browser or device.

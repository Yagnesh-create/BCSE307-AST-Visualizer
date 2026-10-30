/**
 * AST VISUALIZER & COMPILER STUDIO - MASTER CLIENT SCRIPT
 * Course: BCSE307 Compiler Design | Team 16 | Project ID: M13
 * Pure Vanilla JavaScript Client Application
 */

(function () {
  'use strict';

  // =========================================================================
  // APPLICATION STATE
  // =========================================================================
  const state = {
    currentSource: '',
    samplesList: [],
    lastCompilation: null,
    selectedNode: null,
    activeView: 'view-playground',
    activeResultTab: 'panel-ast-visualizer',
    activeAstMode: 'graphical', // 'graphical' | 'hierarchical'
    activeOutputFormat: 'tree',
    tokenFilter: 'ALL',
    tokenSearchQuery: '',
    astSearchQuery: '',
    fontSize: 13,
    // SVG Pan & Zoom State
    zoomScale: 1,
    panX: 40,
    panY: 40,
    isPanning: false,
    panStartX: 0,
    panStartY: 0
  };

  // Node Category Mapping
  const NODE_CATEGORIES = {
    Program: 'structure',
    Block: 'structure',
    FunctionDecl: 'function',
    Param: 'function',
    VarDecl: 'variable',
    Assign: 'variable',
    Assignment: 'variable',
    IfStmt: 'control',
    WhileStmt: 'control',
    ForStmt: 'control',
    ReturnStmt: 'control',
    ExprStmt: 'control',
    BinaryOp: 'expression',
    UnaryOp: 'expression',
    Call: 'expression',
    CallExpr: 'expression',
    Literal: 'literal',
    Identifier: 'literal'
  };

  function getNodeCategory(head) {
    if (!head) return 'other';
    for (const [key, cat] of Object.entries(NODE_CATEGORIES)) {
      if (head.startsWith(key)) return cat;
    }
    return 'other';
  }

  // =========================================================================
  // DOM ELEMENT REFERENCES
  // =========================================================================
  const dom = {
    // Nav Tabs
    navTabs: document.querySelectorAll('.nav-tab-btn'),
    views: document.querySelectorAll('.view-section'),
    
    // Status Pill
    statusPill: document.getElementById('status-pill'),
    statusDot: document.getElementById('status-dot'),
    statusText: document.getElementById('status-text'),
    
    // Editor Elements
    editor: document.getElementById('code-editor'),
    lineNumbers: document.getElementById('line-numbers'),
    cursorPos: document.getElementById('cursor-pos'),
    lineCount: document.getElementById('line-count'),
    charCount: document.getElementById('char-count'),
    sampleSelect: document.getElementById('sample-select'),
    btnCompile: document.getElementById('btn-compile'),
    btnClear: document.getElementById('btn-clear'),
    btnReset: document.getElementById('btn-reset'),
    btnFormat: document.getElementById('btn-format'),
    btnFontPlus: document.getElementById('btn-font-plus'),
    btnFontMinus: document.getElementById('btn-font-minus'),
    
    // Pipeline Ribbon
    pipelineRibbon: document.getElementById('pipeline-ribbon'),
    
    // Results Area
    resultTabs: document.querySelectorAll('.result-tab-btn'),
    resultPanels: document.querySelectorAll('.result-panel'),
    errBadgeCounter: document.getElementById('err-badge-counter'),
    tokenBadgeCounter: document.getElementById('token-badge-counter'),
    
    // AST Visualizer
    btnModeGraphical: document.getElementById('btn-mode-graphical'),
    btnModeHierarchical: document.getElementById('btn-mode-hierarchical'),
    graphicalViewport: document.getElementById('ast-graphical-viewport'),
    svgCanvas: document.getElementById('ast-svg-canvas'),
    hierarchicalContainer: document.getElementById('ast-hierarchical-container'),
    hierarchicalTreeRoot: document.getElementById('ast-tree-root'),
    astSearchInput: document.getElementById('ast-search-input'),
    btnZoomIn: document.getElementById('btn-zoom-in'),
    btnZoomOut: document.getElementById('btn-zoom-out'),
    btnZoomReset: document.getElementById('btn-zoom-reset'),
    btnZoomFit: document.getElementById('btn-zoom-fit'),
    btnExpandAllAst: document.getElementById('btn-expand-all-ast'),
    btnCollapseAllAst: document.getElementById('btn-collapse-all-ast'),
    
    // Inspector Drawer
    inspNodeKind: document.getElementById('insp-node-kind'),
    inspNodeCat: document.getElementById('insp-node-cat'),
    inspNodeAtoms: document.getElementById('insp-node-atoms'),
    inspNodeLoc: document.getElementById('insp-node-loc'),
    inspNodeSubnodes: document.getElementById('insp-node-subnodes'),
    inspNodeDepth: document.getElementById('insp-node-depth'),
    inspChildrenList: document.getElementById('insp-children-list'),
    inspJsonSnippet: document.getElementById('insp-json-snippet'),
    btnHighlightSource: document.getElementById('btn-highlight-source'),
    
    // Token Explorer
    tokenTableBody: document.getElementById('token-table-body'),
    tokenSearchInput: document.getElementById('token-search-input'),
    tokenFilterChips: document.querySelectorAll('.token-filter-chips .filter-chip'),
    
    // Errors Tab
    errorsList: document.getElementById('errors-list'),
    errorsEmptyState: document.getElementById('errors-empty-state'),
    
    // Output Formats Tab
    formatPillBtns: document.querySelectorAll('.format-pill-btn'),
    outputViewerBox: document.getElementById('output-viewer-box'),
    outputFrameWrap: document.getElementById('output-frame-wrap'),
    htmlPreviewFrame: document.getElementById('html-preview-frame'),
    btnCopyOutput: document.getElementById('btn-copy-output'),
    btnDownloadOutput: document.getElementById('btn-download-output'),
    
    // Stats Tab
    statNodeCount: document.getElementById('stat-node-count'),
    statAstDepth: document.getElementById('stat-ast-depth'),
    statTokenCount: document.getElementById('stat-token-count'),
    statLinesCount: document.getElementById('stat-lines-count'),
    statTotalTime: document.getElementById('stat-total-time'),
    statIssuesCount: document.getElementById('stat-issues-count'),
    timeLexMs: document.getElementById('time-lex-ms'),
    timeParseMs: document.getElementById('time-parse-ms'),
    timeSemMs: document.getElementById('time-sem-ms'),
    barSliceLex: document.getElementById('bar-slice-lex'),
    barSliceParse: document.getElementById('bar-slice-parse'),
    barSliceSem: document.getElementById('bar-slice-sem'),
    tokenHistogramBody: document.getElementById('token-histogram-body'),
    
    // Samples Page Grid
    samplesGrid: document.getElementById('samples-grid'),
    sampleFilterChips: document.querySelectorAll('.sample-filter-chips .filter-chip'),
    sampleSearchInput: document.getElementById('sample-search-input'),
    
    // Test Suite Page
    btnRunTestSuite: document.getElementById('btn-run-test-suite'),
    testProgressBar: document.getElementById('test-progress-bar'),
    testSummaryText: document.getElementById('test-summary-text'),
    testFilterChips: document.querySelectorAll('.test-filter-chips .filter-chip'),
    testTableBody: document.getElementById('test-table-body'),
    btnViewRawTerminal: document.getElementById('btn-view-raw-terminal'),
    
    // Diff Modal
    btnOpenDiffModal: document.getElementById('btn-open-diff-modal'),
    diffModal: document.getElementById('diff-modal'),
    diffEditorA: document.getElementById('diff-editor-a'),
    diffEditorB: document.getElementById('diff-editor-b'),
    btnRunDiff: document.getElementById('btn-run-diff'),
    diffResultsContainer: document.getElementById('diff-results-container'),
    
    // Toast
    toast: document.getElementById('toast-notice')
  };

  // =========================================================================
  // TOAST NOTIFICATIONS
  // =========================================================================
  function showToast(message, duration = 2200) {
    if (!dom.toast) return;
    dom.toast.textContent = message;
    dom.toast.classList.add('show');
    clearTimeout(dom.toast._timer);
    dom.toast._timer = setTimeout(() => {
      dom.toast.classList.remove('show');
    }, duration);
  }

  // =========================================================================
  // NAVIGATION & VIEW SWITCHER
  // =========================================================================
  function initNavigation() {
    dom.navTabs.forEach((tab) => {
      tab.addEventListener('click', () => {
        const targetViewId = tab.dataset.view;
        switchView(targetViewId);
      });
    });

    // Delegated links with data-view-target
    document.addEventListener('click', (e) => {
      const targetBtn = e.target.closest('[data-view-target]');
      if (targetBtn) {
        const viewId = targetBtn.dataset.viewTarget;
        switchView(viewId);
      }
    });
  }

  function switchView(viewId) {
    state.activeView = viewId;
    dom.navTabs.forEach((t) => t.classList.toggle('active', t.dataset.view === viewId));
    dom.views.forEach((v) => v.classList.toggle('active', v.id === viewId));

    if (viewId === 'view-playground') {
      updateLineNumbers();
      renderAst();
    }
  }

  // =========================================================================
  // CODE EDITOR & LINE NUMBERS ENGINE
  // =========================================================================
  function initEditor() {
    if (!dom.editor) return;

    dom.editor.addEventListener('input', () => {
      state.currentSource = dom.editor.value;
      const verdict = document.getElementById('compile-verdict');
      verdict.textContent = 'Source changed · compile to update';
      verdict.dataset.status = 'pending';
      updateLineNumbers();
      updateCursorPosition();
    });

    dom.editor.addEventListener('scroll', () => {
      if (dom.lineNumbers) {
        dom.lineNumbers.scrollTop = dom.editor.scrollTop;
      }
    });

    dom.editor.addEventListener('click', updateCursorPosition);
    dom.editor.addEventListener('keyup', updateCursorPosition);

    // Keyboard Shortcuts
    dom.editor.addEventListener('keydown', (e) => {
      // Ctrl+Enter or Cmd+Enter: Compile
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        compileCode();
        return;
      }

      // Tab indentation (4 spaces)
      if (e.key === 'Tab') {
        e.preventDefault();
        const start = dom.editor.selectionStart;
        const end = dom.editor.selectionEnd;
        const value = dom.editor.value;

        if (e.shiftKey) {
          // Outdent
          const before = value.substring(0, start);
          const after = value.substring(end);
          if (before.endsWith('    ')) {
            dom.editor.value = before.substring(0, before.length - 4) + after;
            dom.editor.selectionStart = dom.editor.selectionEnd = start - 4;
          }
        } else {
          // Indent 4 spaces
          dom.editor.value = value.substring(0, start) + '    ' + value.substring(end);
          dom.editor.selectionStart = dom.editor.selectionEnd = start + 4;
        }
        state.currentSource = dom.editor.value;
        updateLineNumbers();
        updateCursorPosition();
      }
    });

    // Toolbar Buttons
    if (dom.btnCompile) dom.btnCompile.addEventListener('click', () => compileCode());

    if (dom.btnClear) {
      dom.btnClear.addEventListener('click', () => {
        dom.editor.value = '';
        state.currentSource = '';
        updateLineNumbers();
        updateCursorPosition();
        showToast('Editor cleared');
      });
    }

    if (dom.btnReset) {
      dom.btnReset.addEventListener('click', () => {
        loadSampleByName('demo.lang');
        showToast('Reset to demo.lang');
      });
    }

    if (dom.btnFormat) {
      dom.btnFormat.addEventListener('click', () => {
        // Simple beautifier: normalize line endings and trim trailing whitespace
        const formatted = dom.editor.value
          .split('\n')
          .map((line) => line.trimEnd())
          .join('\n')
          .trim();
        dom.editor.value = formatted;
        state.currentSource = formatted;
        updateLineNumbers();
        showToast('Code formatted');
      });
    }

    if (dom.btnFontPlus) {
      dom.btnFontPlus.addEventListener('click', () => {
        if (state.fontSize < 20) {
          state.fontSize += 1;
          dom.editor.style.fontSize = `${state.fontSize}px`;
          dom.lineNumbers.style.fontSize = `${state.fontSize}px`;
          updateLineNumbers();
        }
      });
    }

    if (dom.btnFontMinus) {
      dom.btnFontMinus.addEventListener('click', () => {
        if (state.fontSize > 10) {
          state.fontSize -= 1;
          dom.editor.style.fontSize = `${state.fontSize}px`;
          dom.lineNumbers.style.fontSize = `${state.fontSize}px`;
          updateLineNumbers();
        }
      });
    }

    if (dom.sampleSelect) {
      dom.sampleSelect.addEventListener('change', (e) => {
        const val = e.target.value;
        if (val) loadSampleByName(val);
      });
    }
  }

  function updateLineNumbers() {
    if (!dom.lineNumbers || !dom.editor) return;
    const lines = dom.editor.value.split('\n');
    const count = lines.length;
    let html = '';
    for (let i = 1; i <= count; i++) {
      html += `<div class="line-number" id="ln-${i}">${i}</div>`;
    }
    dom.lineNumbers.innerHTML = html;
    if (dom.lineCount) dom.lineCount.textContent = `${count} ln`;
    if (dom.charCount) dom.charCount.textContent = `${dom.editor.value.length} ch`;
  }

  function updateCursorPosition() {
    if (!dom.cursorPos || !dom.editor) return;
    const pos = dom.editor.selectionStart;
    const textBefore = dom.editor.value.substring(0, pos);
    const lines = textBefore.split('\n');
    const curLine = lines.length;
    const curCol = lines[lines.length - 1].length + 1;
    dom.cursorPos.textContent = `Ln ${curLine}, Col ${curCol}`;
  }

  function highlightLine(lineNum) {
    if (!lineNum || !dom.editor) return;
    // Highlight gutter
    document.querySelectorAll('.line-number.error-ln').forEach((el) => el.classList.remove('error-ln'));
    const gutterEl = document.getElementById(`ln-${lineNum}`);
    if (gutterEl) gutterEl.classList.add('error-ln');

    // Scroll editor to line
    const lines = dom.editor.value.split('\n');
    let charOffset = 0;
    for (let i = 0; i < Math.min(lineNum - 1, lines.length); i++) {
      charOffset += lines[i].length + 1;
    }
    dom.editor.focus();
    dom.editor.setSelectionRange(charOffset, charOffset + (lines[lineNum - 1] || '').length);
  }

  // =========================================================================
  // SAMPLES ENGINE
  // =========================================================================
  async function loadSamplesList() {
    try {
      const res = await fetch('/api/samples');
      const data = await res.json();
      state.samplesList = data.samples || [];

      // Populate Editor Select Dropdown
      if (dom.sampleSelect) {
        dom.sampleSelect.innerHTML = '<option value="" disabled>-- Select Sample --</option>';
        state.samplesList.forEach((sample) => {
          const opt = document.createElement('option');
          opt.value = sample.filename;
          opt.textContent = `${sample.title} (${sample.filename})`;
          dom.sampleSelect.appendChild(opt);
        });
      }

      // Populate Samples Library Page Grid
      renderSamplesGrid();

      // Load initial demo.lang if editor is empty
      if (!dom.editor.value.trim()) {
        loadSampleByName('demo.lang');
      }
    } catch (err) {
      console.error('Failed to load samples:', err);
    }
  }

  function loadSampleByName(filename) {
    const sample = state.samplesList.find((s) => s.filename === filename);
    if (!sample) return;

    dom.editor.value = sample.code;
    state.currentSource = sample.code;
    if (dom.sampleSelect) dom.sampleSelect.value = filename;

    updateLineNumbers();
    updateCursorPosition();
    compileCode();
  }

  function renderSamplesGrid() {
    if (!dom.samplesGrid) return;
    const query = (dom.sampleSearchInput ? dom.sampleSearchInput.value : '').toLowerCase();

    const filtered = state.samplesList.filter((s) => {
      const matchCat = state.sampleCategoryFilter === 'ALL' || !state.sampleCategoryFilter || s.category === state.sampleCategoryFilter;
      const matchQuery = !query || s.title.toLowerCase().includes(query) || s.description.toLowerCase().includes(query) || s.filename.toLowerCase().includes(query);
      return matchCat && matchQuery;
    });

    if (filtered.length === 0) {
      dom.samplesGrid.innerHTML = `
        <div class="empty-state" style="grid-column: 1 / -1;">
          <div class="empty-icon">🔍</div>
          <div class="empty-title">No Samples Found</div>
          <div class="empty-desc">Try clearing your search query or switching categories.</div>
        </div>`;
      return;
    }

    dom.samplesGrid.innerHTML = filtered.map((s) => `
      <div class="sample-card">
        <div class="sample-card-head">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span class="badge-tag badge-m13">${escapeHtml(s.category)}</span>
            <span style="font-size:11px; font-family:var(--font-mono); color:var(--text-muted);">${escapeHtml(s.filename)}</span>
          </div>
          <h3 class="sample-card-title">${escapeHtml(s.title)}</h3>
          <p class="sample-card-desc">${escapeHtml(s.description)}</p>
          <div style="font-size:11.5px; color:var(--accent-cyan); font-family:var(--font-mono); margin-top:4px;">
            Target: ${escapeHtml(s.expectedOutcome)}
          </div>
        </div>
        <div class="sample-card-preview">${escapeHtml(s.code)}</div>
        <button class="btn btn-primary" onclick="window.appLoadAndRunSample('${escapeHtml(s.filename)}')">
          <span>⚡ Load into Playground & Run</span>
        </button>
      </div>
    `).join('');
  }

  // Window bridge for inline onclick handlers
  window.appLoadAndRunSample = function (filename) {
    loadSampleByName(filename);
    switchView('view-playground');
  };

  // =========================================================================
  // COMPILER INTEGRATION & API
  // =========================================================================
  async function compileCode() {
    if (state.isCompiling) return;
    state.isCompiling = true;
    document.body.classList.add('is-compiling');
    dom.pipelineRibbon?.setAttribute('aria-busy', 'true');
    const source = dom.editor ? dom.editor.value : '';
    const verdict = document.getElementById('compile-verdict');
    verdict.textContent = 'Analyzing your source…';
    verdict.dataset.status = 'pending';

    // Set UI to Compiling State
    if (dom.statusDot) {
      dom.statusDot.className = 'status-dot compiling';
    }
    if (dom.statusText) {
      dom.statusText.textContent = 'Compiling...';
    }
    if (dom.btnCompile) {
      dom.btnCompile.disabled = true;
      dom.btnCompile.innerHTML = '<span class="status-dot compiling" style="width:10px;height:10px;"></span> <span>Processing...</span>';
    }

    try {
      const res = await fetch('/api/compile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: source })
      });

      if (!res.ok) throw new Error(`Compilation request failed (${res.status})`);
      const data = await res.json();
      state.lastCompilation = data;
      verdict.textContent = data.success ? 'Compilation successful' : `${data.errors.length} diagnostic${data.errors.length === 1 ? '' : 's'} to review`;
      verdict.dataset.status = data.success ? 'success' : 'error';
      state.selectedNode = null;
      animateMetric(document.getElementById('studio-nodes'), data.stats.node_count);
      animateMetric(document.getElementById('studio-tokens'), data.stats.token_count);
      document.getElementById('studio-time').textContent = `${data.stats.total_ms} ms`;

      // Update Pipeline Ribbon
      renderPipeline(data.pipeline);

      // Update Diagnostics & Errors
      renderErrors(data.errors, data.has_syntax_errors, data.has_semantic_issues);

      // Update Tokens
      renderTokens(data.tokens);

      // Update Output Formats
      renderOutputs(data.outputs);

      // Update Statistics
      renderStatistics(data.stats);

      // Render AST Tree
      renderAst();
      requestAnimationFrame(fitAstToView);

      // Update Status Header
      if (dom.statusDot) {
        if (data.success) {
          dom.statusDot.className = 'status-dot';
          dom.statusText.textContent = `Ready · ${data.stats.node_count} AST Nodes`;
        } else if (data.has_syntax_errors) {
          dom.statusDot.className = 'status-dot error';
          dom.statusText.textContent = `Syntax Error (${data.errors.length})`;
        } else if (data.has_semantic_issues) {
          dom.statusDot.className = 'status-dot error';
          dom.statusText.textContent = `Semantic Issues (${data.errors.length})`;
        } else {
          dom.statusDot.className = 'status-dot error';
          dom.statusText.textContent = 'Lexical Error';
        }
      }

      showToast(data.success ? 'Compilation successful!' : 'Compiler reported diagnostics');
    } catch (err) {
      console.error('Compilation failed:', err);
      verdict.textContent = 'Connection failed · try compiling again';
      verdict.dataset.status = 'error';
      if (dom.statusDot) dom.statusDot.className = 'status-dot error';
      if (dom.statusText) dom.statusText.textContent = 'Server Error';
      showToast('Backend communication error');
    } finally {
      state.isCompiling = false;
      document.body.classList.remove('is-compiling');
      dom.pipelineRibbon?.setAttribute('aria-busy', 'false');
      if (dom.btnCompile) {
        dom.btnCompile.disabled = false;
        dom.btnCompile.innerHTML = '<span>▶ Run & Compile</span>';
      }
    }
  }

  // =========================================================================
  // PIPELINE RIBBON RENDERER
  // =========================================================================
  function renderPipeline(pipeline) {
    if (!dom.pipelineRibbon || !pipeline) return;

    dom.pipelineRibbon.innerHTML = pipeline.map((stage, idx) => {
      const isLast = idx === pipeline.length - 1;
      const arrow = isLast ? '' : '<span class="stage-arrow">→</span>';
      return `
        <button type="button" class="pipeline-stage status-${stage.status}" data-stage="${idx}" style="--stage-delay:${idx * 55}ms" title="${escapeHtml(stage.details)}">
          <div class="stage-num">${idx + 1}</div>
          <div class="stage-info">
            <span class="stage-name">${['Source', 'Lexer', 'Parser', 'AST', 'Semantics', 'Outputs'][idx] || escapeHtml(stage.name)}</span>
            <span class="stage-metric">${stage.ms > 0 ? `${stage.ms.toFixed(2)}ms` : stage.status.toUpperCase()}</span>
          </div>
        </button>
        ${arrow}
      `;
    }).join('');
  }

  // =========================================================================
  // AST VISUALIZER ENGINE (SVG GRAPHICAL + HIERARCHICAL CARD TREE)
  // =========================================================================
  function initAstVisualizer() {
    // Mode Switchers
    if (dom.btnModeGraphical) {
      dom.btnModeGraphical.addEventListener('click', () => {
        state.activeAstMode = 'graphical';
        dom.btnModeGraphical.classList.add('active');
        if (dom.btnModeHierarchical) dom.btnModeHierarchical.classList.remove('active');
        dom.graphicalViewport.style.display = 'block';
        dom.hierarchicalContainer.style.display = 'none';
        renderAst();
      });
    }

    if (dom.btnModeHierarchical) {
      dom.btnModeHierarchical.addEventListener('click', () => {
        state.activeAstMode = 'hierarchical';
        dom.btnModeHierarchical.classList.add('active');
        if (dom.btnModeGraphical) dom.btnModeGraphical.classList.remove('active');
        dom.graphicalViewport.style.display = 'none';
        dom.hierarchicalContainer.style.display = 'block';
        renderAst();
      });
    }

    // AST Search Input
    if (dom.astSearchInput) {
      dom.astSearchInput.addEventListener('input', (e) => {
        state.astSearchQuery = e.target.value.toLowerCase();
        renderAst();
      });
    }

    // Zoom & Pan Engine for Graphical Mode
    if (dom.graphicalViewport) {
      dom.graphicalViewport.addEventListener('mousedown', (e) => {
        if (e.button !== 0) return; // Left click only
        state.isPanning = true;
        state.panStartX = e.clientX - state.panX;
        state.panStartY = e.clientY - state.panY;
      });

      window.addEventListener('mousemove', (e) => {
        if (!state.isPanning) return;
        state.panX = e.clientX - state.panStartX;
        state.panY = e.clientY - state.panStartY;
        applySvgTransform();
      });

      window.addEventListener('mouseup', () => {
        state.isPanning = false;
      });

      dom.graphicalViewport.addEventListener('wheel', (e) => {
        e.preventDefault();
        const zoomDelta = e.deltaY < 0 ? 1.12 : 0.88;
        const newZoom = Math.min(Math.max(state.zoomScale * zoomDelta, 0.2), 3.5);
        state.zoomScale = newZoom;
        applySvgTransform();
      });
    }

    if (dom.btnZoomIn) {
      dom.btnZoomIn.addEventListener('click', () => {
        state.zoomScale = Math.min(state.zoomScale * 1.25, 3.5);
        applySvgTransform();
      });
    }

    if (dom.btnZoomOut) {
      dom.btnZoomOut.addEventListener('click', () => {
        state.zoomScale = Math.max(state.zoomScale * 0.8, 0.2);
        applySvgTransform();
      });
    }

    if (dom.btnZoomReset) {
      dom.btnZoomReset.addEventListener('click', () => {
        state.zoomScale = 1;
        state.panX = 40;
        state.panY = 40;
        applySvgTransform();
      });
    }

    if (dom.btnZoomFit) {
      dom.btnZoomFit.addEventListener('click', fitAstToView);
    }

    if (dom.btnExpandAllAst) {
      dom.btnExpandAllAst.addEventListener('click', () => {
        document.querySelectorAll('.ast-tree-item.collapsed').forEach((el) => el.classList.remove('collapsed'));
      });
    }

    if (dom.btnCollapseAllAst) {
      dom.btnCollapseAllAst.addEventListener('click', () => {
        document.querySelectorAll('.ast-tree-item').forEach((el, idx) => {
          if (idx > 0) el.classList.add('collapsed');
        });
      });
    }

    if (dom.btnHighlightSource) {
      dom.btnHighlightSource.addEventListener('click', () => {
        if (state.selectedNode && state.selectedNode.line) {
          highlightLine(state.selectedNode.line);
          showToast(`Jumped to line ${state.selectedNode.line}`);
        }
      });
    }
  }

  function fitAstToView() {
    const group = document.getElementById('ast-svg-main-group');
    if (!group || !dom.graphicalViewport) return;
    const width = dom.graphicalViewport.clientWidth;
    const height = dom.graphicalViewport.clientHeight;
    if (!width || !height) return;
    const bounds = group.getBBox();
    if (!bounds.width || !bounds.height) return;
    const padding = 28;
    state.zoomScale = Math.min((width - padding * 2) / bounds.width, (height - padding * 2) / bounds.height, 1.25);
    state.zoomScale = Math.max(state.zoomScale, 0.02);
    state.panX = (width - bounds.width * state.zoomScale) / 2 - bounds.x * state.zoomScale;
    state.panY = (height - bounds.height * state.zoomScale) / 2 - bounds.y * state.zoomScale;
    applySvgTransform();
  }

  function applySvgTransform() {
    const group = document.getElementById('ast-svg-main-group');
    if (group) {
      group.setAttribute('transform', `translate(${state.panX}, ${state.panY}) scale(${state.zoomScale})`);
    }
  }

  function renderAst() {
    if (!state.lastCompilation || !state.lastCompilation.ast_dict) {
      if (dom.svgCanvas) {
        dom.svgCanvas.innerHTML = `
          <text x="50%" y="50%" fill="#64748b" text-anchor="middle" font-family="Inter" font-size="14">
            No valid AST generated. Write code and click "Run & Compile".
          </text>`;
      }
      if (dom.hierarchicalTreeRoot) {
        dom.hierarchicalTreeRoot.innerHTML = `
          <div class="empty-state">
            <div class="empty-icon">🌳</div>
            <div class="empty-title">AST Not Available</div>
            <div class="empty-desc">Check the Errors tab for syntax or lexical diagnostics.</div>
          </div>`;
      }
      return;
    }

    const rootNode = state.lastCompilation.ast_dict;

    // Render Mode A: Graphical SVG
    renderGraphicalSvg(rootNode);

    // Render Mode B: Hierarchical Collapsible Cards
    renderHierarchicalCards(rootNode);
  }

  // --- SVG Tree Layout Engine ---
  function renderGraphicalSvg(rootNode) {
    if (!dom.svgCanvas) return;

    const nodeWidth = 160;
    const nodeHeight = 52;
    const horizSpacing = 24;
    const vertSpacing = 80;

    let idCounter = 0;
    const layoutNodes = [];
    const layoutEdges = [];

    // Helper to compute tree widths and positions
    function buildLayoutTree(node, depth = 0) {
      const nid = `svg_node_${idCounter++}`;
      const kids = (node.children || []).map((c) => buildLayoutTree(c, depth + 1));

      const layoutItem = {
        id: nid,
        node: node,
        depth: depth,
        children: kids,
        width: nodeWidth,
        height: nodeHeight,
        x: 0,
        y: depth * vertSpacing
      };

      if (kids.length === 0) {
        layoutItem.subtreeWidth = nodeWidth;
      } else {
        const totalChildrenWidth = kids.reduce((sum, k) => sum + k.subtreeWidth, 0) + (kids.length - 1) * horizSpacing;
        layoutItem.subtreeWidth = Math.max(nodeWidth, totalChildrenWidth);
      }

      return layoutItem;
    }

    const layoutRoot = buildLayoutTree(rootNode);

    // Assign X Coordinates based on centered children
    function assignXCoordinates(item, startX) {
      item.x = startX + item.subtreeWidth / 2 - item.width / 2;

      let currentChildX = startX;
      item.children.forEach((child) => {
        assignXCoordinates(child, currentChildX);
        layoutEdges.push({
          sourceId: item.id,
          sourceX: item.x + item.width / 2,
          sourceY: item.y + item.height,
          targetId: child.id,
          targetX: child.x + child.width / 2,
          targetY: child.y
        });
        currentChildX += child.subtreeWidth + horizSpacing;
      });

      layoutNodes.push(item);
    }

    assignXCoordinates(layoutRoot, 40);

    // Category Color Maps
    const darkColors = {
      structure: { stroke: '#6366f1', fill: '#141830', text: '#a5b4fc' },
      function: { stroke: '#10b981', fill: '#0e2920', text: '#6ee7b7' },
      variable: { stroke: '#0ea5e9', fill: '#0c2738', text: '#7dd3fc' },
      control: { stroke: '#f59e0b', fill: '#33230b', text: '#fcd34d' },
      expression: { stroke: '#a855f7', fill: '#281338', text: '#d8b4fe' },
      literal: { stroke: '#ec4899', fill: '#381327', text: '#f472b6' },
      other: { stroke: '#64748b', fill: '#1b2230', text: '#cbd5e1' }
    };
    const lightColors = {
      structure: {stroke: '#6366f1', fill: '#eef2ff', text: '#4338ca'},
      function: {stroke: '#059669', fill: '#ecfdf5', text: '#047857'},
      variable: {stroke: '#0284c7', fill: '#f0f9ff', text: '#0369a1'},
      control: {stroke: '#b45309', fill: '#fffbeb', text: '#92400e'},
      expression: {stroke: '#9333ea', fill: '#faf5ff', text: '#7e22ce'},
      literal: {stroke: '#db2777', fill: '#fdf2f8', text: '#be185d'},
      other: {stroke: '#64748b', fill: '#f1f5f9', text: '#334155'}
    };
    const isLight = document.documentElement.dataset.theme === 'light';
    const catColors = isLight ? lightColors : darkColors;

    // Render Curved Edges
    const edgesSvg = layoutEdges.map((edge) => {
      const midY = (edge.sourceY + edge.targetY) / 2;
      const pathD = `M ${edge.sourceX} ${edge.sourceY} C ${edge.sourceX} ${midY}, ${edge.targetX} ${midY}, ${edge.targetX} ${edge.targetY}`;
      return `<path class="ast-edge" pathLength="1" d="${pathD}" fill="none" stroke="#334155" stroke-width="2" stroke-linecap="round"/>`;
    }).join('');

    // Render Node Rectangles
    const nodesSvg = layoutNodes.map((item) => {
      const kind = item.node.kind || 'Node';
      const cat = getNodeCategory(kind);
      const col = catColors[cat] || catColors.other;
      const atoms = item.node.attributes ? item.node.attributes.join(', ') : '';
      const displayLabel = atoms ? `${kind}(${atoms})` : kind;
      const isSelected = state.selectedNode && state.selectedNode.id === item.id;
      const strokeWidth = isSelected ? 3 : 1.5;
      const strokeCol = isSelected ? '#38bdf8' : col.stroke;

      return `
        <g class="ast-svg-node" id="${item.id}" role="button" tabindex="0" aria-label="Inspect ${escapeHtml(displayLabel)}" transform="translate(${item.x}, ${item.y})" style="cursor:pointer; --node-delay:${Math.min(item.depth * 65, 450)}ms;" onclick="window.appSelectNode('${item.id}')">
          <rect width="${nodeWidth}" height="${nodeHeight}" rx="8" fill="${col.fill}" stroke="${strokeCol}" stroke-width="${strokeWidth}" filter="drop-shadow(0 2px 4px rgba(0,0,0,0.5))"/>
          <text x="12" y="22" fill="${col.text}" font-family="Inter" font-weight="700" font-size="11" letter-spacing="0.4" text-transform="uppercase">${escapeHtml(cat)}</text>
          <text x="12" y="40" fill="${isLight ? '#172b40' : '#f8fafc'}" font-family="JetBrains Mono" font-weight="600" font-size="12">${escapeHtml(truncate(displayLabel, 18))}</text>
          ${item.node.line ? `<text x="${nodeWidth - 10}" y="22" fill="${isLight ? '#526176' : '#94a3b8'}" font-family="JetBrains Mono" font-size="9.5" text-anchor="end">@${item.node.line}:${item.node.column || 1}</text>` : ''}
        </g>
      `;
    }).join('');

    // Save node lookup
    state._layoutNodesLookup = {};
    layoutNodes.forEach((n) => { state._layoutNodesLookup[n.id] = n; });

    dom.svgCanvas.innerHTML = `
      <g id="ast-svg-main-group" transform="translate(${state.panX}, ${state.panY}) scale(${state.zoomScale})">
        ${edgesSvg}
        ${nodesSvg}
      </g>
    `;

    // Select root node by default if none selected
    if (!state.selectedNode && layoutNodes.length > 0) {
      selectNode(layoutRoot.id);
    }
  }

  // --- Hierarchical Collapsible Cards Engine ---
  function renderHierarchicalCards(rootNode) {
    if (!dom.hierarchicalTreeRoot) return;

    let nodeIndex = 0;
    state._cardNodesLookup = {};

    function buildNodeHtml(node, depth = 0) {
      const nid = `card_node_${nodeIndex++}`;
      state._cardNodesLookup[nid] = node;
      const kind = node.kind || 'Node';
      const cat = getNodeCategory(kind);
      const atoms = node.attributes ? node.attributes.join(', ') : '';
      const displayLabel = atoms ? `${kind}(${atoms})` : kind;
      const kids = node.children || [];
      const hasKids = kids.length > 0;

      const renderedKids = kids.map((c) => buildNodeHtml(c, depth + 1)).join('');
      const kidsHtml = hasKids ? `<ul class="ast-tree-children">${renderedKids}</ul>` : '';
      const toggleBtn = hasKids ? `<button class="ast-toggle-btn" onclick="window.appToggleNode('${nid}', event)">▼</button>` : `<span style="width:20px;display:inline-block;"></span>`;
      const countBadge = hasKids ? `<span class="badge-tag badge-m13" style="font-size:9.5px;">${kids.length} ${kids.length === 1 ? 'child' : 'children'}</span>` : '';
      const locBadge = node.line ? `<span class="badge-loc">@${node.line}:${node.column || 1}</span>` : '';

      return `
        <li class="ast-tree-item" id="${nid}">
          <div class="ast-node-row" tabindex="0" aria-label="Inspect ${escapeHtml(displayLabel)}" onclick="window.appSelectNode('${nid}')">
            ${toggleBtn}
            <div class="ast-node-card">
              <span class="badge-cat badge-${cat}">${escapeHtml(cat)}</span>
              <span class="ast-node-label">${escapeHtml(displayLabel)}</span>
              ${locBadge}
              ${countBadge}
            </div>
          </div>
          ${kidsHtml}
        </li>
      `;
    }

    dom.hierarchicalTreeRoot.innerHTML = buildNodeHtml(rootNode);
  }

  // Window bridge for node interactions
  window.appSelectNode = function (nodeId) {
    selectNode(nodeId);
  };

  window.appToggleNode = function (nodeId, event) {
    if (event) event.stopPropagation();
    const item = document.getElementById(nodeId);
    if (item) item.classList.toggle('collapsed');
  };

  function selectNode(nodeId) {
    // Lookup in state
    let nodeData = null;
    if (state._layoutNodesLookup && state._layoutNodesLookup[nodeId]) {
      nodeData = state._layoutNodesLookup[nodeId].node;
    } else if (state._cardNodesLookup && state._cardNodesLookup[nodeId]) {
      nodeData = state._cardNodesLookup[nodeId];
    } else if (state.lastCompilation && state.lastCompilation.ast_dict) {
      nodeData = state.lastCompilation.ast_dict; // Fallback
    }

    if (!nodeData) return;
    state.selectedNode = { id: nodeId, ...nodeData };

    // Update Highlights
    document.querySelectorAll('.ast-tree-item.selected, .ast-svg-node.selected').forEach((el) => el.classList.remove('selected'));
    const cardEl = document.getElementById(nodeId);
    if (cardEl) cardEl.classList.add('selected');

    // Update Inspector Drawer
    if (dom.inspNodeKind) dom.inspNodeKind.textContent = nodeData.kind || 'Node';
    if (dom.inspNodeCat) dom.inspNodeCat.textContent = getNodeCategory(nodeData.kind);
    if (dom.inspNodeAtoms) dom.inspNodeAtoms.textContent = nodeData.attributes ? nodeData.attributes.join(', ') : 'None';
    if (dom.inspNodeLoc) dom.inspNodeLoc.textContent = nodeData.line ? `Line ${nodeData.line}, Col ${nodeData.column || 1}` : 'N/A';
    if (dom.inspNodeSubnodes) {
      const count = countSubnodes(nodeData);
      dom.inspNodeSubnodes.textContent = count;
    }
    if (dom.inspNodeDepth) {
      const depth = computeNodeDepth(nodeData);
      dom.inspNodeDepth.textContent = depth;
    }
    if (dom.inspJsonSnippet) {
      dom.inspJsonSnippet.textContent = JSON.stringify(nodeData, null, 2);
    }

    // Children quick links
    if (dom.inspChildrenList) {
      const kids = nodeData.children || [];
      if (kids.length === 0) {
        dom.inspChildrenList.innerHTML = '<span style="color:var(--text-faint); font-size:12px;">Leaf node (0 children)</span>';
      } else {
        dom.inspChildrenList.innerHTML = kids.map((k) => `
          <div style="padding:4px 8px; background:var(--bg-surface); border-radius:4px; margin-bottom:4px; font-family:var(--font-mono); font-size:11.5px; border:1px solid var(--border-subtle);">
            ${escapeHtml(k.kind)} ${k.line ? `<span style="color:var(--text-faint);">@${k.line}</span>` : ''}
          </div>
        `).join('');
      }
    }
  }

  function countSubnodes(n) {
    if (!n) return 0;
    let sum = 1;
    (n.children || []).forEach((c) => { sum += countSubnodes(c); });
    return sum;
  }

  function computeNodeDepth(n) {
    if (!n || !n.children || n.children.length === 0) return 1;
    let maxChildDepth = 0;
    n.children.forEach((c) => {
      maxChildDepth = Math.max(maxChildDepth, computeNodeDepth(c));
    });
    return 1 + maxChildDepth;
  }

  // =========================================================================
  // TOKEN EXPLORER ENGINE
  // =========================================================================
  function initTokens() {
    if (dom.tokenSearchInput) {
      dom.tokenSearchInput.addEventListener('input', (e) => {
        state.tokenSearchQuery = e.target.value.toLowerCase();
        filterAndRenderTokens();
      });
    }

    dom.tokenFilterChips.forEach((chip) => {
      chip.addEventListener('click', () => {
        dom.tokenFilterChips.forEach((c) => c.classList.remove('active'));
        chip.classList.add('active');
        state.tokenFilter = chip.dataset.filter || 'ALL';
        filterAndRenderTokens();
      });
    });
  }

  function renderTokens(tokens) {
    state._tokensList = tokens || [];
    if (dom.tokenBadgeCounter) {
      dom.tokenBadgeCounter.textContent = state._tokensList.length;
    }
    filterAndRenderTokens();
  }

  function filterAndRenderTokens() {
    if (!dom.tokenTableBody) return;
    const tokens = state._tokensList || [];
    const query = state.tokenSearchQuery;
    const filter = state.tokenFilter;

    const filtered = tokens.filter((t) => {
      const matchCat = filter === 'ALL' || t.category.toUpperCase() === filter.toUpperCase();
      const matchQuery = !query || t.type.toLowerCase().includes(query) || (t.value && t.value.toLowerCase().includes(query));
      return matchCat && matchQuery;
    });

    if (filtered.length === 0) {
      dom.tokenTableBody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align:center; padding:24px; color:var(--text-muted);">
            No tokens match your search criteria.
          </td>
        </tr>`;
      return;
    }

    dom.tokenTableBody.innerHTML = filtered.map((t) => `
      <tr>
        <td style="color:var(--text-faint); font-family:var(--font-mono);">${t.index}</td>
        <td class="code-cell" style="color:var(--accent-cyan);">${escapeHtml(t.type)}</td>
        <td><span class="badge-cat badge-${t.category.toLowerCase()}">${escapeHtml(t.category)}</span></td>
        <td class="code-cell">${t.value ? escapeHtml(t.value) : '<span style="color:var(--text-faint);">None</span>'}</td>
        <td style="font-family:var(--font-mono);">${t.line}:${t.column}</td>
      </tr>
    `).join('');
  }

  // =========================================================================
  // ERROR & DIAGNOSTICS ENGINE
  // =========================================================================
  function renderErrors(errors, hasSyntaxErrors, hasSemanticIssues) {
    if (!dom.errorsList) return;
    const errCount = errors ? errors.length : 0;

    if (dom.errBadgeCounter) {
      dom.errBadgeCounter.textContent = errCount;
      dom.errBadgeCounter.className = errCount > 0 ? 'badge-counter alert' : 'badge-counter';
    }

    if (!errors || errors.length === 0) {
      dom.errorsList.style.display = 'none';
      if (dom.errorsEmptyState) dom.errorsEmptyState.style.display = 'flex';
      return;
    }

    dom.errorsList.style.display = 'flex';
    if (dom.errorsEmptyState) dom.errorsEmptyState.style.display = 'none';

    // Panic recovery banner
    let recoveryBanner = '';
    if (hasSyntaxErrors) {
      recoveryBanner = `
        <div style="background:rgba(245, 158, 11, 0.1); border:1px solid var(--accent-amber); border-radius:var(--radius-md); padding:12px 16px; font-size:12.5px; color:var(--accent-amber);">
          <strong>Panic-Mode Error Recovery Active:</strong> The parser identified syntax errors and synchronized forward at statement boundaries (semicolons/keywords) to collect multiple diagnostics without crashing.
        </div>`;
    }

    const cardsHtml = errors.map((err) => {
      const isError = err.severity === 'error';
      return `
        <div class="diagnostic-card ${isError ? 'error' : 'warning'}">
          <div class="diag-header">
            <div class="diag-badges">
              <span class="diag-phase ${err.phase.toLowerCase()}">${escapeHtml(err.phase)}</span>
              <span style="font-size:11.5px; font-family:var(--font-mono); color:var(--text-muted);">
                Line ${err.line || '?'}, Col ${err.column || '?'}
              </span>
            </div>
            ${err.line ? `<button class="btn btn-icon-only" title="Jump to Line" onclick="window.appJumpToLine(${err.line})">📍 Jump</button>` : ''}
          </div>
          <div class="diag-msg">${escapeHtml(err.message)}</div>
          ${err.snippet ? `<div class="diag-snippet">${formatErrorSnippet(err.snippet)}</div>` : ''}
        </div>
      `;
    }).join('');

    dom.errorsList.innerHTML = recoveryBanner + cardsHtml;
  }

  function formatErrorSnippet(snippet) {
    const lines = snippet.split('\n');
    if (lines.length >= 2) {
      const codeLine = escapeHtml(lines[0]);
      const caretLine = `<span class="caret">${escapeHtml(lines[1])}</span>`;
      return `${codeLine}\n${caretLine}`;
    }
    return escapeHtml(snippet);
  }

  window.appJumpToLine = function (line) {
    highlightLine(line);
    showToast(`Jumped to line ${line}`);
  };

  // =========================================================================
  // OUTPUT FORMATS ENGINE
  // =========================================================================
  function initOutputs() {
    dom.formatPillBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        dom.formatPillBtns.forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        state.activeOutputFormat = btn.dataset.format;
        updateOutputDisplay();
      });
    });

    if (dom.btnCopyOutput) {
      dom.btnCopyOutput.addEventListener('click', () => {
        const text = getActiveOutputContent();
        if (text) {
          navigator.clipboard.writeText(text).then(() => {
            showToast('Output copied to clipboard!');
          }).catch(() => {
            showToast('Failed to copy automatically');
          });
        }
      });
    }

    if (dom.btnDownloadOutput) {
      dom.btnDownloadOutput.addEventListener('click', () => {
        const text = getActiveOutputContent();
        if (!text) return;
        const fmt = state.activeOutputFormat;
        const ext = { tree: 'txt', sexpr: 'sexpr', json: 'json', dot: 'dot', html: 'html' }[fmt] || 'txt';
        const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ast_output.${ext}`;
        a.click();
        URL.revokeObjectURL(url);
        showToast(`Downloaded ast_output.${ext}`);
      });
    }
  }

  function renderOutputs(outputs) {
    state._outputs = outputs || {};
    updateOutputDisplay();
  }

  function getActiveOutputContent() {
    if (!state._outputs) return '';
    return state._outputs[state.activeOutputFormat] || '';
  }

  function updateOutputDisplay() {
    const fmt = state.activeOutputFormat;
    const content = getActiveOutputContent();

    if (fmt === 'html') {
      if (dom.outputViewerBox) dom.outputViewerBox.style.display = 'none';
      if (dom.outputFrameWrap) dom.outputFrameWrap.style.display = 'block';
      if (dom.htmlPreviewFrame) {
        dom.htmlPreviewFrame.srcdoc = content.replace('data-theme="dark"', `data-theme="${document.documentElement.dataset.theme}"`);
      }
    } else {
      if (dom.outputViewerBox) dom.outputViewerBox.style.display = 'block';
      if (dom.outputFrameWrap) dom.outputFrameWrap.style.display = 'none';
      if (dom.outputViewerBox) {
        dom.outputViewerBox.textContent = content || 'No output generated for this format.';
      }
    }
  }

  // =========================================================================
  // STATISTICS & PROFILER ENGINE
  // =========================================================================
  function renderStatistics(stats) {
    if (!stats) return;

    if (dom.statNodeCount) dom.statNodeCount.textContent = stats.node_count;
    if (dom.statAstDepth) dom.statAstDepth.textContent = stats.ast_depth;
    if (dom.statTokenCount) dom.statTokenCount.textContent = stats.token_count;
    if (dom.statLinesCount) dom.statLinesCount.textContent = `${stats.source_lines} / ${stats.source_chars}`;
    if (dom.statTotalTime) dom.statTotalTime.textContent = `${stats.total_ms}ms`;
    if (dom.statIssuesCount) {
      const errCount = (state.lastCompilation && state.lastCompilation.errors) ? state.lastCompilation.errors.length : 0;
      dom.statIssuesCount.textContent = errCount;
    }

    if (dom.timeLexMs) dom.timeLexMs.textContent = `${stats.lex_ms.toFixed(2)}ms`;
    if (dom.timeParseMs) dom.timeParseMs.textContent = `${stats.parse_ms.toFixed(2)}ms`;
    if (dom.timeSemMs) dom.timeSemMs.textContent = `${stats.sem_ms.toFixed(2)}ms`;

    // Proportional Timing Bar
    const totalPhaseTime = Math.max(stats.lex_ms + stats.parse_ms + stats.sem_ms, 0.001);
    const lexPct = (stats.lex_ms / totalPhaseTime) * 100;
    const parsePct = (stats.parse_ms / totalPhaseTime) * 100;
    const semPct = (stats.sem_ms / totalPhaseTime) * 100;

    if (dom.barSliceLex) dom.barSliceLex.style.width = `${lexPct}%`;
    if (dom.barSliceParse) dom.barSliceParse.style.width = `${parsePct}%`;
    if (dom.barSliceSem) dom.barSliceSem.style.width = `${semPct}%`;

    // Token Histogram Table
    if (dom.tokenHistogramBody) {
      const hist = stats.token_histogram || {};
      const entries = Object.entries(hist).sort((a, b) => b[1] - a[1]);
      const maxCount = entries.length > 0 ? entries[0][1] : 1;

      dom.tokenHistogramBody.innerHTML = entries.map(([type, count]) => {
        const pct = Math.round((count / maxCount) * 100);
        return `
          <tr>
            <td class="code-cell" style="color:var(--accent-cyan); font-size:12px;">${escapeHtml(type)}</td>
            <td style="font-family:var(--font-mono); font-weight:700;">${count}</td>
            <td style="width:50%;">
              <div style="background:var(--bg-card); height:8px; border-radius:4px; overflow:hidden;">
                <div style="background:var(--accent-cyan); height:100%; width:${pct}%;"></div>
              </div>
            </td>
          </tr>
        `;
      }).join('');
    }
  }

  // =========================================================================
  // RESULTS TABS CONTROLLER
  // =========================================================================
  function initResultTabs() {
    dom.resultTabs.forEach((tab) => {
      tab.addEventListener('click', () => {
        const targetPanelId = tab.dataset.tab;
        dom.resultTabs.forEach((t) => t.classList.remove('active'));
        dom.resultPanels.forEach((p) => p.classList.remove('active'));

        tab.classList.add('active');
        const panel = document.getElementById(targetPanelId);
        if (panel) panel.classList.add('active');

        state.activeResultTab = targetPanelId;
        if (targetPanelId === 'panel-ast-visualizer') {
          renderAst();
        }
      });
    });
  }

  // =========================================================================
  // AUTOMATED TEST SUITE RUNNER
  // =========================================================================
  function initTestSuite() {
    if (dom.btnRunTestSuite) {
      dom.btnRunTestSuite.addEventListener('click', async () => {
        dom.btnRunTestSuite.disabled = true;
        dom.btnRunTestSuite.innerHTML = '<span class="status-dot compiling" style="width:10px;height:10px;"></span> <span>Executing 39 Test Cases...</span>';
        if (dom.testProgressBar) dom.testProgressBar.style.width = '20%';

        try {
          const res = await fetch('/api/tests/run', { method: 'POST' });
          const data = await res.json();
          state._testResults = data;

          if (dom.testProgressBar) {
            dom.testProgressBar.style.width = '100%';
            dom.testProgressBar.style.background = data.failed_count === 0 ? 'var(--accent-emerald)' : 'var(--accent-rose)';
          }

          if (dom.testSummaryText) {
            dom.testSummaryText.innerHTML = `
              <strong>Result:</strong> ${data.passed_count}/${data.total_tests} Passed 
              (${data.failed_count} Failed) in <strong>${data.elapsed_ms}ms</strong>
            `;
          }

          renderTestTable(data.tests);
          showToast(`Test suite finished: ${data.passed_count}/${data.total_tests} passed!`);
        } catch (err) {
          console.error('Test run failed:', err);
          showToast('Failed to execute test suite');
        } finally {
          dom.btnRunTestSuite.disabled = false;
          dom.btnRunTestSuite.innerHTML = '<span>▶ Run All 39 Unit Tests & Corpus</span>';
        }
      });
    }

    dom.testFilterChips.forEach((chip) => {
      chip.addEventListener('click', () => {
        dom.testFilterChips.forEach((c) => c.classList.remove('active'));
        chip.classList.add('active');
        state.testStatusFilter = chip.dataset.filter || 'ALL';
        if (state._testResults) {
          renderTestTable(state._testResults.tests);
        }
      });
    });

    if (dom.btnViewRawTerminal) {
      dom.btnViewRawTerminal.addEventListener('click', () => {
        if (!state._testResults) {
          showToast('Please run the tests first!');
          return;
        }
        alert(state._testResults.raw_output);
      });
    }
  }

  function renderTestTable(tests) {
    if (!dom.testTableBody || !tests) return;
    const filter = state.testStatusFilter || 'ALL';

    const filtered = tests.filter((t) => {
      if (filter === 'ALL') return true;
      return t.status === filter;
    });

    dom.testTableBody.innerHTML = filtered.map((t) => {
      const isPass = t.status === 'PASS';
      return `
        <tr>
          <td class="code-cell" style="color:var(--text-main);">${escapeHtml(t.name)}</td>
          <td><span class="badge-tag" style="background:var(--bg-card); color:var(--text-muted); border:1px solid var(--border-subtle);">${escapeHtml(t.category)}</span></td>
          <td><span class="badge-tag" style="background:${isPass ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)'}; color:${isPass ? 'var(--accent-emerald)' : 'var(--accent-rose)'}; border:1px solid ${isPass ? 'var(--accent-emerald)' : 'var(--accent-rose)'};">${t.status}</span></td>
          <td style="font-family:var(--font-mono); font-size:11.5px; color:var(--text-muted);">${escapeHtml(t.details)}</td>
        </tr>
      `;
    }).join('');
  }

  // =========================================================================
  // AST DIFF VIEWER ENGINE
  // =========================================================================
  function initDiffModal() {
    if (dom.btnOpenDiffModal && dom.diffModal) {
      dom.btnOpenDiffModal.addEventListener('click', () => {
        dom.diffModal.classList.add('active');
        // Pre-fill editor A with current code
        if (dom.diffEditorA && !dom.diffEditorA.value) {
          dom.diffEditorA.value = dom.editor.value;
        }
      });
    }

    document.querySelectorAll('.modal-close-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.modal-overlay').forEach((m) => m.classList.remove('active'));
      });
    });

    if (dom.btnRunDiff) {
      dom.btnRunDiff.addEventListener('click', async () => {
        const srcA = dom.diffEditorA.value;
        const srcB = dom.diffEditorB.value;

        try {
          const res = await fetch('/api/diff', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sourceA: srcA, sourceB: srcB })
          });
          const data = await res.json();

          if (dom.diffResultsContainer) {
            dom.diffResultsContainer.innerHTML = `
              <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:16px;">
                <div style="background:var(--bg-card); padding:12px; border-radius:8px; border:1px solid var(--border-subtle);">
                  <h4 style="font-size:13px; margin-bottom:6px;">Version A</h4>
                  <div style="font-size:12px; color:var(--text-muted); font-family:var(--font-mono);">
                    Nodes: ${data.versionA.nodes} | Depth: ${data.versionA.depth} | Tokens: ${data.versionA.tokens}
                  </div>
                </div>
                <div style="background:var(--bg-card); padding:12px; border-radius:8px; border:1px solid var(--border-subtle);">
                  <h4 style="font-size:13px; margin-bottom:6px;">Version B</h4>
                  <div style="font-size:12px; color:var(--text-muted); font-family:var(--font-mono);">
                    Nodes: ${data.versionB.nodes} | Depth: ${data.versionB.depth} | Tokens: ${data.versionB.tokens}
                  </div>
                </div>
              </div>
              <div style="display:flex; gap:16px; font-size:12.5px; font-weight:700; color:var(--accent-cyan); margin-bottom:12px;">
                <span>Δ Nodes: ${data.diff.node_delta > 0 ? '+' : ''}${data.diff.node_delta}</span>
                <span>Δ Depth: ${data.diff.depth_delta > 0 ? '+' : ''}${data.diff.depth_delta}</span>
                <span>Δ Tokens: ${data.diff.token_delta > 0 ? '+' : ''}${data.diff.token_delta}</span>
              </div>
              <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
                <pre style="background:var(--bg-surface); padding:12px; border-radius:8px; font-family:var(--font-mono); font-size:11.5px; overflow:auto; max-height:280px; border:1px solid var(--border-main);">${escapeHtml(data.versionA.tree)}</pre>
                <pre style="background:var(--bg-surface); padding:12px; border-radius:8px; font-family:var(--font-mono); font-size:11.5px; overflow:auto; max-height:280px; border:1px solid var(--border-main);">${escapeHtml(data.versionB.tree)}</pre>
              </div>
            `;
          }
        } catch (err) {
          console.error('Diff failed:', err);
          showToast('Failed to compare ASTs');
        }
      });
    }
  }

  // =========================================================================
  // UTILITY HELPERS
  // =========================================================================
  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function animateMetric(element, target) {
    cancelAnimationFrame(element._animationFrame);
    const start = Number(element.dataset.value || 0);
    element.dataset.value = String(target);
    if (document.documentElement.dataset.motion === 'off') { element.textContent = target; return; }
    const started = performance.now();
    const tick = (now) => {
      const progress = Math.min((now - started) / 380, 1);
      element.textContent = Math.round(start + (target - start) * (1 - Math.pow(1 - progress, 3)));
      if (progress < 1) element._animationFrame = requestAnimationFrame(tick);
    };
    element._animationFrame = requestAnimationFrame(tick);
  }

  function truncate(str, maxLen = 20) {
    if (!str) return '';
    return str.length > maxLen ? str.substring(0, maxLen - 1) + '…' : str;
  }

  // =========================================================================
  // BOOTSTRAP INITIALIZATION
  // =========================================================================
  function initPresentationTools() {
    const focusButton = document.getElementById('btn-focus');
    focusButton.addEventListener('click', () => {
      const expanded = document.body.classList.toggle('workspace-expanded');
      focusButton.setAttribute('aria-pressed', String(expanded));
      focusButton.textContent = expanded ? 'Restore workspace' : 'Expand workspace';
      requestAnimationFrame(fitAstToView);
    });
    const openResult = (id) => {
      const tab = Array.from(dom.resultTabs).find((item) => item.dataset.tab === id);
      tab?.click();
      document.getElementById(id)?.scrollIntoView({ block: 'nearest' });
    };
    document.getElementById('btn-review-diagnostics').addEventListener('click', () => openResult('panel-errors'));
    dom.pipelineRibbon.addEventListener('click', (event) => {
      const stage = event.target.closest('[data-stage]');
      if (!stage) return;
      const index = Number(stage.dataset.stage);
      if (index === 0) { dom.editor.focus(); return; }
      const panels = ['','panel-tokens','panel-ast-visualizer','panel-ast-visualizer','panel-errors','panel-outputs'];
      openResult(panels[index]);
      if (index === 2 || index === 3) requestAnimationFrame(fitAstToView);
    });
    document.getElementById('btn-export-svg').addEventListener('click', () => {
      const original = document.getElementById('ast-svg-main-group');
      if (!original || !state.lastCompilation?.ast_dict) {
        showToast('Compile a program with a valid AST first.');
        return;
      }
      const bounds = original.getBBox();
      if (!bounds.width || !bounds.height) { showToast('Switch to Graphical Tree before exporting.'); return; }
      const clone = original.cloneNode(true);
      clone.removeAttribute('transform');
      clone.querySelectorAll('.ast-svg-node').forEach((node) => {
        node.removeAttribute('onclick');
        node.removeAttribute('tabindex');
        node.removeAttribute('role');
        node.removeAttribute('style');
      });
      const ns = 'http://www.w3.org/2000/svg';
      const svg = document.createElementNS(ns, 'svg');
      svg.setAttribute('xmlns', ns);
      svg.setAttribute('viewBox', `${bounds.x - 24} ${bounds.y - 24} ${bounds.width + 48} ${bounds.height + 48}`);
      svg.setAttribute('width', bounds.width + 48);
      svg.setAttribute('height', bounds.height + 48);
      const background = document.createElementNS(ns, 'rect');
      background.setAttribute('x', bounds.x - 24);
      background.setAttribute('y', bounds.y - 24);
      background.setAttribute('width', bounds.width + 48);
      background.setAttribute('height', bounds.height + 48);
      background.setAttribute('fill', document.documentElement.dataset.theme === 'light' ? '#f5f9fc' : '#0b1220');
      svg.append(background, clone);
      const blob = new Blob([new XMLSerializer().serializeToString(svg)], {type: 'image/svg+xml'});
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'compiler-ast.svg';
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      showToast('AST image exported for your report.');
    });
  }

  window.addEventListener('DOMContentLoaded', () => {
    document.addEventListener('studio:theme', () => {
      renderAst();
      if (state.activeOutputFormat === 'html') updateOutputDisplay();
    });
    dom.hierarchicalTreeRoot.addEventListener('keydown', (event) => {
      if (event.target.classList.contains('ast-node-row') && (event.key === 'Enter' || event.key === ' ')) {
        event.preventDefault();
        selectNode(event.target.closest('.ast-tree-item').id);
      }
    });
    initPresentationTools();
    const motionButton = document.getElementById('btn-motion');
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    let motionPreference = null;
    try { motionPreference = localStorage.getItem('studio-motion'); } catch (_) { /* Storage may be unavailable. */ }
    function updateMotion() {
      const enabled = !reducedMotion.matches && motionPreference !== 'off';
      document.documentElement.dataset.motion = enabled ? 'on' : 'off';
      motionButton.textContent = enabled ? 'Motion on' : 'Motion off';
      motionButton.setAttribute('aria-pressed', String(enabled));
      motionButton.disabled = reducedMotion.matches;
      motionButton.title = reducedMotion.matches ? 'Reduced motion follows your system preference' : 'Toggle interface animations';
    }
    motionButton.addEventListener('click', () => {
      motionPreference = document.documentElement.dataset.motion === 'on' ? 'off' : 'on';
      try { localStorage.setItem('studio-motion', motionPreference); } catch (_) { /* Keep the session preference. */ }
      updateMotion();
    });
    reducedMotion.addEventListener('change', updateMotion);
    updateMotion();
    dom.svgCanvas.addEventListener('keydown', (event) => {
      const node = event.target.closest('.ast-svg-node');
      if (node && (event.key === 'Enter' || event.key === ' ')) {
        event.preventDefault();
        selectNode(node.id);
      }
    });
    initNavigation();
    initEditor();
    initAstVisualizer();
    initTokens();
    initOutputs();
    initResultTabs();
    initTestSuite();
    initDiffModal();
    loadSamplesList();
  });

})();

/**
 * Main application coordinator for the Graphing Calculator.
 */

import {
  PALETTE,
  DEFAULT_VIEW,
  EXAMPLES,
  DEBOUNCE_DELAY,
} from './config.js';

import {
  compileEquation,
  splitTopLevel,
} from './math-engine.js';

import { GraphRenderer } from './renderer.js';
import { GraphController } from './graph-controller.js';
import {
  renderFunctionsList,
  bindFunctionsListEvents,
  updateEquationInputState,
  setClearConfirmVisible,
  showErrorBanner,
  updateCoordinates,
  resetCoordinates,
  updateViewRange,
  setGridButtonActive,
  toggleFullscreenOverlay,
  bindControls,
} from './ui.js';

(function initCalculatorApp() {
  // DOM Elements
  const canvas = document.getElementById('graph-canvas');
  const fsCanvas = document.getElementById('fs-canvas');
  const functionsListEl = document.getElementById('functions-list');
  const errorBannerEl = document.getElementById('error-banner');
  const errorTextEl = document.getElementById('error-text');
  const coordsEl = document.getElementById('coords-display');
  const viewRangeEl = document.getElementById('view-range');
  const gridToggleBtn = document.getElementById('grid-toggle-btn');
  const fsOverlay = document.getElementById('fs-overlay');

  // Application State
  let equations = []; // { id, raw, color, enabled, fns, errors }
  let nextId = 0;
  let nextColorIdx = 0;
  const pendingTimers = new Map();
  let isFullscreenOpen = false;

  function clearEquationTimer(id) {
    if (pendingTimers.has(id)) {
      clearTimeout(pendingTimers.get(id));
      pendingTimers.delete(id);
    }
  }

  function clearAllTimers() {
    for (const timer of pendingTimers.values()) {
      clearTimeout(timer);
    }
    pendingTimers.clear();
  }

  const settings = {
    showGrid: true,
    gridSizeMul: 1,
    lineWidth: 2,
  };

  // Subsystems
  const renderer = new GraphRenderer(canvas, fsCanvas);

  function onViewChange() {
    render();
  }

  function onCoordinates(x, y) {
    updateCoordinates(coordsEl, x, y);
  }

  function onCoordinatesLeave() {
    resetCoordinates(coordsEl);
  }

  const controller = new GraphController(canvas, fsCanvas, DEFAULT_VIEW, {
    onViewChange,
    onCoordinates,
    onCoordinatesLeave,
  });

  // --- Rendering & Error Handling ---

  function render() {
    renderer.drawMain(controller.getView(), equations, settings);
    updateViewRange(viewRangeEl, controller.getView());

    if (isFullscreenOpen) {
      renderer.drawFullscreen(controller.getView(), equations, settings);
    }
  }

  function refreshErrors() {
    const errs = equations.flatMap((e) => e.errors || []);
    showErrorBanner(errorBannerEl, errorTextEl, errs);
  }

  // --- Equation Management ---

  function addEquation(raw, color) {
    const trimmed = typeof raw === 'string' ? raw.trim() : raw;
    if (!trimmed || (Array.isArray(trimmed) && trimmed.length === 0)) return;

    const id = nextId++;
    const c = color || PALETTE[nextColorIdx % PALETTE.length];
    nextColorIdx++;

    const eq = { id, raw: trimmed, color: c, enabled: true, fns: [], errors: [] };
    compileEquation(eq);
    equations.push(eq);

    renderFunctionsList(functionsListEl, equations);
    render();
    refreshErrors();
  }

  function removeEquation(id) {
    clearEquationTimer(id);
    equations = equations.filter((e) => e.id !== id);
    renderFunctionsList(functionsListEl, equations);
    render();
    refreshErrors();
  }

  function toggleEquation(id) {
    const eq = equations.find((e) => e.id === id);
    if (eq) eq.enabled = !eq.enabled;
    renderFunctionsList(functionsListEl, equations);
    render();
  }

  function cycleColor(id) {
    const eq = equations.find((e) => e.id === id);
    if (!eq) return;
    const i = PALETTE.indexOf(eq.color);
    eq.color = PALETTE[(i + 1) % PALETTE.length];
    const dot = functionsListEl ? functionsListEl.querySelector(`[data-action="cycle-color"][data-id="${eq.id}"]`) : null;
    if (dot) {
      dot.style.background = eq.color;
    } else {
      renderFunctionsList(functionsListEl, equations);
    }
    render();
  }

  function onRawInput(id, val) {
    const eq = equations.find((e) => e.id === id);
    if (!eq) return;

    const wasArray = Array.isArray(eq.raw);
    eq.raw = wasArray ? splitTopLevel(val).map((s) => s.trim()).filter(Boolean) : val;

    clearEquationTimer(id);
    const timer = setTimeout(() => {
      pendingTimers.delete(id);
      compileEquation(eq);
      updateEquationInputState(eq.id, eq.errors.length > 0);
      render();
      refreshErrors();
    }, DEBOUNCE_DELAY);
    pendingTimers.set(id, timer);
  }

  function onCommit(id) {
    clearEquationTimer(id);
    const eq = equations.find((e) => e.id === id);
    if (!eq) return;
    compileEquation(eq);
    renderFunctionsList(functionsListEl, equations);
    render();
    refreshErrors();
  }

  function clearAllEquations() {
    clearAllTimers();
    equations = [];
    nextColorIdx = 0;
    renderFunctionsList(functionsListEl, equations);
    render();
    if (errorBannerEl) errorBannerEl.classList.add('hidden');
    setClearConfirmVisible(false);
  }

  function loadExample(exampleKey) {
    const example = EXAMPLES[exampleKey];
    if (!example) return;
    addEquation(example.exprs);
  }

  // --- Fullscreen Handling ---

  const leftPanel = document.getElementById('left-panel');
  const fsSidebarContainer = document.getElementById('fs-sidebar-container');
  const fsToggleSidebarBtn = document.getElementById('fs-toggle-sidebar-btn');
  let leftPanelParent = null;
  let leftPanelNextSibling = null;
  let isFsSidebarOpen = true;

  if (leftPanel) {
    leftPanelParent = leftPanel.parentElement;
    leftPanelNextSibling = leftPanel.nextElementSibling;
  }

  function applyFsSidebarVisibility() {
    if (leftPanel && isFullscreenOpen) {
      leftPanel.classList.toggle('hidden', !isFsSidebarOpen);
    }
    if (fsToggleSidebarBtn) {
      fsToggleSidebarBtn.setAttribute('aria-pressed', String(isFsSidebarOpen));
      fsToggleSidebarBtn.classList.toggle('bg-teal-50', isFsSidebarOpen);
      fsToggleSidebarBtn.classList.toggle('text-teal-600', isFsSidebarOpen);
    }
  }

  if (fsToggleSidebarBtn) {
    fsToggleSidebarBtn.addEventListener('click', () => {
      isFsSidebarOpen = !isFsSidebarOpen;
      applyFsSidebarVisibility();
    });
  }

  function getFsToolbarHeight() {
    const toolbar = fsOverlay ? fsOverlay.querySelector('div') : null;
    return (toolbar && toolbar.offsetHeight) ? toolbar.offsetHeight : 44;
  }

  function setupFullscreen(silentAspect = true) {
    const w = window.innerWidth;
    const toolbarH = getFsToolbarHeight();
    const h = Math.max(window.innerHeight - toolbarH, 0);
    renderer.resizeFullscreen(w, h);
    controller.fitAspect(w, h, silentAspect);
  }

  function toggleFullscreen() {
    isFullscreenOpen = !isFullscreenOpen;
    toggleFullscreenOverlay(fsOverlay, isFullscreenOpen);
    if (isFullscreenOpen) {
      if (leftPanel && fsSidebarContainer) {
        fsSidebarContainer.appendChild(leftPanel);
        leftPanel.classList.add(
          'absolute', 'top-0', 'right-0', 'bottom-0', 'w-80',
          'shadow-2xl', 'pointer-events-auto', 'z-40'
        );
        leftPanel.style.height = '100%';
        leftPanel.style.position = 'absolute';
        leftPanel.style.top = '0';
        leftPanel.style.right = '0';
        leftPanel.style.bottom = '0';
        leftPanel.style.left = '';
        leftPanel.style.zIndex = '40';
      }
      applyFsSidebarVisibility();
      setupFullscreen(true);
      render();
      refreshErrors();
    } else {
      if (leftPanel && leftPanelParent) {
        leftPanel.classList.remove(
          'absolute', 'top-0', 'right-0', 'bottom-0', 'w-80',
          'shadow-2xl', 'pointer-events-auto', 'z-40'
        );
        leftPanel.style.height = '';
        leftPanel.style.position = '';
        leftPanel.style.top = '';
        leftPanel.style.right = '';
        leftPanel.style.bottom = '';
        leftPanel.style.left = '';
        leftPanel.style.zIndex = '';
        if (leftPanelNextSibling) {
          leftPanelParent.insertBefore(leftPanel, leftPanelNextSibling);
        } else {
          leftPanelParent.appendChild(leftPanel);
        }
        // Restore normal-page visibility
        leftPanel.classList.remove('hidden');
      }
      // After reinserting the sidebar, resize and refit the main graph canvas
      const { width, height } = renderer.resizeMain();
      controller.fitAspect(width, height, true);
      render();
      refreshErrors();
    }
  }

  // --- Layout & Resize ---

  function handleResize() {
    if (isFullscreenOpen) {
      setupFullscreen(true);
      renderer.resizeMain();
    } else {
      const { width, height } = renderer.resizeMain();
      controller.fitAspect(width, height, true);
    }
    render();
  }

  // --- Controls & Bindings ---

  bindFunctionsListEvents(functionsListEl, {
    onCycleColor: cycleColor,
    onToggleEquation: toggleEquation,
    onRemoveEquation: removeEquation,
    onRawInput: onRawInput,
    onCommit: onCommit,
  });

  bindControls({
    onAddEquation: (val) => addEquation(val),
    onAskClearAll: () => {
      if (equations.length > 0) setClearConfirmVisible(true);
    },
    onConfirmClearAll: clearAllEquations,
    onCancelClearAll: () => setClearConfirmVisible(false),
    onLoadExample: (exampleKey) => loadExample(exampleKey),
    onZoomIn: () => controller.zoomIn(),
    onZoomOut: () => controller.zoomOut(),
    onResetView: () => {
      if (isFullscreenOpen) {
        const w = renderer.getFsWidth();
        const h = renderer.getFsHeight();
        controller.resetView(w, h);
      } else {
        const w = renderer.getMainWidth();
        const h = renderer.getMainHeight();
        controller.resetView(w, h);
      }
      render();
    },
    onPanLeft: () => controller.panLeft(),
    onPanRight: () => controller.panRight(),
    onPanUp: () => controller.panUp(),
    onPanDown: () => controller.panDown(),
    onToggleGrid: () => {
      settings.showGrid = !settings.showGrid;
      setGridButtonActive(gridToggleBtn, settings.showGrid);
      render();
    },
    onExportPNG: (fromFs) => {
      renderer.exportToPng(fromFs, 'graph.png');
    },
    onGridSizeChange: (multiplier) => {
      settings.gridSizeMul = multiplier;
      render();
    },
    onLineWidthChange: (width) => {
      settings.lineWidth = width;
      render();
    },
    onToggleFullscreen: toggleFullscreen,
  });

  // Watch for dark-mode changes on <html>
  new MutationObserver(() => {
    render();
  }).observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });

  window.addEventListener('resize', handleResize);

  // Initial startup
  function startup() {
    renderFunctionsList(functionsListEl, equations);
    handleResize();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startup);
  } else {
    startup();
  }
})();

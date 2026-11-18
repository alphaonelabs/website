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
  let debounceTimer = null;
  let isFullscreenOpen = false;

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
    renderFunctionsList(functionsListEl, equations);
    render();
  }

  function onRawInput(id, val) {
    const eq = equations.find((e) => e.id === id);
    if (!eq) return;

    const wasArray = Array.isArray(eq.raw);
    eq.raw = wasArray ? splitTopLevel(val).map((s) => s.trim()).filter(Boolean) : val;

    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      compileEquation(eq);
      updateEquationInputState(eq.id, eq.errors.length > 0);
      render();
      refreshErrors();
    }, DEBOUNCE_DELAY);
  }

  function onCommit(id) {
    const eq = equations.find((e) => e.id === id);
    if (!eq) return;
    compileEquation(eq);
    renderFunctionsList(functionsListEl, equations);
    render();
    refreshErrors();
  }

  function clearAllEquations() {
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

  function setupFullscreen() {
    const w = window.innerWidth;
    const h = window.innerHeight - 44;
    renderer.resizeFullscreen(w, h);
    renderer.drawFullscreen(controller.getView(), equations, settings);
  }

  function toggleFullscreen() {
    isFullscreenOpen = !isFullscreenOpen;
    toggleFullscreenOverlay(fsOverlay, isFullscreenOpen);
    if (isFullscreenOpen) {
      setupFullscreen();
    }
  }

  // --- Layout & Resize ---

  function handleResize() {
    const { width, height } = renderer.resizeMain();
    controller.fitAspect(width, height);
    if (isFullscreenOpen) {
      setupFullscreen();
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
      const w = renderer.getMainWidth();
      const h = renderer.getMainHeight();
      controller.resetView(w, h);
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

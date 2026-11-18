/**
 * UI Component: DOM bindings, dynamic function list rendering, settings and overlays.
 */

import { GRID_CONFIG } from './config.js';

export function escapeHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * Renders the functions list rows into the container.
 * @param {HTMLElement} containerEl
 * @param {Array} equations
 */
export function renderFunctionsList(containerEl, equations) {
  if (!containerEl) return;

  if (!equations.length) {
    containerEl.innerHTML = `
      <div class="px-4 py-6 text-center text-sm text-gray-400 dark:text-gray-500">
        <i class="fas fa-chart-line text-2xl mb-2 block opacity-20"></i>
        No functions added yet
      </div>`;
    return;
  }

  containerEl.innerHTML = equations.map((eq, idx) => {
    const rawStr = Array.isArray(eq.raw) ? eq.raw.join(', ') : (eq.raw || '');
    const hasErr = eq.errors && eq.errors.length > 0;
    return `
    <div class="eq-row flex items-center gap-2.5 px-4 py-3 ${eq.enabled ? '' : 'dimmed'}" role="listitem">
      <button type="button"
        class="color-dot flex-shrink-0"
        style="background:${eq.color}"
        data-action="cycle-color"
        data-id="${eq.id}"
        title="Click to change colour"
        aria-label="Equation colour"
      ></button>
      <input
        id="eq-raw-${eq.id}"
        type="text"
        value="${escapeHtml(rawStr)}"
        placeholder="e.g. sin(x)"
        class="eq-raw-input flex-1 min-w-0 text-sm rounded-lg px-2.5 py-2 bg-gray-50 dark:bg-gray-700/60
               border ${hasErr ? 'border-red-400 dark:border-red-600' : 'border-gray-200 dark:border-gray-600'}
               text-gray-800 dark:text-gray-100 placeholder-gray-400
               focus:outline-none focus:ring-2 ${hasErr ? 'focus:ring-red-400' : 'focus:ring-teal-400'}
               transition-colors"
        data-id="${eq.id}"
        aria-label="Equation ${idx + 1}"
        autocomplete="off"
        spellcheck="false"
      />
      <button type="button"
        data-action="toggle-equation"
        data-id="${eq.id}"
        class="flex-shrink-0 w-7 h-7 flex items-center justify-center rounded-lg
               ${eq.enabled ? 'text-teal-500 hover:bg-teal-50 dark:hover:bg-teal-900/20' : 'text-gray-300 dark:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700'}
               transition-colors"
        title="${eq.enabled ? 'Hide' : 'Show'}"
        aria-pressed="${eq.enabled}"
        aria-label="${eq.enabled ? 'Hide' : 'Show'} equation ${idx + 1}"
      ><i class="fas ${eq.enabled ? 'fa-eye' : 'fa-eye-slash'} text-xs"></i></button>
      <button type="button"
        data-action="remove-equation"
        data-id="${eq.id}"
        class="flex-shrink-0 w-7 h-7 flex items-center justify-center rounded-lg
               text-gray-300 dark:text-gray-600 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
        title="Remove"
        aria-label="Remove equation ${idx + 1}"
      ><i class="fas fa-times text-xs"></i></button>
    </div>`;
  }).join('');
}

/**
 * Attaches delegated listeners to the equation list container.
 */
export function bindFunctionsListEvents(containerEl, callbacks) {
  if (!containerEl) return;

  containerEl.addEventListener('click', (e) => {
    const cycleBtn = e.target.closest('[data-action="cycle-color"]');
    if (cycleBtn && callbacks.onCycleColor) {
      callbacks.onCycleColor(Number(cycleBtn.dataset.id));
      return;
    }

    const toggleBtn = e.target.closest('[data-action="toggle-equation"]');
    if (toggleBtn && callbacks.onToggleEquation) {
      callbacks.onToggleEquation(Number(toggleBtn.dataset.id));
      return;
    }

    const removeBtn = e.target.closest('[data-action="remove-equation"]');
    if (removeBtn && callbacks.onRemoveEquation) {
      callbacks.onRemoveEquation(Number(removeBtn.dataset.id));
      return;
    }
  });

  containerEl.addEventListener('input', (e) => {
    if (e.target.classList.contains('eq-raw-input') && callbacks.onRawInput) {
      callbacks.onRawInput(Number(e.target.dataset.id), e.target.value);
    }
  });

  containerEl.addEventListener('keydown', (e) => {
    if (e.target.classList.contains('eq-raw-input') && e.key === 'Enter' && callbacks.onCommit) {
      callbacks.onCommit(Number(e.target.dataset.id));
    }
  });
}

/**
 * In-place styling update for an equation input to avoid re-rendering DOM during continuous typing.
 */
export function updateEquationInputState(id, hasError) {
  const input = document.getElementById(`eq-raw-${id}`);
  if (!input) return;
  input.classList.toggle('border-red-400', hasError);
  input.classList.toggle('dark:border-red-600', hasError);
  input.classList.toggle('border-gray-200', !hasError);
  input.classList.toggle('dark:border-gray-600', !hasError);
  input.classList.toggle('focus:ring-red-400', hasError);
  input.classList.toggle('focus:ring-teal-400', !hasError);
}

export function setClearConfirmVisible(show) {
  const btn = document.getElementById('clear-all-btn');
  const confirmWrap = document.getElementById('clear-confirm');
  if (!btn || !confirmWrap) return;

  if (show) {
    btn.classList.add('hidden');
    confirmWrap.classList.remove('hidden');
    confirmWrap.classList.add('flex');
  } else {
    btn.classList.remove('hidden');
    confirmWrap.classList.add('hidden');
    confirmWrap.classList.remove('flex');
  }
}

export function showErrorBanner(bannerEl, textEl, errors) {
  if (!bannerEl || !textEl) return;
  if (errors && errors.length > 0) {
    textEl.textContent = errors.join(' | ');
    bannerEl.classList.remove('hidden');
  } else {
    bannerEl.classList.add('hidden');
  }
}

export function updateCoordinates(coordsEl, x, y) {
  if (coordsEl) {
    coordsEl.textContent = `x = ${x.toFixed(3)},  y = ${y.toFixed(3)}`;
  }
}

export function resetCoordinates(coordsEl) {
  if (coordsEl) {
    coordsEl.textContent = 'Hover or touch the graph to see coordinates';
  }
}

export function updateViewRange(viewRangeEl, V) {
  if (!viewRangeEl) return;
  const f = (v) => parseFloat(v.toPrecision(4));
  viewRangeEl.textContent = `x [${f(V.xMin)}, ${f(V.xMax)}]  y [${f(V.yMin)}, ${f(V.yMax)}]`;
}

export function setGridButtonActive(btnEl, isGridVisible) {
  if (!btnEl) return;
  btnEl.classList.toggle('btn-inactive', !isGridVisible);
  btnEl.setAttribute('aria-pressed', String(isGridVisible));
}

export function toggleFullscreenOverlay(overlayEl, isOpen) {
  if (!overlayEl) return;
  if (isOpen) {
    overlayEl.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  } else {
    overlayEl.classList.add('hidden');
    document.body.style.overflow = '';
  }
}

/**
 * Binds all global page and toolbar controls.
 */
export function bindControls(callbacks) {
  // Equation input
  const eqInput = document.getElementById('eq-input');
  const addBtn = document.getElementById('eq-add-btn');

  if (eqInput) {
    eqInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && callbacks.onAddEquation) {
        callbacks.onAddEquation(eqInput.value);
        eqInput.value = '';
      }
    });
  }

  if (addBtn) {
    addBtn.addEventListener('click', () => {
      if (callbacks.onAddEquation && eqInput) {
        callbacks.onAddEquation(eqInput.value);
        eqInput.value = '';
        eqInput.focus();
      }
    });
  }

  // Clear all controls
  const clearAllBtn = document.getElementById('clear-all-btn');
  const clearYesBtn = document.getElementById('clear-confirm-yes');
  const clearNoBtn = document.getElementById('clear-confirm-no');

  if (clearAllBtn) {
    clearAllBtn.addEventListener('click', () => {
      if (callbacks.onAskClearAll) callbacks.onAskClearAll();
    });
  }
  if (clearYesBtn) {
    clearYesBtn.addEventListener('click', () => {
      if (callbacks.onConfirmClearAll) callbacks.onConfirmClearAll();
    });
  }
  if (clearNoBtn) {
    clearNoBtn.addEventListener('click', () => {
      if (callbacks.onCancelClearAll) callbacks.onCancelClearAll();
    });
  }

  // Example buttons
  document.querySelectorAll('[data-example]').forEach((btn) => {
    btn.addEventListener('click', () => {
      if (callbacks.onLoadExample) {
        callbacks.onLoadExample(btn.dataset.example);
      }
    });
  });

  // Zoom / Pan / Reset controls
  const zoomInBtn = document.getElementById('zoom-in-btn');
  const zoomOutBtn = document.getElementById('zoom-out-btn');
  const resetBtn = document.getElementById('reset-view-btn');
  const panLeftBtn = document.getElementById('pan-left-btn');
  const panRightBtn = document.getElementById('pan-right-btn');
  const panUpBtn = document.getElementById('pan-up-btn');
  const panDownBtn = document.getElementById('pan-down-btn');
  const gridToggleBtn = document.getElementById('grid-toggle-btn');
  const exportBtn = document.getElementById('export-png-btn');

  if (zoomInBtn) zoomInBtn.addEventListener('click', () => callbacks.onZoomIn?.());
  if (zoomOutBtn) zoomOutBtn.addEventListener('click', () => callbacks.onZoomOut?.());
  if (resetBtn) resetBtn.addEventListener('click', () => callbacks.onResetView?.());
  if (panLeftBtn) panLeftBtn.addEventListener('click', () => callbacks.onPanLeft?.());
  if (panRightBtn) panRightBtn.addEventListener('click', () => callbacks.onPanRight?.());
  if (panUpBtn) panUpBtn.addEventListener('click', () => callbacks.onPanUp?.());
  if (panDownBtn) panDownBtn.addEventListener('click', () => callbacks.onPanDown?.());
  if (gridToggleBtn) gridToggleBtn.addEventListener('click', () => callbacks.onToggleGrid?.());
  if (exportBtn) exportBtn.addEventListener('click', () => callbacks.onExportPNG?.(false));

  // Settings sliders
  const gridSizeRange = document.getElementById('grid-size-range');
  const gridSizeLabel = document.getElementById('grid-size-label');
  if (gridSizeRange) {
    gridSizeRange.addEventListener('input', (e) => {
      const val = e.target.value;
      if (gridSizeLabel) {
        gridSizeLabel.textContent = GRID_CONFIG.LABELS[val] || 'Normal';
      }
      callbacks.onGridSizeChange?.(GRID_CONFIG.MULTIPLIERS[val] || 1);
    });
  }

  const lineWidthRange = document.getElementById('line-width-range');
  const lineWidthLabel = document.getElementById('line-width-label');
  if (lineWidthRange) {
    lineWidthRange.addEventListener('input', (e) => {
      const val = parseFloat(e.target.value);
      if (lineWidthLabel) {
        lineWidthLabel.textContent = `${val}px`;
      }
      callbacks.onLineWidthChange?.(val);
    });
  }

  // Fullscreen controls
  const fullscreenBtn = document.getElementById('fullscreen-btn');
  const fsCloseBtn = document.getElementById('fs-close-btn');
  const fsExportBtn = document.getElementById('fs-export-btn');

  if (fullscreenBtn) {
    fullscreenBtn.addEventListener('click', () => callbacks.onToggleFullscreen?.());
  }
  if (fsCloseBtn) {
    fsCloseBtn.addEventListener('click', () => callbacks.onToggleFullscreen?.());
  }
  if (fsExportBtn) {
    fsExportBtn.addEventListener('click', () => callbacks.onExportPNG?.(true));
  }
}

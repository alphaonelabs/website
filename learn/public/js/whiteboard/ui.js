/**
 * UI controls, toolbar, fullscreen, and tool button states.
 */

export const TOOL_ICONS = {
  pen: 'fas fa-pen',
  highlighter: 'fas fa-highlighter',
  eraser: 'fas fa-eraser',
  line: 'fas fa-minus',
  rectangle: 'far fa-square',
  circle: 'far fa-circle',
  text: 'fas fa-font',
  arrow: 'fas fa-arrow-right'
};

export function escapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function setStatus(statusEl, text, isConnected) {
  if (!statusEl) return;
  statusEl.textContent = text;
  statusEl.className = 'text-xs ' + (isConnected
    ? 'text-teal-600 dark:text-teal-400 font-medium'
    : 'text-gray-500 dark:text-gray-400');
}

export function syncToolButtons(activeTool, canvas) {
  document.querySelectorAll('.tool-button').forEach((button) => {
    button.setAttribute('aria-pressed', button.dataset.tool === activeTool ? 'true' : 'false');
  });

  const activeToolIcon = document.querySelector('#active-tool-icon i');
  if (activeToolIcon && TOOL_ICONS[activeTool]) {
    activeToolIcon.className = `${TOOL_ICONS[activeTool]} text-xs text-teal-700 dark:text-teal-400`;
  }

  if (canvas) {
    if (activeTool === 'eraser') canvas.style.cursor = 'cell';
    else if (activeTool === 'text') canvas.style.cursor = 'text';
    else canvas.style.cursor = 'crosshair';
  }
}

function initToggleDropdown(btnId, dropdownId, wrapId, useFlex = false) {
  const btn = document.getElementById(btnId);
  const dropdown = document.getElementById(dropdownId);
  if (!btn || !dropdown) return;

  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    const isOpen = !dropdown.classList.contains('hidden');
    dropdown.classList.toggle('hidden', isOpen);
    if (useFlex) dropdown.classList.toggle('flex', !isOpen);
  });

  document.addEventListener('click', (e) => {
    if (!btn.closest(`#${wrapId}`).contains(e.target)) {
      dropdown.classList.add('hidden');
      if (useFlex) dropdown.classList.remove('flex');
    }
  });
}

export function initClickDropdowns() {
  initToggleDropdown('stroke-width-btn', 'stroke-width-dropdown', 'width-dropdown-wrap', true);
  initToggleDropdown('users-btn', 'users-dropdown', 'users-dropdown-wrap', false);
}

export function updateActiveUsersList(containerEl, countEl, participants) {
  const users = Array.isArray(participants) ? participants : [];
  if (countEl) countEl.textContent = String(users.length);
  if (!containerEl) return;

  if (!users.length) {
    containerEl.innerHTML = '<span class="text-gray-400">No signed-in users connected.</span>';
    return;
  }

  containerEl.innerHTML = users.map((user) => {
    const name = user.display_name || user.participant_id || 'User';
    return `<span class="rounded-full bg-teal-50 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300 px-2.5 py-0.5 font-medium text-[11px]">${escapeHtml(name)}</span>`;
  }).join('');
}

export function isFullscreen() {
  return Boolean(
    document.fullscreenElement ||
    document.webkitFullscreenElement ||
    document.mozFullScreenElement ||
    document.msFullscreenElement
  );
}

export function toggleFullscreen(container) {
  if (!isFullscreen()) {
    (container.requestFullscreen || container.webkitRequestFullscreen || container.msRequestFullscreen)
      ?.call(container);
  } else {
    (document.exitFullscreen || document.webkitExitFullscreen || document.msExitFullscreen)
      ?.call(document);
  }
}

export function updateFullscreenIcon(iconEl, btnEl) {
  if (!iconEl) return;
  if (isFullscreen()) {
    iconEl.className = 'fas fa-compress text-xs';
    if (btnEl) btnEl.title = 'Exit Fullscreen';
  } else {
    iconEl.className = 'fas fa-expand text-xs';
    if (btnEl) btnEl.title = 'Toggle Fullscreen';
  }
}

export function applyViewerRestrictions(canvas) {
  const viewerNote = document.getElementById('viewer-note');
  if (viewerNote) viewerNote.classList.remove('hidden');
  if (canvas) canvas.style.cursor = 'not-allowed';

  ['toolSelect', 'penColor', 'penWidth'].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.disabled = true;
  });

  ['undoBoard', 'redoBoard', 'clearBoard', 'uploadBoard', 'removeImage'].forEach((id) => {
    const btn = document.getElementById(id);
    if (btn) {
      btn.classList.add('opacity-50');
      btn.title = 'Sign in to use this control';
    }
  });
}

export function bindWhiteboardControls(callbacks = {}) {
  const {
    canInteract = true,
    onConnect = () => {},
    onToolChange = () => {},
    onColorChange = () => {},
    onWidthChange = () => {},
    onImageUpload = () => {},
    onDownload = () => {},
    onClear = () => {},
    onUndo = () => {},
    onRedo = () => {},
    onRequireLogin = () => {}
  } = callbacks;

  const roomInput = document.getElementById('room');
  const toolSelect = document.getElementById('toolSelect');
  const penColorInput = document.getElementById('penColor');
  const penWidthInput = document.getElementById('penWidth');
  const penWidthValue = document.getElementById('penWidthValue');
  const colorPreview = document.getElementById('color-preview');
  const loadInput = document.getElementById('loadInput');
  const container = document.getElementById('whiteboard-container');
  const fullscreenBtn = document.getElementById('fullscreen-btn');
  const fullscreenIcon = document.getElementById('fullscreen-icon');

  initClickDropdowns();

  document.getElementById('connect')?.addEventListener('click', onConnect);
  roomInput?.addEventListener('change', onConnect);

  toolSelect?.addEventListener('change', () => onToolChange(toolSelect.value));
  document.querySelectorAll('.tool-button').forEach((btn) => {
    btn.addEventListener('click', () => {
      toolSelect.value = btn.dataset.tool;
      onToolChange(btn.dataset.tool);
    });
  });

  penColorInput?.addEventListener('input', () => {
    if (colorPreview) colorPreview.style.backgroundColor = penColorInput.value;
    onColorChange(penColorInput.value);
  });

  penWidthInput?.addEventListener('input', () => {
    if (penWidthValue) penWidthValue.textContent = penWidthInput.value;
    onWidthChange(penWidthInput.value);
  });

  document.getElementById('uploadBoard')?.addEventListener('click', () => {
    if (!canInteract) { onRequireLogin(); return; }
    loadInput?.click();
  });

  loadInput?.addEventListener('change', (e) => {
    const file = e.target.files?.[0];
    if (file) {
      onImageUpload(file);
      e.target.value = '';
    }
  });

  document.getElementById('downloadBoard')?.addEventListener('click', onDownload);
  document.getElementById('clearBoard')?.addEventListener('click', onClear);
  document.getElementById('undoBoard')?.addEventListener('click', onUndo);
  document.getElementById('redoBoard')?.addEventListener('click', onRedo);

  fullscreenBtn?.addEventListener('click', () => toggleFullscreen(container));
  ['fullscreenchange', 'webkitfullscreenchange', 'mozfullscreenchange', 'MSFullscreenChange'].forEach((evt) => {
    document.addEventListener(evt, () => updateFullscreenIcon(fullscreenIcon, fullscreenBtn));
  });

  window.addEventListener('keydown', (e) => {
    if (['INPUT', 'SELECT', 'TEXTAREA'].includes(e.target.tagName)) return;
    if ((e.ctrlKey || e.metaKey) && (e.key === 'z' || e.key === 'Z')) {
      e.shiftKey ? onRedo() : onUndo();
      e.preventDefault();
    } else if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || e.key === 'Y')) {
      onRedo();
      e.preventDefault();
    }
  });
}

/**
 * Inline text editor overlay and hit-testing for whiteboard text elements.
 */

export class InlineTextEditor {
  constructor(viewportEl, canvas, options = {}) {
    this.viewportEl = viewportEl;
    this.canvas = canvas;
    this.onCommit = options.onCommit || (() => {});
    this.onCancel = options.onCancel || (() => {});
    this.activeEditor = null;
  }

  static getFontSize(event) {
    return Math.max(12, Number(event?.size || 4) * 5);
  }

  isOpen() {
    return Boolean(this.activeEditor);
  }

  open(normalizedPoint, existingEvent = null, defaultSize = 4, defaultColor = '#7a6418') {
    if (this.activeEditor) this.commit();

    const rect = this.canvas.getBoundingClientRect();
    const viewportRect = this.viewportEl.getBoundingClientRect();

    const pixelX = normalizedPoint.x * this.canvas.width;
    const pixelY = normalizedPoint.y * this.canvas.height;
    const cssLeft = rect.left - viewportRect.left + (pixelX / this.canvas.width) * rect.width;
    const cssTop = rect.top - viewportRect.top + (pixelY / this.canvas.height) * rect.height;

    const fontSize = existingEvent
      ? InlineTextEditor.getFontSize(existingEvent)
      : InlineTextEditor.getFontSize({ size: defaultSize });
    const scaledFontSize = fontSize * (rect.width / this.canvas.width);
    const color = existingEvent?.color || defaultColor;

    const textarea = document.createElement('textarea');
    textarea.id = 'inline-text-editor';
    textarea.placeholder = 'Type your text…';
    textarea.value = existingEvent?.text || '';
    textarea.style.left = cssLeft + 'px';
    textarea.style.top = (cssTop - scaledFontSize) + 'px';
    textarea.style.fontSize = scaledFontSize + 'px';
    textarea.style.color = color;
    textarea.style.lineHeight = '1.3';
    textarea.rows = 1;

    this.viewportEl.appendChild(textarea);
    textarea.focus();

    const autoResize = () => {
      textarea.style.height = 'auto';
      textarea.style.height = textarea.scrollHeight + 'px';
    };
    textarea.addEventListener('input', autoResize);
    autoResize();

    this.activeEditor = { textarea, point: normalizedPoint, existingEvent };

    textarea.addEventListener('blur', () => setTimeout(() => this.commit(), 0));
    textarea.addEventListener('keydown', (e) => {
      e.stopPropagation();
      if (e.key === 'Escape') {
        this.cancel();
      } else if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.commit();
      }
    });
  }

  commit() {
    if (!this.activeEditor) return;
    const { textarea, point, existingEvent } = this.activeEditor;
    const text = textarea.value.trim();
    this.activeEditor = null;
    textarea.remove();
    this.onCommit(text, point, existingEvent);
  }

  cancel() {
    if (!this.activeEditor) return;
    const { textarea } = this.activeEditor;
    this.activeEditor = null;
    textarea.remove();
    this.onCancel();
  }

  findTextEventAt(normalizedPoint, events) {
    const ctx = this.canvas.getContext('2d');
    const clickX = normalizedPoint.x * this.canvas.width;
    const clickY = normalizedPoint.y * this.canvas.height;

    for (let i = events.length - 1; i >= 0; i--) {
      const ev = events[i];
      if (!ev || ev.kind !== 'text' || !ev.from || !ev.text) continue;

      const textX = ev.from.x * this.canvas.width;
      const textY = ev.from.y * this.canvas.height;
      const fontSize = InlineTextEditor.getFontSize(ev);

      ctx.save();
      ctx.font = fontSize + 'px sans-serif';
      const measured = ctx.measureText(ev.text);
      ctx.restore();

      if (
        clickX >= textX &&
        clickX <= textX + measured.width &&
        clickY >= textY - fontSize &&
        clickY <= textY + 4
      ) {
        return ev;
      }
    }
    return null;
  }
}

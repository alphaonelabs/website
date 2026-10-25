/**
 * Handles pointer, touch, and mouse input on the canvas to coordinate freehand and shape drawing.
 */

import { generateEventId } from './storage.js';

export class DrawingController {
  constructor(canvas, renderer, textEditor, options = {}) {
    this.canvas = canvas;
    this.renderer = renderer;
    this.textEditor = textEditor;
    this.onSendEvent = options.onSendEvent || (() => {});
    this.onPreview = options.onPreview || (() => {});
    this.onRequireLogin = options.onRequireLogin || (() => {});
    this.getTool = options.getTool || (() => 'pen');
    this.getPenColor = options.getPenColor || (() => '#0f766e');
    this.getPenWidth = options.getPenWidth || (() => 4);
    this.canInteract = options.canInteract ?? true;
    this.getEvents = options.getEvents || (() => []);
    this.onCoordinates = options.onCoordinates || (() => {});
    this.onImageResize = options.onImageResize || (() => {});
    this.onImageResizeEnd = options.onImageResizeEnd || (() => {});

    this.drawing = false;
    this.startPoint = null;
    this.lastPoint = null;
    this.draftEvent = null;
    this.imageDrag = null;

    this.bindEvents();
  }

  currentMode() {
    const tool = this.getTool();
    if (tool === 'eraser') return 'eraser';
    if (tool === 'highlighter') return 'highlighter';
    if (tool === 'text') return 'text';
    if (['line', 'rectangle', 'circle', 'arrow'].includes(tool)) return 'shape';
    return 'pen';
  }

  makeEvent(kind, from, to, text = '') {
    const mode = this.currentMode();
    return {
      event_id: generateEventId(),
      kind,
      from,
      to: to || from,
      color: this.getPenColor(),
      size: Number(this.getPenWidth() || 4),
      mode,
      alpha: mode === 'highlighter' ? 0.3 : 1,
      text
    };
  }

  getCanvasPixelPoint(e) {
    const rect = this.canvas.getBoundingClientRect();
    const touch = e.touches && e.touches[0]
      ? e.touches[0]
      : (e.changedTouches && e.changedTouches[0] ? e.changedTouches[0] : e);
    const scaleX = rect.width > 0 ? (this.canvas.width / rect.width) : 1;
    const scaleY = rect.height > 0 ? (this.canvas.height / rect.height) : 1;
    return {
      x: (touch.clientX - rect.left) * scaleX,
      y: (touch.clientY - rect.top) * scaleY
    };
  }

  getImageHandleAt(point) {
    const b = this.renderer.imageBounds;
    if (!this.renderer.uploadedImage || !b) return null;

    // Move badge at top center
    const pillW = 60;
    const pillH = 20;
    const pillX = b.x + b.width / 2 - pillW / 2;
    const pillY = b.y - pillH - 6;
    if (point.x >= pillX && point.x <= pillX + pillW && point.y >= pillY && point.y <= pillY + pillH) {
      return { type: 'move', cursor: 'move' };
    }

    const radius = 15;
    const dist = (hx, hy) => Math.hypot(point.x - hx, point.y - hy);

    // 4 Corner handles
    if (dist(b.x, b.y) <= radius) return { type: 'resize', handle: 'nw', cursor: 'nwse-resize' };
    if (dist(b.x + b.width, b.y) <= radius) return { type: 'resize', handle: 'ne', cursor: 'nesw-resize' };
    if (dist(b.x + b.width, b.y + b.height) <= radius) return { type: 'resize', handle: 'se', cursor: 'nwse-resize' };
    if (dist(b.x, b.y + b.height) <= radius) return { type: 'resize', handle: 'sw', cursor: 'nesw-resize' };

    // 4 Edge circular handles
    if (dist(b.x + b.width / 2, b.y) <= radius) return { type: 'resize', handle: 'n', cursor: 'ns-resize' };
    if (dist(b.x + b.width / 2, b.y + b.height) <= radius) return { type: 'resize', handle: 's', cursor: 'ns-resize' };
    if (dist(b.x, b.y + b.height / 2) <= radius) return { type: 'resize', handle: 'w', cursor: 'ew-resize' };
    if (dist(b.x + b.width, b.y + b.height / 2) <= radius) return { type: 'resize', handle: 'e', cursor: 'ew-resize' };

    // Edge-dragging borders
    const edgeTol = 7;
    const inX = point.x >= b.x - edgeTol && point.x <= b.x + b.width + edgeTol;
    const inY = point.y >= b.y - edgeTol && point.y <= b.y + b.height + edgeTol;

    if (inX && Math.abs(point.y - b.y) <= edgeTol) return { type: 'resize', handle: 'n', cursor: 'ns-resize' };
    if (inX && Math.abs(point.y - (b.y + b.height)) <= edgeTol) return { type: 'resize', handle: 's', cursor: 'ns-resize' };
    if (inY && Math.abs(point.x - b.x) <= edgeTol) return { type: 'resize', handle: 'w', cursor: 'ew-resize' };
    if (inY && Math.abs(point.x - (b.x + b.width)) <= edgeTol) return { type: 'resize', handle: 'e', cursor: 'ew-resize' };

    return null;
  }

  updateToolCursor() {
    if (!this.canInteract) {
      this.canvas.style.cursor = 'not-allowed';
      return;
    }
    const tool = this.getTool();
    if (tool === 'eraser') {
      this.canvas.style.cursor = 'cell';
    } else if (tool === 'text') {
      this.canvas.style.cursor = 'text';
    } else {
      this.canvas.style.cursor = 'crosshair';
    }
  }

  start(e) {
    const pixelPoint = this.getCanvasPixelPoint(e);
    const handle = this.getImageHandleAt(pixelPoint);
    if (handle && this.renderer.imageBounds) {
      e.preventDefault();
      if (!this.canInteract) {
        this.onRequireLogin();
        return;
      }
      const b = this.renderer.imageBounds;
      this.imageDrag = {
        type: handle.type,
        handle: handle.handle,
        startPixel: pixelPoint,
        startBounds: { ...b },
        aspectRatio: b.height / b.width
      };
      return;
    }

    e.preventDefault();
    if (!this.canInteract) {
      this.onRequireLogin();
      return;
    }
    const point = this.renderer.pointFromEvent(e);
    this.onCoordinates(point);

    const tool = this.getTool();
    if (tool === 'text') {
      const existing = this.textEditor.findTextEventAt(point, this.getEvents());
      this.textEditor.open(point, existing, this.getPenWidth(), this.getPenColor());
      return;
    }

    this.drawing = true;
    this.startPoint = point;
    this.lastPoint = point;
    this.draftEvent = null;
  }

  move(e) {
    const pixelPoint = this.getCanvasPixelPoint(e);

    // Active image resize or drag operation
    if (this.imageDrag) {
      e.preventDefault();
      const { type, handle, startPixel, startBounds, aspectRatio } = this.imageDrag;
      const dx = pixelPoint.x - startPixel.x;
      const dy = pixelPoint.y - startPixel.y;
      let newBounds = { ...startBounds };

      if (type === 'move') {
        newBounds.x = Math.round(startBounds.x + dx);
        newBounds.y = Math.round(startBounds.y + dy);
      } else if (handle === 'se') {
        const newW = Math.max(50, startBounds.width + dx);
        newBounds.width = Math.round(newW);
        newBounds.height = Math.round(newW * aspectRatio);
      } else if (handle === 'sw') {
        const newW = Math.max(50, startBounds.width - dx);
        newBounds.x = Math.round(startBounds.x + (startBounds.width - newW));
        newBounds.width = Math.round(newW);
        newBounds.height = Math.round(newW * aspectRatio);
      } else if (handle === 'ne') {
        const newW = Math.max(50, startBounds.width + dx);
        const newH = newW * aspectRatio;
        newBounds.y = Math.round(startBounds.y + (startBounds.height - newH));
        newBounds.width = Math.round(newW);
        newBounds.height = Math.round(newH);
      } else if (handle === 'nw') {
        const newW = Math.max(50, startBounds.width - dx);
        const newH = newW * aspectRatio;
        newBounds.x = Math.round(startBounds.x + (startBounds.width - newW));
        newBounds.y = Math.round(startBounds.y + (startBounds.height - newH));
        newBounds.width = Math.round(newW);
        newBounds.height = Math.round(newH);
      } else if (handle === 'e') {
        const newW = Math.max(50, startBounds.width + dx);
        newBounds.width = Math.round(newW);
        newBounds.height = Math.round(newW * aspectRatio);
      } else if (handle === 'w') {
        const newW = Math.max(50, startBounds.width - dx);
        newBounds.x = Math.round(startBounds.x + (startBounds.width - newW));
        newBounds.width = Math.round(newW);
        newBounds.height = Math.round(newW * aspectRatio);
      } else if (handle === 's') {
        const newH = Math.max(40, startBounds.height + dy);
        newBounds.height = Math.round(newH);
        newBounds.width = Math.round(newH / aspectRatio);
      } else if (handle === 'n') {
        const newH = Math.max(40, startBounds.height - dy);
        newBounds.y = Math.round(startBounds.y + (startBounds.height - newH));
        newBounds.height = Math.round(newH);
        newBounds.width = Math.round(newH / aspectRatio);
      }

      this.renderer.imageBounds = newBounds;
      this.renderer.redrawAll(this.getEvents());
      this.onImageResize(newBounds);
      return;
    }

    // Dynamic cursor feedback when hovering over handles
    if (!this.drawing) {
      const handle = this.getImageHandleAt(pixelPoint);
      if (handle) {
        this.canvas.style.cursor = handle.cursor;
      } else {
        this.updateToolCursor();
      }
    }

    const point = this.renderer.pointFromEvent(e);
    this.onCoordinates(point);
    if (!this.drawing || !this.lastPoint) return;
    e.preventDefault();

    const tool = this.getTool();
    if (tool === 'pen' || tool === 'eraser' || tool === 'highlighter') {
      this.onSendEvent(this.makeEvent('stroke', this.lastPoint, point));
      this.lastPoint = point;
    } else {
      this.draftEvent = this.makeEvent(tool, this.startPoint, point);
      this.onPreview(this.draftEvent);
    }
  }

  stop(e) {
    if (this.imageDrag) {
      const finalBounds = this.renderer.imageBounds;
      this.imageDrag = null;
      this.onImageResizeEnd(finalBounds);
      this.updateToolCursor();
      return;
    }

    if (!this.drawing) return;
    this.drawing = false;

    const hasPointer = e && (
      typeof e.clientX === 'number' ||
      (e.touches && e.touches[0]) ||
      (e.changedTouches && e.changedTouches[0])
    );
    const point = hasPointer
      ? this.renderer.pointFromEvent(e.changedTouches && e.changedTouches[0] ? e.changedTouches[0] : e)
      : this.lastPoint;

    const tool = this.getTool();
    if (['line', 'rectangle', 'circle', 'arrow'].includes(tool)) {
      this.onSendEvent(this.makeEvent(tool, this.startPoint, point));
    }

    this.startPoint = null;
    this.lastPoint = null;
    this.draftEvent = null;
    this.updateToolCursor();
  }

  bindEvents() {
    this.start = this.start.bind(this);
    this.move = this.move.bind(this);
    this.stop = this.stop.bind(this);

    this.canvas.addEventListener('mousedown', this.start);
    this.canvas.addEventListener('mousemove', this.move);
    window.addEventListener('mouseup', this.stop);

    this.canvas.addEventListener('touchstart', this.start, { passive: false });
    this.canvas.addEventListener('touchmove', this.move, { passive: false });
    this.canvas.addEventListener('touchend', this.stop, { passive: false });
    this.canvas.addEventListener('mouseleave', (e) => {
      this.stop(e);
      this.updateToolCursor();
    });

    // Double-click to edit existing text
    this.canvas.addEventListener('dblclick', (e) => {
      if (!this.canInteract) return;
      const point = this.renderer.pointFromEvent(e);
      const textEv = this.textEditor.findTextEventAt(point, this.getEvents());
      if (textEv) {
        this.textEditor.open(point, textEv, this.getPenWidth(), this.getPenColor());
      }
    });
  }
}

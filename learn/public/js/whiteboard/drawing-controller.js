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

    this.drawing = false;
    this.startPoint = null;
    this.lastPoint = null;
    this.draftEvent = null;

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

  start(e) {
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
    this.canvas.addEventListener('mouseleave', this.stop);

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

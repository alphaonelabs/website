/**
 * Canvas 2D rendering engine for the Whiteboard.
 */

import { computeInitialImageBounds } from './storage.js';

export class WhiteboardRenderer {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.images = [];
    this.selectedImageIndex = -1;
    this.lastEvents = [];
  }

  setImages(images) {
    this.images = images || [];
  }

  addImage(img, bounds) {
    this.images.push({ img, bounds });
    this.selectedImageIndex = this.images.length - 1;
    return this.selectedImageIndex;
  }

  removeImage(index) {
    this.images.splice(index, 1);
    this.selectedImageIndex = -1;
  }

  pointFromEvent(event) {
    const rect = this.canvas.getBoundingClientRect();
    const touch = event.touches && event.touches[0] ? event.touches[0] : event;
    return {
      x: Math.max(0, Math.min(1, (touch.clientX - rect.left) / rect.width)),
      y: Math.max(0, Math.min(1, (touch.clientY - rect.top) / rect.height))
    };
  }

  px(point) {
    return {
      x: point.x * this.canvas.width,
      y: point.y * this.canvas.height
    };
  }

  setStyle(event) {
    const ctx = this.ctx;
    ctx.lineWidth = Number(event.size || 4);
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.strokeStyle = event.color || '#7a6418';
    ctx.fillStyle = event.color || '#7a6418';
    ctx.globalAlpha = Number(event.alpha || 1);
    ctx.globalCompositeOperation = event.mode === 'eraser' ? 'destination-out' : 'source-over';
  }

  drawArrow(from, to) {
    const ctx = this.ctx;
    const headlen = Math.max(10, Number(ctx.lineWidth || 4) * 3);
    const angle = Math.atan2(to.y - from.y, to.x - from.x);

    ctx.beginPath();
    ctx.moveTo(from.x, from.y);
    ctx.lineTo(to.x, to.y);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(to.x, to.y);
    ctx.lineTo(to.x - headlen * Math.cos(angle - Math.PI / 6), to.y - headlen * Math.sin(angle - Math.PI / 6));
    ctx.moveTo(to.x, to.y);
    ctx.lineTo(to.x - headlen * Math.cos(angle + Math.PI / 6), to.y - headlen * Math.sin(angle + Math.PI / 6));
    ctx.stroke();
  }

  drawEvent(event) {
    if (!event || !event.from) return;
    const kind = event.kind || 'stroke';
    const from = this.px(event.from);
    const to = this.px(event.to || event.from);
    const ctx = this.ctx;

    ctx.save();
    this.setStyle(event);

    if (kind === 'stroke' || kind === 'line') {
      ctx.beginPath();
      ctx.moveTo(from.x, from.y);
      ctx.lineTo(to.x, to.y);
      ctx.stroke();
    } else if (kind === 'rectangle') {
      ctx.strokeRect(from.x, from.y, to.x - from.x, to.y - from.y);
    } else if (kind === 'circle') {
      const radius = Math.hypot(to.x - from.x, to.y - from.y);
      ctx.beginPath();
      ctx.arc(from.x, from.y, radius, 0, Math.PI * 2);
      ctx.stroke();
    } else if (kind === 'arrow') {
      this.drawArrow(from, to);
    } else if (kind === 'text') {
      ctx.globalCompositeOperation = 'source-over';
      ctx.globalAlpha = 1;
      ctx.font = Math.max(12, Number(event.size || 4) * 5) + 'px sans-serif';
      ctx.fillText(event.text || '', from.x, from.y);
    }

    ctx.restore();
  }

  drawBackground(drawHandles = true) {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    for (const { img, bounds } of this.images) {
      const b = bounds || computeInitialImageBounds(img, this.canvas);
      this.ctx.drawImage(img, b.x, b.y, b.width, b.height);
    }
    const selected = this.images[this.selectedImageIndex];
    if (drawHandles && selected) {
      this.drawImageHandles(selected.bounds);
    }
  }

  drawImageHandles(bounds) {
    if (!bounds) return;
    const ctx = this.ctx;
    ctx.save();

    ctx.strokeStyle = '#7a6418';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([5, 4]);
    ctx.strokeRect(bounds.x, bounds.y, bounds.width, bounds.height);
    ctx.setLineDash([]);

    const pillW = 60;
    const pillH = 20;
    const pillX = bounds.x + bounds.width / 2 - pillW / 2;
    const pillY = bounds.y - pillH - 6;
    if (pillY >= 4) {
      ctx.fillStyle = '#7a6418';
      ctx.beginPath();
      if (typeof ctx.roundRect === 'function') {
        ctx.roundRect(pillX, pillY, pillW, pillH, 6);
      } else {
        ctx.rect(pillX, pillY, pillW, pillH);
      }
      ctx.fill();
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 11px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('✥ Move', pillX + pillW / 2, pillY + pillH / 2);
    }

    const drawHandle = (hx, hy) => {
      ctx.fillStyle = '#ffffff';
      ctx.strokeStyle = '#7a6418';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(hx, hy, 5.5, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    };

    drawHandle(bounds.x, bounds.y);
    drawHandle(bounds.x + bounds.width, bounds.y);
    drawHandle(bounds.x + bounds.width, bounds.y + bounds.height);
    drawHandle(bounds.x, bounds.y + bounds.height);
    drawHandle(bounds.x + bounds.width / 2, bounds.y);
    drawHandle(bounds.x + bounds.width / 2, bounds.y + bounds.height);
    drawHandle(bounds.x, bounds.y + bounds.height / 2);
    drawHandle(bounds.x + bounds.width, bounds.y + bounds.height / 2);

    ctx.restore();
  }

  redrawAll(events = [], extraEvent = null, drawHandles = true) {
    this.lastEvents = events;
    this.drawBackground(drawHandles);
    for (const event of events) {
      this.drawEvent(event);
    }
    if (extraEvent) {
      this.drawEvent(extraEvent);
    }
  }

  exportToPng(filenamePrefix = 'whiteboard') {
    const offscreen = document.createElement('canvas');
    offscreen.width = this.canvas.width;
    offscreen.height = this.canvas.height;
    const offCtx = offscreen.getContext('2d');
    offCtx.fillStyle = '#f8f9fa';
    offCtx.fillRect(0, 0, offscreen.width, offscreen.height);

    // Render without selection handles so the export is clean
    this.redrawAll(this.lastEvents || [], null, false);
    offCtx.drawImage(this.canvas, 0, 0);
    this.redrawAll(this.lastEvents || [], null, true);

    const safeName = filenamePrefix.replace(/[^A-Za-z0-9_-]+/g, '-');
    const link = document.createElement('a');
    link.href = offscreen.toDataURL('image/png');
    link.download = `${safeName}-whiteboard.png`;
    link.click();
  }
}

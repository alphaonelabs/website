/**
 * Canvas 2D rendering engine for the Whiteboard.
 */

export class WhiteboardRenderer {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.uploadedImage = null;
    this.imageScale = 1;
  }

  setBackgroundImage(image, scale = 1) {
    this.uploadedImage = image;
    this.imageScale = Number(scale || 1);
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
    ctx.strokeStyle = event.color || '#0f766e';
    ctx.fillStyle = event.color || '#0f766e';
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

  drawBackground() {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    if (this.uploadedImage) {
      this.ctx.drawImage(
        this.uploadedImage,
        0,
        0,
        this.uploadedImage.width * this.imageScale,
        this.uploadedImage.height * this.imageScale
      );
    }
  }

  redrawAll(events = [], extraEvent = null) {
    this.drawBackground();
    for (let i = 0; i < events.length; i++) {
      this.drawEvent(events[i]);
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
    offCtx.drawImage(this.canvas, 0, 0);

    const safeName = filenamePrefix.replace(/[^A-Za-z0-9_-]+/g, '-');
    const link = document.createElement('a');
    link.href = offscreen.toDataURL('image/png');
    link.download = `${safeName}-whiteboard.png`;
    link.click();
  }
}

export function segmentsIntersect(x1, y1, x2, y2, x3, y3, x4, y4) {
  const denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4);
  if (denom === 0) return false;
  const t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom;
  const u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom;
  return t >= 0 && t <= 1 && u >= 0 && u <= 1;
}

export function segmentIntersectsRect(x1, y1, x2, y2, rx, ry, rw, rh) {
  if (x2 >= rx && x2 <= rx + rw && y2 >= ry && y2 <= ry + rh) return true;
  return (
    segmentsIntersect(x1, y1, x2, y2, rx, ry, rx + rw, ry) ||
    segmentsIntersect(x1, y1, x2, y2, rx + rw, ry, rx + rw, ry + rh) ||
    segmentsIntersect(x1, y1, x2, y2, rx, ry + rh, rx + rw, ry + rh) ||
    segmentsIntersect(x1, y1, x2, y2, rx, ry, rx, ry + rh)
  );
}

export function pointToSegmentDist(px, py, x1, y1, x2, y2) {
  const A = px - x1, B = py - y1, C = x2 - x1, D = y2 - y1;
  const lenSq = C * C + D * D;
  const param = lenSq !== 0 ? Math.max(0, Math.min(1, (A * C + B * D) / lenSq)) : 0;
  return Math.hypot(px - (x1 + param * C), py - (y1 + param * D));
}

export function beamIntersectsBlock(x1, y1, x2, y2, block) {
  const cx = block.x + block.size / 2, cy = block.y + block.size / 2;
  if (block.shape === 'circle') {
    return pointToSegmentDist(cx, cy, x1, y1, x2, y2) < block.size / 2;
  } else if (block.shape === 'triangle') {
    const tx1 = block.x + block.size / 2, ty1 = block.y;
    const tx2 = block.x, ty2 = block.y + block.size;
    const tx3 = block.x + block.size, ty3 = block.y + block.size;
    return (
      segmentsIntersect(x1, y1, x2, y2, tx1, ty1, tx2, ty2) ||
      segmentsIntersect(x1, y1, x2, y2, tx2, ty2, tx3, ty3) ||
      segmentsIntersect(x1, y1, x2, y2, tx3, ty3, tx1, ty1)
    );
  } else {
    return segmentIntersectsRect(x1, y1, x2, y2, block.x, block.y, block.size, block.size);
  }
}

export function getColorName(hslColor) {
  const match = hslColor.match(/hsl\((\d+)/);
  if (!match) return hslColor;
  const hue = parseInt(match[1]);
  const names = [
    [15, 'Red'], [45, 'Orange'], [75, 'Yellow'], [105, 'Yellow-Green'],
    [135, 'Green'], [165, 'Teal'], [195, 'Cyan'], [225, 'Sky Blue'],
    [255, 'Blue'], [285, 'Purple'], [315, 'Magenta'], [345, 'Pink'],
  ];
  for (const [max, name] of names) {
    if (hue < max) return name;
  }
  return 'Red';
}

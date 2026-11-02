const SUPPORTED_TYPES = new Set([
    'button', 'input', 'text', 'image', 'navbar', 'table',
    'modal', 'frame', 'browser', 'mobile'
]);

function number(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
}

function text(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&apos;');
}

function geometry(element) {
    const x = number(element.x);
    const y = number(element.y);
    const width = Math.max(0, number(element.width));
    const height = Math.max(0, number(element.height));
    return { x, y, width, height };
}

function label(element, x, y, width, height, options = {}) {
    const cx = x + width / 2;
    const cy = y + height / 2;
    return `<text x="${options.start ? x + 12 : cx}" y="${cy}" fill="#333333" font-family="Arial, sans-serif" font-size="${options.fontSize || 14}" ${options.start ? 'text-anchor="start"' : 'text-anchor="middle"'} dominant-baseline="middle">${text(element.text)}</text>`;
}

export function elementToSvg(element) {
    const { x, y, width, height } = geometry(element);
    const type = element.type || '';
    if (!SUPPORTED_TYPES.has(type)) {
        return `<!-- Unsupported Mockuper element type: ${text(type)} -->`;
    }

    switch (type) {
        case 'button':
            return `<g data-element-id="${text(element.id)}" data-type="button"><rect x="${x}" y="${y}" width="${width}" height="${height}" rx="6" fill="#ffffff" stroke="#333333" stroke-width="3"/><text x="${x + width / 2}" y="${y + height / 2}" fill="#333333" font-family="Arial, sans-serif" font-size="14" font-weight="bold" text-anchor="middle" dominant-baseline="middle">${text(element.text)}</text></g>`;
        case 'input':
            return `<g data-element-id="${text(element.id)}" data-type="input"><rect x="${x}" y="${y}" width="${width}" height="${height}" rx="4" fill="#ffffff" stroke="#666666" stroke-width="2"/><text x="${x + 12}" y="${y + height / 2}" fill="#666666" font-family="Arial, sans-serif" font-size="14" text-anchor="start" dominant-baseline="middle">${text(element.text)}</text></g>`;
        case 'text':
            return `<g data-element-id="${text(element.id)}" data-type="text">${label(element, x, y, width, height, { start: true })}</g>`;
        case 'image':
            return `<g data-element-id="${text(element.id)}" data-type="image"><rect x="${x}" y="${y}" width="${width}" height="${height}" fill="#e8e8e8" stroke="#333333" stroke-width="3"/><line x1="${x}" y1="${y}" x2="${x + width}" y2="${y + height}" stroke="#cccccc" stroke-width="2"/><line x1="${x + width}" y1="${y}" x2="${x}" y2="${y + height}" stroke="#cccccc" stroke-width="2"/></g>`;
        case 'navbar':
            return `<g data-element-id="${text(element.id)}" data-type="navbar"><rect x="${x}" y="${y}" width="${width}" height="${height}" fill="#d0d0d0" stroke="#333333" stroke-width="3"/>${label(element, x, y, width, height, { fontSize: 14 })}</g>`;
        case 'table': {
            const parts = [`<g data-element-id="${text(element.id)}" data-type="table"><rect x="${x}" y="${y}" width="${width}" height="${height}" fill="#ffffff" stroke="#333333" stroke-width="3"/>`];
            for (let col = 1; col < 3; col++) {
                const lineX = x + width * col / 3;
                parts.push(`<line x1="${lineX}" y1="${y}" x2="${lineX}" y2="${y + height}" stroke="#333333" stroke-width="1"/>`);
            }
            for (let row = 1; row < 3; row++) {
                const lineY = y + height * row / 3;
                parts.push(`<line x1="${x}" y1="${lineY}" x2="${x + width}" y2="${lineY}" stroke="#333333" stroke-width="1"/>`);
            }
            for (let index = 0; index < 9; index++) {
                const col = index % 3;
                const row = Math.floor(index / 3);
                const cellX = x + width * col / 3;
                const cellY = y + height * row / 3;
                parts.push(`<text x="${cellX + 6}" y="${cellY + 16}" fill="#333333" font-family="Arial, sans-serif" font-size="12">Cell ${index + 1}</text>`);
            }
            parts.push('</g>');
            return parts.join('');
        }
        case 'modal':
            return `<g data-element-id="${text(element.id)}" data-type="modal"><rect x="${x}" y="${y}" width="${width}" height="${height}" rx="8" fill="#f5f5f5" stroke="#333333" stroke-width="4"/>${label(element, x, y, width, height, { fontSize: 14 })}</g>`;
        case 'frame':
            return `<g data-element-id="${text(element.id)}" data-type="frame"><rect x="${x}" y="${y}" width="${width}" height="${height}" fill="none" stroke="#666666" stroke-width="3" stroke-dasharray="8 5"/>${label(element, x, y, width, height, { fontSize: 14 })}</g>`;
        case 'browser': {
            const barHeight = Math.min(40, height);
            const contentY = y + barHeight;
            return `<g data-element-id="${text(element.id)}" data-type="browser"><rect x="${x}" y="${y}" width="${width}" height="${height}" rx="8" fill="#ffffff" stroke="#333333" stroke-width="3"/><rect x="${x}" y="${y}" width="${width}" height="${barHeight}" rx="6" fill="#d0d0d0" stroke="#333333" stroke-width="2"/><circle cx="${x + 14}" cy="${y + barHeight / 2}" r="6" fill="#ffffff" stroke="#333333" stroke-width="2"/><circle cx="${x + 30}" cy="${y + barHeight / 2}" r="6" fill="#ffffff" stroke="#333333" stroke-width="2"/><circle cx="${x + 46}" cy="${y + barHeight / 2}" r="6" fill="#ffffff" stroke="#333333" stroke-width="2"/><rect x="${x + 62}" y="${y + 8}" width="${Math.max(20, width - 74)}" height="${Math.max(12, barHeight - 16)}" rx="4" fill="#ffffff" stroke="#333333" stroke-width="2"/><text x="${x + 68}" y="${y + barHeight / 2}" fill="#333333" font-family="Arial, sans-serif" font-size="11" dominant-baseline="middle">https://example.com</text><text x="${x + 16}" y="${contentY + 30}" fill="#333333" font-family="Arial, sans-serif" font-size="14">${text(element.text)}</text></g>`;
        }
        case 'mobile': {
            const headerHeight = 24;
            const footerHeight = 40;
            return `<g data-element-id="${text(element.id)}" data-type="mobile"><rect x="${x}" y="${y}" width="${width}" height="${height}" rx="24" fill="#ffffff" stroke="#333333" stroke-width="4"/><rect x="${x + 8}" y="${y + 12}" width="${Math.max(0, width - 16)}" height="${headerHeight}" fill="#f5f5f5"/><line x1="${x + width / 2 - 30}" y1="${y + 20}" x2="${x + width / 2 + 30}" y2="${y + 20}" stroke="#666666" stroke-width="4" stroke-linecap="round"/><text x="${x + 16}" y="${y + 54}" fill="#333333" font-family="Arial, sans-serif" font-size="14">${text(element.text)}</text><rect x="${x + 8}" y="${y + height - footerHeight - 12}" width="${Math.max(0, width - 16)}" height="${footerHeight}" fill="#f5f5f5"/><line x1="${x + width / 2 - 25}" y1="${y + height - 24}" x2="${x + width / 2 + 25}" y2="${y + height - 24}" stroke="#333333" stroke-width="4" stroke-linecap="round"/></g>`;
        }
        default:
            return `<!-- Unsupported Mockuper element type: ${text(type)} -->`;
    }
}

export function pageToSvg(page) {
    const elements = Array.isArray(page?.elements) ? [...page.elements] : [];
    elements.sort((a, b) => number(a.zIndex) - number(b.zIndex));

    let maxX = 800;
    let maxY = 600;
    elements.forEach(element => {
        const { x, y, width, height } = geometry(element);
        maxX = Math.max(maxX, x + width + 40);
        maxY = Math.max(maxY, y + height + 40);
    });

    const body = elements.map(elementToSvg).join('\n  ');
    return `<svg xmlns="http://www.w3.org/2000/svg" width="${maxX}" height="${maxY}" viewBox="0 0 ${maxX} ${maxY}">
  <rect x="0" y="0" width="${maxX}" height="${maxY}" fill="#ffffff"/>
  ${body}
</svg>`;
}

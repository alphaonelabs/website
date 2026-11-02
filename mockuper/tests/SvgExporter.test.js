import test from 'node:test';
import assert from 'node:assert/strict';
import { elementToSvg, pageToSvg } from '../js/modules/SvgExporter.js';

const types = [
    'button', 'input', 'text', 'image', 'navbar',
    'table', 'modal', 'frame', 'browser', 'mobile'
];

test('exports every Mockuper component type as SVG markup', () => {
    for (const type of types) {
        const svg = elementToSvg({
            id: `${type}-1`,
            type,
            x: 10,
            y: 20,
            width: 200,
            height: 100,
            text: `${type} label`,
            zIndex: 0
        });
        assert.match(svg, /^<g /);
        assert.match(svg, new RegExp(`data-type="${type}"`));
    }
});

test('button SVG includes its geometry and text', () => {
    const svg = elementToSvg({
        id: 'button-1', type: 'button', x: 12, y: 34, width: 120, height: 40,
        text: 'Save', zIndex: 0
    });
    assert.match(svg, /<rect x="12" y="34" width="120" height="40"/);
    assert.match(svg, />Save<\/text>/);
});

test('text SVG escapes XML-sensitive characters', () => {
    const svg = elementToSvg({
        id: 'text-1', type: 'text', x: 0, y: 0, width: 100, height: 30,
        text: '<Heading & "notes">', zIndex: 0
    });
    assert.match(svg, /&lt;Heading &amp; &quot;notes&quot;&gt;/);
    assert.doesNotMatch(svg, /<Heading/);
});

test('table SVG contains three columns and three rows of cells', () => {
    const svg = elementToSvg({
        id: 'table-1', type: 'table', x: 0, y: 0, width: 300, height: 180,
        text: '', zIndex: 0
    });
    assert.equal((svg.match(/<line/g) || []).length, 4);
    assert.match(svg, /Cell 9/);
});

test('browser SVG includes its toolbar and address bar', () => {
    const svg = elementToSvg({
        id: 'browser-1', type: 'browser', x: 0, y: 0, width: 800, height: 600,
        text: 'Browser Content', zIndex: 0
    });
    assert.match(svg, /https:\/\/example\.com/);
    assert.match(svg, /Browser Content/);
});

test('mobile SVG includes header, footer, and page text', () => {
    const svg = elementToSvg({
        id: 'mobile-1', type: 'mobile', x: 0, y: 0, width: 375, height: 667,
        text: 'Mobile App', zIndex: 0
    });
    assert.match(svg, /data-type="mobile"/);
    assert.match(svg, /Mobile App/);
});

test('unsupported component types return an SVG comment instead of invalid markup', () => {
    const svg = elementToSvg({
        id: 'custom-1', type: 'custom', x: 0, y: 0, width: 10, height: 10, text: ''
    });
    assert.match(svg, /^<!-- Unsupported Mockuper element type: custom -->$/);
});

test('page SVG is valid, includes a white background, and sorts by z-index', () => {
    const svg = pageToSvg({
        elements: [
            { id: '2', type: 'text', x: 400, y: 300, width: 100, height: 30, text: 'Front', zIndex: 2 },
            { id: '1', type: 'button', x: 10, y: 20, width: 120, height: 40, text: 'Back', zIndex: 1 }
        ]
    });
    assert.match(svg, /^<svg xmlns="http:\/\/www\.w3\.org\/2000\/svg"/);
    assert.match(svg, /fill="#ffffff"/);
    assert.ok(svg.indexOf('data-element-id="1"') < svg.indexOf('data-element-id="2"'));
    assert.match(svg, /<\/svg>$/);
});

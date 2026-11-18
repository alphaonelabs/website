/**
 * Graphing Calculator Configuration and Constants
 */

export const PALETTE = [
  '#0d9488', '#7c3aed', '#dc2626', '#2563eb',
  '#d97706', '#db2777', '#059669', '#9333ea',
  '#0891b2', '#ea580c', '#65a30d', '#c026d3',
];

export const DEFAULT_VIEW = {
  xMin: -10,
  xMax: 10,
  yMin: -7,
  yMax: 7,
};

export const GRID_CONFIG = {
  LABELS: {
    '1': 'Fine',
    '2': 'Normal',
    '3': 'Coarse',
  },
  MULTIPLIERS: {
    '1': 0.5,
    '2': 1,
    '3': 2,
  },
};

export const LINE_WIDTH_CONFIG = {
  DEFAULT: 2,
  FULLSCREEN_OFFSET: 0.5,
};

export const NAVIGATION = {
  PAN_STEP: 0.18,
  ZOOM_IN_FACTOR: 0.72,
  ZOOM_OUT_FACTOR: 1.39,
  WHEEL_ZOOM_IN: 0.88,
  WHEEL_ZOOM_OUT: 1.14,
};

export const DEBOUNCE_DELAY = 280;

export const EXAMPLES = {
  parabola: {
    label: 'Parabola',
    mathDisplay: 'x²',
    exprs: ['x^2'],
  },
  sine: {
    label: 'Sine Wave',
    mathDisplay: 'sin(x)',
    exprs: ['sin(x)'],
  },
  circle: {
    label: 'Circle',
    mathDisplay: 'x²+y²=9',
    exprs: ['sqrt(9-x^2)', '-sqrt(9-x^2)'],
  },
  tangent: {
    label: 'Tangent',
    mathDisplay: 'tan(x)',
    exprs: ['tan(x)'],
  },
  logarithm: {
    label: 'Logarithm',
    mathDisplay: 'log(x)',
    exprs: ['log10(x)'],
  },
  exponential: {
    label: 'Exponential',
    mathDisplay: 'eˣ',
    exprs: ['exp(x)'],
  },
};

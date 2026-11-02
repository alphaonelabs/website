// Shared Tailwind theme for learn: loaded right after the Tailwind CDN script.
// Alpha One Labs brand palette. learn's teal/cyan accent classes map onto a
// gold scale so every page picks up the brand without per-page edits.
// 600/700 are darkened from gold-deep so white text and gold text on white
// meet WCAG AA (600 on white 5.4:1, white on 600 5.4:1).
window.A1_TAILWIND_THEME = {
  colors: (function () {
    var gold = { 50: '#fbf8ee', 100: '#f6efd9', 200: '#ecdeb0', 300: '#e2c66a', 400: '#c7ab4f', 500: '#9a8236', 600: '#7c692e', 700: '#685721', 800: '#524520', 900: '#3a3117', 950: '#221d0d' };
    // Neutral (non-blue) grays for structure: white/black pages, #0f0f0f raised surfaces in dark.
    var neutral = { 50: '#fafafa', 100: '#f5f5f5', 200: '#e6e6e6', 300: '#d8d8d8', 400: '#a3a3a3', 500: '#737373', 600: '#4a4a4a', 700: '#333333', 800: '#121212', 900: '#0a0a0a', 950: '#050505' };
    // No rainbow accents: warm hues fold into brass, cool/green hues into neutral gray. Red stays for errors.
    return { teal: gold, cyan: gold, gold: gold, orange: gold, amber: gold, yellow: gold,
      gray: neutral, slate: neutral, zinc: neutral, neutral: neutral, stone: neutral,
      purple: neutral, violet: neutral, indigo: neutral, blue: neutral, sky: neutral, fuchsia: neutral, pink: neutral, rose: neutral,
      green: neutral, emerald: neutral, lime: neutral,
      a1: { black: '#000000', white: '#ffffff', gold: '#c7ab4f', 'gold-bright': '#e2c66a', 'gold-deep': '#9a8236' } };
  })(),
  fontFamily: {
    sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
    display: ['Barlow Condensed', 'Arial Narrow', 'Impact', 'sans-serif'],
    mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace']
  },
  // Design system v2: near-square corners (tags 2px, buttons/inputs 4px, cards 6px,
  // panels 8px). `full` stays round for avatars and status dots.
  borderRadius: { sm: '2px', DEFAULT: '4px', md: '4px', lg: '4px', xl: '6px', '2xl': '6px', '3xl': '8px' },
  // Hard 1px borders instead of soft drop shadows.
  boxShadow: { sm: 'none', DEFAULT: 'none', md: 'none', lg: 'none', xl: 'none', '2xl': 'none', inner: 'none' }
};
window.applyA1TailwindTheme = function () {
  var cfg = window.tailwind && window.tailwind.config ? window.tailwind.config : {};
  var theme = cfg.theme || {};
  var extend = theme.extend || {};
  window.tailwind.config = Object.assign({}, cfg, {
    darkMode: cfg.darkMode || 'class',
    theme: Object.assign({}, theme, {
      extend: Object.assign({}, extend, {
        colors: Object.assign({}, extend.colors || {}, window.A1_TAILWIND_THEME.colors),
        fontFamily: Object.assign({}, extend.fontFamily || {}, window.A1_TAILWIND_THEME.fontFamily),
        borderRadius: Object.assign({}, extend.borderRadius || {}, window.A1_TAILWIND_THEME.borderRadius),
        boxShadow: Object.assign({}, extend.boxShadow || {}, window.A1_TAILWIND_THEME.boxShadow)
      })
    })
  });
};
tailwind.config = { darkMode: 'class', theme: { extend: {} } };
window.applyA1TailwindTheme();

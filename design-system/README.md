# Alpha One Labs design system

Live guide: **https://design.alphaonelabs.com**

```html
<link rel="stylesheet" href="https://design.alphaonelabs.com/brand.css">
<script src="https://design.alphaonelabs.com/chrome.js" defer></script>

<a1-header site="Your site" sticky></a1-header>
<main style="background: var(--a1-bg); color: var(--a1-text)">…</main>
<a1-footer source="your-folder"></a1-footer>
```

- `brand.css`: tokens (`--a1-*`) and opt-in `.a1-*` components, light and dark.
- `tokens.json`: the same tokens as data.
- `chrome.js`: the shared `<a1-header>` and `<a1-footer>`, plus the cross-site theme toggle (`window.A1Theme`).
- `assets/`: the A1 logo, the mascot portraits, and PCB-style circuit art (`scripts-circuits.py` regenerates the `pcb-*.svg` files).
- `build-kit.py`: rebuilds `downloads/alpha-one-labs-design-system.zip`.

Brand direction: sharp, editorial, intelligent. Plain white and black, brass gold used sparingly, hard borders, condensed uppercase headlines. Lead with learning, activities, teaching and community.

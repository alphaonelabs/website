/*
 * Alpha One Labs shared site chrome — https://design.alphaonelabs.com
 *
 *   <script src="https://design.alphaonelabs.com/chrome.js" defer></script>
 *   <a1-header site="QuantaLab" site-href="/"></a1-header>
 *   ...your page...
 *   <a1-footer source="quantalab"></a1-footer>
 *
 * Both elements render inside Shadow DOM, so they never inherit or leak styles.
 * <a1-header> attributes:
 *   site       name shown next to the mark (optional)
 *   site-href  where the site name links (default "/")
 *   theme      "dark" (default) or "light"
 *   sticky     present = stick to the top while scrolling
 * Put site-specific links in the header with slot="actions".
 * <a1-footer> attributes:
 *   source     folder in alphaonelabs/website, for the "Edit on GitHub" link
 *   theme      "dark" (default) or "light"
 */
(() => {
  const MARK = `<svg viewBox="-4 -4 440 494" aria-hidden="true" class="mark">
    <path d="M140.08 0L431.86 145.89L431.86 438.37L140.08 292.48Z" fill="#000" stroke="#fff" stroke-width="10"/>
    <path d="M317.72 163.61H377.27V342.25H347.5V193.38H317.72Z" fill="#fff"/>
    <path d="M0.14 56.42L285.96 199.34L285.96 485.16L0.14 342.25Z" fill="#fff" stroke="#000" stroke-width="10"/>
    <path fill="#000" fill-rule="evenodd" d="M124.41 164.3H161.54L219.47 342.25H185.04L171.54 300.49H114.66L101.19 342.25H66.76ZM143.06 212.45L122.66 274.56H163.14Z"/>
  </svg>`;

  const SITES = [
    ["Learn", "https://learn.alphaonelabs.com"],
    ["Virtual World", "https://virtual.alphaonelabs.com"],
    ["QuantaLab", "https://quantalab.alphaonelabs.com"],
    ["BotLab", "https://botlab.alphaonelabs.com"],
    ["VoxBridge", "https://voxbridge.alphaonelabs.com"],
    ["EarthMind", "https://earthmind.alphaonelabs.com"],
    ["Mockuper", "https://mockuper.alphaonelabs.com"],
    ["PMOSS", "https://pmoss.alphaonelabs.com"],
    ["GSoC", "https://gsoc.alphaonelabs.com"],
  ];
  const REPO = "https://github.com/alphaonelabs/website";

  // Theme: follow the system unless the visitor picked one. The choice lives in
  // a cookie on .alphaonelabs.com so it carries across every subdomain.
  const html = document.documentElement;
  const light = matchMedia("(prefers-color-scheme: light)");
  const saved = () => (document.cookie.match(/(?:^|; )a1-theme=(light|dark)/) || [])[1] || null;
  const current = () => html.getAttribute("data-a1-theme") || (light.matches ? "light" : "dark");
  const listeners = new Set();
  const notify = () => {
    const theme = current();
    listeners.forEach((fn) => fn(theme));
    document.dispatchEvent(new CustomEvent("a1-themechange", { detail: { theme } }));
  };
  if (saved()) html.setAttribute("data-a1-theme", saved());
  light.addEventListener("change", () => { if (!saved()) notify(); });
  window.A1Theme = {
    get: current,
    set(theme) {
      const domain = location.hostname.endsWith("alphaonelabs.com") ? "; domain=.alphaonelabs.com" : "";
      document.cookie = `a1-theme=${theme}; path=/; max-age=31536000; SameSite=Lax${domain}`;
      html.setAttribute("data-a1-theme", theme);
      notify();
    },
    toggle() { this.set(current() === "light" ? "dark" : "light"); },
  };
  const followTheme = (el) => {
    const sync = () => el.setAttribute("data-mode", el.getAttribute("theme") || current());
    sync();
    listeners.add(sync);
    return sync;
  };

  const THEME = `
    :host { --bg:#000; --fg:#fff; --muted:#a3a3a3; --line:#2e2e2e; --gold:#c7ab4f; --gold-hi:#e2c66a; --hover:#141414;
            display:block; font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif; }
    :host([data-mode="light"]) { --bg:#fff; --fg:#000; --muted:#525252; --line:#e4e4e4; --gold:#7c692e; --gold-hi:#000; --hover:#f2f2f2; }
    *, *::before, *::after { box-sizing:border-box; }
    a { color:inherit; text-decoration:none; }
    a:focus-visible, button:focus-visible, summary:focus-visible { outline:2px solid var(--gold-hi); outline-offset:3px; border-radius:6px; }
    .mark { width:30px; height:auto; flex:none; }
  `;

  class A1Header extends HTMLElement {
    connectedCallback() {
      if (this.shadowRoot) return;
      const site = this.getAttribute("site");
      const siteHref = this.getAttribute("site-href") || "/";
      const root = this.attachShadow({ mode: "open" });
      followTheme(this);
      const showToggle = !this.hasAttribute("theme") && !this.hasAttribute("no-theme-toggle");
      if (this.hasAttribute("sticky")) Object.assign(this.style, { position: "sticky", top: "0", zIndex: "1000" });
      const links = [
        ["Learn", "https://learn.alphaonelabs.com"],
        ["GSoC", "https://gsoc.alphaonelabs.com"],
        ["Design", "https://design.alphaonelabs.com"],
      ];
      root.innerHTML = `<style>${THEME}
        header { background:var(--bg); color:var(--fg); border-bottom:1px solid var(--line); }
        .bar { max-width:1200px; margin:0 auto; height:64px; padding:0 20px; display:flex; align-items:center; gap:16px; }
        .brand { display:flex; align-items:center; gap:12px; font-family:"Space Grotesk",Inter,sans-serif; font-weight:700; font-size:17px; letter-spacing:-0.01em; white-space:nowrap; }
        .site { color:var(--muted); font-weight:500; }
        .site::before { content:"/"; margin:0 10px 0 2px; color:var(--line); }
        .site:hover { color:var(--gold); }
        nav { margin-left:auto; display:flex; align-items:center; gap:4px; }
        nav a, summary { padding:8px 12px; border-radius:999px; font-size:14px; font-weight:500; color:var(--muted); cursor:pointer; transition:color .15s, background .15s; }
        nav a:hover, summary:hover { color:var(--fg); background:var(--hover); }
        details { position:relative; }
        summary { list-style:none; display:flex; align-items:center; gap:6px; }
        summary::-webkit-details-marker { display:none; }
        summary::after { content:""; width:6px; height:6px; border:solid currentColor; border-width:0 1.5px 1.5px 0; transform:rotate(45deg) translateY(-2px); }
        .menu { position:absolute; right:0; top:calc(100% + 8px); min-width:220px; padding:8px; background:var(--bg); border:1px solid var(--line); border-radius:14px; box-shadow:0 12px 40px rgb(0 0 0 / .35); display:grid; }
        .menu a { padding:9px 12px; border-radius:8px; color:var(--fg); }
        .menu a:hover { background:var(--hover); color:var(--gold); }
        .gh, .toggle { display:inline-flex; padding:8px; color:var(--muted); border-radius:999px; transition:color .15s, background .15s; }
        .gh:hover, .toggle:hover { color:var(--fg); background:var(--hover); }
        .gh svg, .toggle svg { width:20px; height:20px; }
        .gh svg { fill:currentColor; }
        .toggle { border:0; background:none; cursor:pointer; }
        .toggle svg { fill:none; stroke:currentColor; stroke-width:2; stroke-linecap:round; }
        :host([data-mode="light"]) .sun, :host(:not([data-mode="light"])) .moon { display:none; }
        .actions { display:flex; align-items:center; gap:8px; }
        .trace { height:2px; background:linear-gradient(90deg, transparent, var(--gold) 20%, var(--gold) 80%, transparent); opacity:.55; }
        @media (max-width: 720px) { .wide { display:none; } .site { display:none; } }
      </style>
      <header>
        <div class="bar">
          <a class="brand" href="https://alphaonelabs.com" aria-label="Alpha One Labs home">${MARK}<span>Alpha One Labs</span></a>
          ${site ? `<a class="site" href="${siteHref}">${site}</a>` : ""}
          <nav aria-label="Alpha One Labs">
            ${links.map(([t, h]) => `<a class="wide" href="${h}">${t}</a>`).join("")}
            <details>
              <summary>Sites</summary>
              <div class="menu" role="menu">${SITES.map(([t, h]) => `<a role="menuitem" href="${h}">${t}</a>`).join("")}</div>
            </details>
            ${showToggle ? `<button class="toggle" type="button" aria-label="Toggle light and dark theme">
              <svg class="sun" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>
              <svg class="moon" viewBox="0 0 24 24" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>
            </button>` : ""}
            <a class="gh" href="${REPO}" aria-label="Alpha One Labs on GitHub"><svg viewBox="0 0 16 16"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg></a>
            <div class="actions"><slot name="actions"></slot></div>
          </nav>
        </div>
        <div class="trace"></div>
      </header>`;
      const toggle = root.querySelector(".toggle");
      if (toggle) toggle.addEventListener("click", () => window.A1Theme.toggle());
      // Close the sites menu when clicking elsewhere
      const details = root.querySelector("details");
      document.addEventListener("click", (e) => { if (!e.composedPath().includes(details)) details.open = false; });
    }
  }

  class A1Footer extends HTMLElement {
    connectedCallback() {
      if (this.shadowRoot) return;
      const source = this.getAttribute("source");
      const root = this.attachShadow({ mode: "open" });
      followTheme(this);
      const col = (title, items) => `<div><h3>${title}</h3><ul>${items.map(([t, h]) => `<li><a href="${h}">${t}</a></li>`).join("")}</ul></div>`;
      root.innerHTML = `<style>${THEME}
        footer { background:var(--bg); color:var(--fg); border-top:1px solid var(--line); }
        .wrap { max-width:1200px; margin:0 auto; padding:48px 20px 28px; }
        .top { display:grid; grid-template-columns:1.4fr repeat(3, 1fr); gap:32px; }
        .about { display:grid; gap:14px; align-content:start; }
        .about .brand { display:flex; align-items:center; gap:12px; font-family:"Space Grotesk",Inter,sans-serif; font-weight:700; font-size:18px; }
        .about .mark { width:36px; }
        .about p { margin:0; color:var(--muted); font-size:14px; line-height:1.6; max-width:34ch; }
        h3 { margin:0 0 12px; font:700 11px/1 "JetBrains Mono",ui-monospace,monospace; letter-spacing:.18em; text-transform:uppercase; color:var(--gold); }
        ul { list-style:none; margin:0; padding:0; display:grid; gap:9px; }
        li a { color:var(--muted); font-size:14px; transition:color .15s; }
        li a:hover { color:var(--fg); }
        .bottom { margin-top:40px; padding-top:20px; border-top:1px solid var(--line); display:flex; flex-wrap:wrap; gap:12px 24px; justify-content:space-between; color:var(--muted); font-size:13px; }
        .bottom a:hover { color:var(--gold); }
        @media (max-width: 760px) { .top { grid-template-columns:1fr 1fr; } .about { grid-column:1 / -1; } }
      </style>
      <footer>
        <div class="wrap">
          <div class="top">
            <div class="about">
              <a class="brand" href="https://alphaonelabs.com">${MARK}<span>Alpha One Labs</span></a>
              <p>Free, open-source tools that make science and technology hands-on. Built by a community of learners and makers.</p>
            </div>
            ${col("Sites", SITES.slice(0, 5))}
            ${col("More", SITES.slice(5).concat([["Design system", "https://design.alphaonelabs.com"]]))}
            ${col("Community", [["GitHub", REPO], ["Contribute", `${REPO}/blob/main/CONTRIBUTING.md`], ["Discussions", "https://github.com/orgs/alphaonelabs/discussions"], ["Good first issues", `${REPO}/issues?q=is%3Aopen+label%3A%22good+first+issue%22`], ["Code of conduct", `${REPO}/blob/main/CODE_OF_CONDUCT.md`]])}
          </div>
          <div class="bottom">
            <span>© ${new Date().getFullYear()} Alpha One Labs · Open-source education for everyone</span>
            ${source ? `<a href="${REPO}/tree/main/${source}">Edit this site on GitHub →</a>` : ""}
          </div>
        </div>
      </footer>`;
    }
  }

  if (!customElements.get("a1-header")) customElements.define("a1-header", A1Header);
  if (!customElements.get("a1-footer")) customElements.define("a1-footer", A1Footer);
})();

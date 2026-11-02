/*
 * Alpha One Labs shared site chrome v2 — https://design.alphaonelabs.com
 *
 *   <script src="https://design.alphaonelabs.com/chrome.js" defer></script>
 *   <a1-header site="QuantaLab" site-href="/" sticky></a1-header>
 *   ...your page...
 *   <a1-footer source="quantalab"></a1-footer>
 *
 * Both render inside Shadow DOM, so they never inherit or leak styles.
 * <a1-header> attributes:
 *   site             name shown after the wordmark (optional)
 *   site-href        where the site name links (default "/")
 *   theme            "light" | "dark" to pin the header (hides the toggle)
 *   sticky           stick to the top while scrolling
 *   no-theme-toggle  hide the theme toggle
 *   compact          hide the Sign in / Explore Activities buttons
 * Site-specific header controls go in slot="actions".
 * <a1-footer source="folder"> adds an "Edit this site on GitHub" link.
 *
 * Theme: follows the system unless the visitor picks one with the toggle. The
 * choice lives in an "a1-theme" cookie on .alphaonelabs.com, is mirrored to
 * data-a1-theme on <html>, and fires an "a1-themechange" event on document.
 */
(() => {
  const LEARN = "https://learn.alphaonelabs.com";
  const REPO = "https://github.com/alphaonelabs/website";
  const NAV = [
    ["Activities", `${LEARN}/activity`],
    ["Classroom", `${LEARN}/virtual-classroom`],
    ["Teach", `${LEARN}/teach`],
    ["Community", `${LEARN}/forum`],
    ["About", `${LEARN}/about`],
  ];
  const SITES = [
    ["Learn", LEARN, "Activities, classes and community"],
    ["Virtual World", "https://virtual.alphaonelabs.com", "Walk into classes in 3D"],
    ["QuantaLab", "https://quantalab.alphaonelabs.com", "Virtual science lab"],
    ["BotLab", "https://botlab.alphaonelabs.com", "Robotics playground"],
    ["VoxBridge", "https://voxbridge.alphaonelabs.com", "Accessibility tools"],
    ["EarthMind", "https://earthmind.alphaonelabs.com", "Environmental monitoring"],
    ["Mockuper", "https://mockuper.alphaonelabs.com", "Wireframe studio"],
    ["PMOSS", "https://pmoss.alphaonelabs.com", "Project management"],
    ["GSoC", "https://gsoc.alphaonelabs.com", "Google Summer of Code"],
    ["Design system", "https://design.alphaonelabs.com", "Brand, tokens and components"],
  ];

  const MARK = `<svg class="mark" viewBox="-6 -6 444 498" aria-hidden="true">
    <path d="M140.08 0L431.86 145.89L431.86 438.37L140.08 292.48Z" fill="#000" stroke="#fff" stroke-width="12"/>
    <path d="M317.72 163.61H377.27V342.25H347.5V193.38H317.72Z" fill="#fff"/>
    <path d="M0.14 56.42L285.96 199.34L285.96 485.16L0.14 342.25Z" fill="#fff" stroke="#000" stroke-width="12"/>
    <path fill="#000" fill-rule="evenodd" d="M124.41 164.3H161.54L219.47 342.25H185.04L171.54 300.49H114.66L101.19 342.25H66.76ZM143.06 212.45L122.66 274.56H163.14Z"/>
  </svg>`;
  const DIVIDER = `<svg class="pcb" viewBox="0 0 760 120" preserveAspectRatio="xMinYMid meet" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><rect x="340" y="20" width="84" height="80" stroke-width="3.5"/><circle cx="352" cy="32" r="3.2" fill="currentColor" stroke="none"/><rect x="326" y="31" width="14" height="6" fill="currentColor" stroke="none"/><rect x="424" y="31" width="14" height="6" fill="currentColor" stroke="none"/><path d="M0 18 L196 18 L212 34 L326 34"/><path d="M438 34 L456 34 L472 18 L690 18 L704 32"/><circle cx="708" cy="36" r="5.5" stroke-width="3"/><rect x="326" y="47" width="14" height="6" fill="currentColor" stroke="none"/><rect x="424" y="47" width="14" height="6" fill="currentColor" stroke="none"/><path d="M0 34 L202 34 L218 50 L326 50"/><path d="M438 50 L462 50 L478 34 L668 34 L682 48"/><circle cx="686" cy="52" r="5.5" stroke-width="3"/><rect x="326" y="63" width="14" height="6" fill="currentColor" stroke="none"/><rect x="424" y="63" width="14" height="6" fill="currentColor" stroke="none"/><path d="M0 50 L208 50 L224 66 L326 66"/><path d="M438 66 L468 66 L484 50 L646 50 L660 64"/><circle cx="664" cy="68" r="5.5" stroke-width="3"/><rect x="326" y="79" width="14" height="6" fill="currentColor" stroke="none"/><rect x="424" y="79" width="14" height="6" fill="currentColor" stroke="none"/><path d="M0 66 L214 66 L230 82 L326 82"/><path d="M438 82 L474 82 L490 66 L624 66 L638 80"/><circle cx="642" cy="84" r="5.5" stroke-width="3"/></svg>`;
  const GH = `<svg viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>`;
  const SUN = `<svg class="sun" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>`;
  const MOON = `<svg class="moon" viewBox="0 0 24 24" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>`;

  // ---- theme ------------------------------------------------------------
  const html = document.documentElement;
  const prefersDark = matchMedia("(prefers-color-scheme: dark)");
  const saved = () => (document.cookie.match(/(?:^|; )a1-theme=(light|dark)/) || [])[1] || null;
  const current = () => html.getAttribute("data-a1-theme") || (prefersDark.matches ? "dark" : "light");
  const listeners = new Set();
  const notify = () => {
    const theme = current();
    listeners.forEach((fn) => fn(theme));
    document.dispatchEvent(new CustomEvent("a1-themechange", { detail: { theme } }));
  };
  if (saved()) html.setAttribute("data-a1-theme", saved());
  prefersDark.addEventListener("change", () => { if (!saved()) notify(); });
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
  };

  const BASE = `
    @import url("https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@800;900&family=Inter:wght@500;600;700;800&display=swap");
    :host { --bg:#fff; --fg:#101010; --muted:#4a4a4a; --soft:#d8d8d8; --hard:#101010; --hover:#f5f5f5; --gold:#d4af37; --gold-hi:#f0c658; --on-gold:#080808;
            display:block; font-family:Inter,system-ui,-apple-system,"Segoe UI",Arial,sans-serif; }
    :host([data-mode="dark"]) { --bg:#000; --fg:#fafafa; --muted:#c6c6c6; --soft:#383838; --hard:#e1e1e1; --hover:#161616; --gold:#e1b746; --gold-hi:#f3cc61; }
    *, *::before, *::after { box-sizing:border-box; }
    a { color:inherit; text-decoration:none; }
    a:focus-visible, button:focus-visible, summary:focus-visible { outline:3px solid var(--gold); outline-offset:3px; }
    .mark { width:34px; height:auto; flex:none; display:block; }
    .wordmark { font:900 26px/1 "Barlow Condensed","Arial Narrow",Impact,sans-serif; letter-spacing:.01em; text-transform:uppercase; white-space:nowrap; }
    .btn { display:inline-flex; align-items:center; justify-content:center; gap:6px; min-height:38px; padding:0 14px; border:1px solid var(--hard); border-radius:2px; font:800 13px/1 Inter,sans-serif; white-space:nowrap; background:var(--bg); color:var(--fg); cursor:pointer; transition:background .15s; }
    .btn:hover { background:var(--hover); }
    .btn--gold { background:var(--gold); border-color:var(--gold); color:var(--on-gold); }
    .btn--gold:hover { background:var(--gold-hi); border-color:var(--gold-hi); }
    .icon { display:inline-grid; place-items:center; width:38px; height:38px; border:1px solid transparent; border-radius:2px; background:none; color:var(--fg); cursor:pointer; }
    .icon:hover { border-color:var(--soft); background:var(--hover); }
    .icon svg { width:19px; height:19px; fill:none; stroke:currentColor; stroke-width:2; stroke-linecap:round; }
  `;

  class A1Header extends HTMLElement {
    connectedCallback() {
      if (this.shadowRoot) return;
      const site = this.getAttribute("site");
      const siteHref = this.getAttribute("site-href") || "/";
      const showToggle = !this.hasAttribute("theme") && !this.hasAttribute("no-theme-toggle");
      const compact = this.hasAttribute("compact");
      const root = this.attachShadow({ mode: "open" });
      followTheme(this);
      if (this.hasAttribute("sticky")) Object.assign(this.style, { position: "sticky", top: "0", zIndex: "1000" });
      const sitesMenu = SITES.map(([t, h, d]) => `<a role="menuitem" href="${h}"><b>${t}</b><span>${d}</span></a>`).join("");
      root.innerHTML = `<style>${BASE}
        header { background:var(--bg); color:var(--fg); border-bottom:1px solid var(--soft); }
        .bar { max-width:1280px; margin:0 auto; min-height:76px; padding:0 clamp(16px,4vw,48px); display:flex; align-items:center; gap:18px; }
        .brand { display:flex; align-items:center; gap:12px; }
        .divider { width:1px; align-self:stretch; margin:20px 2px; background:var(--soft); }
        .site { font:800 13px/1 Inter,sans-serif; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); white-space:nowrap; }
        .site:hover { color:var(--fg); }
        nav.primary { display:flex; align-items:center; gap:22px; margin-left:8px; }
        nav.primary a { font:700 14px/1 Inter,sans-serif; padding:8px 0; border-bottom:2px solid transparent; }
        nav.primary a:hover { border-bottom-color:var(--gold); }
        .end { margin-left:auto; display:flex; align-items:center; gap:6px; }
        details { position:relative; }
        summary { list-style:none; }
        summary::-webkit-details-marker { display:none; }
        .sites-btn { display:inline-flex; align-items:center; gap:8px; width:auto; padding:0 10px; font:700 14px/1 Inter,sans-serif; }
        .sites-btn::after { content:""; width:6px; height:6px; border:solid currentColor; border-width:0 2px 2px 0; transform:rotate(45deg) translateY(-2px); }
        .menu { position:absolute; right:0; top:calc(100% + 10px); width:min(560px, 92vw); padding:8px; background:var(--bg); border:1px solid var(--hard); display:grid; grid-template-columns:1fr 1fr; gap:2px; z-index:10; }
        .menu a { display:grid; gap:2px; padding:10px 12px; border:1px solid transparent; }
        .menu a:hover { border-color:var(--soft); background:var(--hover); }
        .menu b { font:900 18px/1 "Barlow Condensed",sans-serif; text-transform:uppercase; }
        .menu span { font-size:12px; color:var(--muted); }
        .mobile { display:none; }
        .drawer { display:none; }
        :host([data-mode="light"]) .sun, :host([data-mode="dark"]) .moon { display:none; }
        @media (max-width: 1080px) { nav.primary { display:none; } .mobile { display:inline-grid; } }
        @media (max-width: 720px) { .site, .divider, .signin, .explore { display:none; } .wordmark { font-size:22px; } .sites { display:none; } }
        header.open .drawer { display:block; border-top:1px solid var(--soft); }
        .drawer nav { max-width:1280px; margin:0 auto; padding:12px clamp(16px,4vw,48px) 20px; display:grid; gap:2px; }
        .drawer a { padding:12px 0; border-bottom:1px solid var(--soft); font:900 24px/1 "Barlow Condensed",sans-serif; text-transform:uppercase; }
        .drawer .row { display:flex; gap:8px; padding-top:14px; }
      </style>
      <header>
        <div class="bar">
          <a class="brand" href="https://alphaonelabs.com" aria-label="Alpha One Labs home">${MARK}<span class="wordmark">Alpha One Labs</span></a>
          ${site ? `<span class="divider" aria-hidden="true"></span><a class="site" href="${siteHref}">${site}</a>` : ""}
          <nav class="primary" aria-label="Alpha One Labs">${NAV.map(([t, h]) => `<a href="${h}">${t}</a>`).join("")}</nav>
          <div class="end">
            <slot name="actions"></slot>
            <details class="sites"><summary class="icon sites-btn" aria-label="All Alpha One Labs sites">Sites</summary><div class="menu" role="menu">${sitesMenu}</div></details>
            ${showToggle ? `<button class="icon toggle" type="button" aria-label="Toggle light and dark theme">${SUN}${MOON}</button>` : ""}
            <a class="icon" href="${REPO}" aria-label="Alpha One Labs on GitHub">${GH}</a>
            ${compact ? "" : `<a class="btn signin" href="${LEARN}/login">Sign in</a><a class="btn btn--gold explore" href="${LEARN}/activity">Explore Activities ↗</a>`}
            <button class="icon mobile" type="button" aria-label="Open menu" aria-expanded="false"><svg viewBox="0 0 24 24"><path d="M4 7h16M4 12h16M4 17h16"/></svg></button>
          </div>
        </div>
        <div class="drawer"><nav aria-label="Alpha One Labs menu">
          ${NAV.map(([t, h]) => `<a href="${h}">${t}</a>`).join("")}
          ${SITES.map(([t, h]) => `<a href="${h}" style="font-size:18px">${t}</a>`).join("")}
          <div class="row"><a class="btn" href="${LEARN}/login" style="font:800 13px Inter;border:1px solid var(--hard);padding:0 14px">Sign in</a><a class="btn btn--gold" href="${LEARN}/activity" style="font:800 13px Inter;padding:0 14px">Explore Activities ↗</a></div>
        </nav></div>
      </header>`;
      const toggle = root.querySelector(".toggle");
      if (toggle) toggle.addEventListener("click", () => window.A1Theme.toggle());
      const header = root.querySelector("header");
      const burger = root.querySelector(".mobile");
      burger.addEventListener("click", () => {
        const open = header.classList.toggle("open");
        burger.setAttribute("aria-expanded", String(open));
        burger.setAttribute("aria-label", open ? "Close menu" : "Open menu");
      });
      const details = root.querySelector("details");
      document.addEventListener("click", (e) => { if (!e.composedPath().includes(details)) details.open = false; });
      document.addEventListener("keydown", (e) => { if (e.key === "Escape") { details.open = false; header.classList.remove("open"); } });
    }
  }

  class A1Footer extends HTMLElement {
    connectedCallback() {
      if (this.shadowRoot) return;
      const source = this.getAttribute("source");
      const root = this.attachShadow({ mode: "open" });
      followTheme(this);
      const col = (title, items) => `<div><h3>${title}</h3><ul>${items.map(([t, h]) => `<li><a href="${h}">${t}</a></li>`).join("")}</ul></div>`;
      root.innerHTML = `<style>${BASE}
        footer { background:var(--bg); color:var(--fg); border-top:1px solid var(--soft); }
        .wrap { max-width:1280px; margin:0 auto; padding:0 clamp(16px,4vw,48px); }
        .pcb { display:block; width:min(100%, 560px); height:auto; color:var(--gold); margin:36px 0 28px; }
        .top { display:grid; grid-template-columns:1.5fr repeat(3, 1fr); gap:32px; padding-bottom:36px; }
        .about { display:grid; gap:14px; align-content:start; }
        .brand { display:flex; align-items:center; gap:12px; }
        .tag { font:900 22px/1 "Barlow Condensed",sans-serif; text-transform:uppercase; letter-spacing:.02em; }
        .tag span { color:var(--gold); }
        .about p { margin:0; color:var(--muted); font-size:14px; line-height:1.6; max-width:36ch; }
        h3 { margin:0 0 14px; font:800 11px/1 Inter,sans-serif; letter-spacing:.12em; text-transform:uppercase; }
        ul { list-style:none; margin:0; padding:0; display:grid; gap:10px; }
        li a { color:var(--muted); font-size:14px; }
        li a:hover { color:var(--fg); text-decoration:underline; text-underline-offset:3px; }
        .bottom { border-top:1px solid var(--soft); padding:18px 0 40px; display:flex; flex-wrap:wrap; justify-content:space-between; gap:10px 24px; font-size:13px; color:var(--muted); }
        .bottom a:hover { color:var(--fg); }
        @media (max-width: 800px) { .top { grid-template-columns:1fr 1fr; } .about { grid-column:1 / -1; } }
      </style>
      <footer><div class="wrap">
        ${DIVIDER}
        <div class="top">
          <div class="about">
            <a class="brand" href="https://alphaonelabs.com" aria-label="Alpha One Labs home">${MARK}<span class="wordmark">Alpha One Labs</span></a>
            <div class="tag">Learn. Share. <span>Explore.</span></div>
            <p>A community-powered learning platform where curious people learn, teach and explore together, online and around the world.</p>
          </div>
          ${col("Learn", NAV.concat([["Study groups", `${LEARN}/study-groups`]]))}
          ${col("Sites", SITES.slice(1, 9).map(([t, h]) => [t, h]))}
          ${col("Community", [["GitHub", REPO], ["Contribute", `${REPO}/blob/main/CONTRIBUTING.md`], ["Discussions", "https://github.com/orgs/alphaonelabs/discussions"], ["Google Summer of Code", "https://gsoc.alphaonelabs.com"], ["Design system", "https://design.alphaonelabs.com"], ["Code of conduct", `${REPO}/blob/main/CODE_OF_CONDUCT.md`]])}
        </div>
        <div class="bottom">
          <span>© ${new Date().getFullYear()} Alpha One Labs · Open source, built by its community</span>
          <span>${source ? `<a href="${REPO}/tree/main/${source}">Edit this site on GitHub ↗</a>` : ""}</span>
        </div>
      </div></footer>`;
    }
  }

  if (!customElements.get("a1-header")) customElements.define("a1-header", A1Header);
  if (!customElements.get("a1-footer")) customElements.define("a1-footer", A1Footer);
})();

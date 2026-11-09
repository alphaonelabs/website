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
  const SOCIAL_ICONS = {
    twitter: `<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.936 9.936 0 0024 4.59z"/></svg>`,
    discord: `<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M20.317 4.37a19.791 19.791 0 00-4.885-1.515.074.074 0 00-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 00-5.487 0 12.64 12.64 0 00-.617-1.25.077.077 0 00-.079-.037A19.736 19.736 0 003.677 4.37a.07.07 0 00-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 00.031.057 19.9 19.9 0 005.993 3.03.078.078 0 00.084-.028c.462-.63.874-1.295 1.226-1.994.021-.041.001-.09-.041-.106a13.107 13.107 0 01-1.872-.892.077.077 0 01-.008-.128 10.2 10.2 0 00.372-.292.074.074 0 01.077-.01c3.929 1.793 8.18 1.793 12.061 0a.074.074 0 01.078.01c.12.098.246.198.373.292a.077.077 0 01-.006.127 12.299 12.299 0 01-1.873.894.077.077 0 00-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 00.084.028 19.839 19.839 0 006.002-3.03.077.077 0 00.032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 00-.031-.028zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/></svg>`,
    instagram: `<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg>`,
    linkedin: `<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/></svg>`,
    facebook: `<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>`,
    youtube: `<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>`,
    github: GH,
    slack: `<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z"/></svg>`,
  };
  const SOCIALS = [
    ["Twitter", "https://twitter.com/alphaonelabs", SOCIAL_ICONS.twitter],
    ["Discord", "https://discord.gg/HJtuzTJN3h", SOCIAL_ICONS.discord],
    ["Instagram", "https://instagram.com/alphaonelabs1", SOCIAL_ICONS.instagram],
    ["LinkedIn", "https://www.linkedin.com/company/alpha-one-labs", SOCIAL_ICONS.linkedin],
    ["Facebook", "https://facebook.com/alphaonelabs", SOCIAL_ICONS.facebook],
    ["YouTube", "https://youtube.com/alphaonelabs", SOCIAL_ICONS.youtube],
    ["GitHub", "https://github.com/AlphaOneLabs", SOCIAL_ICONS.github],
    ["Slack", "https://join.slack.com/t/alphaonelabs/shared_invite/zt-3glzypiib-8Lq~UZwWvcCFAjeG5uwcPg", SOCIAL_ICONS.slack],
  ];

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
        .top { display:grid; grid-template-columns:1.5fr repeat(4, 1fr); gap:32px; padding-bottom:36px; }
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
        .socials { display:grid; grid-template-columns:repeat(4, 38px); gap:10px 20px; width:fit-content; margin-top:16px; }
        .social-link { display:inline-flex; align-items:center; justify-content:center; width:38px; height:38px; border-radius:9999px; border:1px solid var(--soft); color:var(--muted); transition:all .15s ease; }
        .social-link:hover { border-color:var(--gold); color:var(--gold); transform:translateY(-1px); }
        .social-link svg { width:16px; height:16px; fill:currentColor; }
        @media (max-width: 800px) { .top { grid-template-columns:1fr 1fr; } .about { grid-column:1 / -1; } }
      </style>
      <footer><div class="wrap">
        ${DIVIDER}
        <div class="top">
          <div class="about">
            <a class="brand" href="https://alphaonelabs.com" aria-label="Alpha One Labs home">${MARK}<span class="wordmark">Alpha One Labs</span></a>
            <div class="tag">Learn. Share. <span>Explore.</span></div>
            <p>A community-powered learning platform where curious people learn, teach and explore together, online and around the world.</p>
            <div class="socials" aria-label="Social media links">${SOCIALS.map(([label, href, icon]) => `<a class="social-link" href="${href}" target="_blank" rel="noopener noreferrer" aria-label="${label}">${icon}</a>`).join("")}</div>
          </div>
          ${col("Learn", [["Browse Activities", `${LEARN}/activity`], ["Classroom", `${LEARN}/virtual-classroom`], ["Study Groups", `${LEARN}/study-groups`], ["Quizzes", `${LEARN}/quizzes`], ["Videos", `${LEARN}/activity?type=video`], ["Challenges", `${LEARN}/challenges`]])}
          ${col("Teach", [["Teach an Activity", `${LEARN}/teach`], ["Virtual Classroom", `${LEARN}/virtual-classroom`], ["Progress Trackers", `${LEARN}/progress`], ["Graphing Calculator", `${LEARN}/calculator`], ["Whiteboard", `${LEARN}/whiteboard`]])}
          ${col("Community", [["Forum", `${LEARN}/forum`], ["Blog", `${LEARN}/blog`], ["Discussions", "https://github.com/orgs/alphaonelabs/discussions"], ["Contribute", `${REPO}/blob/main/CONTRIBUTING.md`], ["GSoC", "https://gsoc.alphaonelabs.com"], ["Code of Conduct", `${REPO}/blob/main/CODE_OF_CONDUCT.md`]])}
          ${col("About", [["About Us", `${LEARN}/about`], ["Affiliations", `${LEARN}/affiliations`], ["Privacy Policy", `${LEARN}/privacy`], ["Terms", `${LEARN}/terms`], ["Status", `${LEARN}/status`], ["Feedback", `${LEARN}/feedback`]])}
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

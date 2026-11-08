/**
 * Minimal client-side i18n helper for the learn frontend.
 *
 * Markup:
 *   <span data-i18n="login.welcome">Welcome back!</span>
 *   <input data-i18n-placeholder="login.username_placeholder" placeholder="username">
 *   Supported attribute variants: data-i18n-placeholder, data-i18n-title,
 *   data-i18n-aria-label.
 *
 * Script:
 *   i18n.t("login.error_failed", "Login failed");
 *   i18n.t("greeting", "Hello {name}", { name: "GK" });
 *
 * The English text stays in the HTML as the default, so a page remains fully
 * usable if a catalog fails to load. Catalogs live in /locales/<lang>.json.
 * Lookup order: current language, then English, then the inline fallback.
 */
(function () {
  "use strict";

  // Guard against the script being included twice on the same page.
  if (window.i18n) return;

  const DEFAULT_LANG = "en";
  const SUPPORTED_LANGS = ["en", "es", "fr", "de", "zh"];
  const STORAGE_KEY = "lang";
  const TRANSLATABLE_ATTRIBUTES = ["placeholder", "title", "aria-label"];

  const catalogs = {};
  let currentLang = DEFAULT_LANG;
  let initPromise = null;

  /**
   * Pick the UI language: saved preference, then browser language, then English.
   * @returns {string} A language code from SUPPORTED_LANGS.
   */
  function detectLang() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (SUPPORTED_LANGS.includes(saved)) return saved;
    } catch (err) {
      // localStorage can be unavailable (private mode, blocked storage).
    }
    const browserLang = (navigator.language || DEFAULT_LANG)
      .slice(0, 2)
      .toLowerCase();
    return SUPPORTED_LANGS.includes(browserLang) ? browserLang : DEFAULT_LANG;
  }

  /**
   * Fetch and cache a catalog. Never throws: a failed load yields an empty
   * catalog so lookups fall back to English or the inline text.
   * @param {string} lang
   * @returns {Promise<Object>}
   */
  async function loadCatalog(lang) {
    if (catalogs[lang]) return catalogs[lang];
    try {
      const res = await fetch(`/locales/${lang}.json`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      catalogs[lang] =
        data && typeof data === "object" && !Array.isArray(data) ? data : {};
    } catch (err) {
      console.warn(`[i18n] Could not load "${lang}" catalog:`, err);
      catalogs[lang] = {};
    }
    return catalogs[lang];
  }

  /**
   * Find a string for `key` in the current language, then English.
   * @param {string} key
   * @returns {string|null} The string, or null if no catalog has it.
   */
  function lookup(key) {
    for (const lang of [currentLang, DEFAULT_LANG]) {
      const catalog = catalogs[lang];
      if (
        catalog &&
        Object.prototype.hasOwnProperty.call(catalog, key) &&
        typeof catalog[key] === "string"
      ) {
        return catalog[key];
      }
    }
    return null;
  }

  /**
   * Translate a key from script code.
   * @param {string} key
   * @param {string} [fallback] English text used if the key is missing or the
   *   catalog has not loaded yet. Defaults to the key itself.
   * @param {Object} [vars] Values for {name} style placeholders.
   * @returns {string}
   */
  function t(key, fallback, vars) {
    let text = lookup(key);
    if (text === null) text = fallback !== undefined ? String(fallback) : key;
    if (vars) {
      text = text.replace(/\{(\w+)\}/g, (match, name) =>
        Object.prototype.hasOwnProperty.call(vars, name)
          ? String(vars[name])
          : match
      );
    }
    return text;
  }

   /**
   * Translate every tagged element in `root`, including `root` itself.
   * Uses textContent and setAttribute only (never innerHTML), so catalog
   * content cannot inject markup. Elements whose key is missing keep their
   * existing text.
   * @param {Document|Element|DocumentFragment} [root=document]
   */
  function apply(root = document) {
    const findElements = (selector) => {
      const elements = [];
      if (root.matches && root.matches(selector)) {
        elements.push(root);
      }
      return elements.concat(Array.from(root.querySelectorAll(selector)));
    };

    findElements("[data-i18n]").forEach((el) => {
      const value = lookup(el.getAttribute("data-i18n"));
      if (value !== null) el.textContent = value;
    });

    TRANSLATABLE_ATTRIBUTES.forEach((attr) => {
      findElements(`[data-i18n-${attr}]`).forEach((el) => {
        const value = lookup(el.getAttribute(`data-i18n-${attr}`));
        if (value !== null) el.setAttribute(attr, value);
      });
    });

    document.documentElement.lang = currentLang;
  }
  

  /**
   * Load catalogs and translate the page. Safe to call more than once.
   * Dispatches a document-level "i18n:ready" event when done.
   * @returns {Promise<void>}
   */
  function init() {
    if (!initPromise) {
      initPromise = (async () => {
        currentLang = detectLang();
        await loadCatalog(DEFAULT_LANG);
        if (currentLang !== DEFAULT_LANG) await loadCatalog(currentLang);
        apply(document);
        document.dispatchEvent(
          new CustomEvent("i18n:ready", { detail: { lang: currentLang } })
        );
      })();
    }
    return initPromise;
  }

  window.i18n = Object.freeze({
    init,
    t,
    apply,
    get lang() {
      return currentLang;
    },
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const chromeSource = fs.readFileSync(path.join(__dirname, "..", "chrome.js"), "utf8");

function createHeader() {
  let activeElement = null;
  const documentListeners = {};
  const headerFocusTargets = new Set();
  const attributes = new Map();
  const burgerListeners = {};
  const header = {
    classList: {
      open: false,
      toggle(_name, force) {
        this.open = force;
      },
      contains() {
        return this.open;
      },
    },
    contains(element) {
      return headerFocusTargets.has(element);
    },
  };
  const burger = {
    focus() {
      activeElement = this;
    },
    setAttribute(name, value) {
      attributes.set(name, value);
    },
    addEventListener(name, listener) {
      burgerListeners[name] = listener;
    },
  };
  const drawerLink = {
    focus() {
      activeElement = this;
    },
  };
  const drawer = { querySelector: () => drawerLink };
  const details = {
    open: false,
    contains: () => false,
  };
  const summary = { focus() {} };
  headerFocusTargets.add(burger);
  headerFocusTargets.add(drawerLink);

  const root = {
    innerHTML: "",
    querySelector(selector) {
      return {
        ".toggle": null,
        header,
        ".mobile": burger,
        ".drawer": drawer,
        details,
        "details summary": summary,
      }[selector];
    },
    get activeElement() {
      return activeElement;
    },
  };
  const host = {
    shadowRoot: null,
    attachShadow() {
      this.shadowRoot = root;
      return root;
    },
    getAttribute: () => null,
    hasAttribute: () => false,
    setAttribute(name, value) {
      attributes.set(name, value);
    },
  };
  const html = {
    getAttribute: () => null,
    setAttribute() {},
  };
  const customElements = new Map();
  const context = {
    HTMLElement: class {},
    CustomEvent: class {},
    customElements: {
      get: (name) => customElements.get(name),
      define: (name, value) => customElements.set(name, value),
    },
    document: {
      documentElement: html,
      cookie: "",
      addEventListener(name, listener) {
        documentListeners[name] = listener;
      },
      dispatchEvent() {},
    },
    location: { hostname: "localhost" },
    matchMedia: () => ({ matches: false, addEventListener() {} }),
    window: {},
  };
  vm.runInNewContext(chromeSource, context, { filename: "chrome.js" });
  const instance = new (customElements.get("a1-header"))();
  Object.assign(instance, host);
  instance.connectedCallback();

  return {
    attributes,
    burger,
    burgerListeners,
    drawerLink,
    documentListeners,
    header,
    getActiveElement: () => activeElement,
    setActiveElement(element) {
      activeElement = element;
    },
  };
}

test("Escape closes the drawer and returns focus to the toggle from inside the header", () => {
  const { attributes, burger, burgerListeners, documentListeners, getActiveElement, header } = createHeader();
  burgerListeners.click();
  assert.equal(header.classList.open, true);

  let prevented = false;
  documentListeners.keydown({ key: "Escape", preventDefault: () => { prevented = true; } });

  assert.equal(header.classList.open, false);
  assert.equal(attributes.get("aria-expanded"), "false");
  assert.equal(attributes.get("aria-label"), "Open menu");
  assert.equal(getActiveElement(), burger);
  assert.equal(prevented, true);
});

test("Escape closes the drawer without moving focus or preventing default outside the header", () => {
  const { attributes, burgerListeners, documentListeners, getActiveElement, header, setActiveElement } = createHeader();
  const outsideControl = {};
  burgerListeners.click();
  setActiveElement(outsideControl);

  let prevented = false;
  documentListeners.keydown({ key: "Escape", preventDefault: () => { prevented = true; } });

  assert.equal(header.classList.open, false);
  assert.equal(attributes.get("aria-expanded"), "false");
  assert.equal(attributes.get("aria-label"), "Open menu");
  assert.equal(getActiveElement(), outsideControl);
  assert.equal(prevented, false);
});

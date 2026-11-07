import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";

const workerSource = fs.readFileSync(
  new URL("../public/service-worker.js", import.meta.url),
  "utf8",
);
const baseSource = fs.readFileSync(
  new URL("../public/base.html", import.meta.url),
  "utf8",
);

function createWorkerHarness() {
  const listeners = {};
  const stores = new Map();
  const fetchCalls = [];
  const deletedCaches = [];
  let networkAvailable = true;

  function makeResponse(body = "ok", status = 200, headers = {}) {
    return {
      ok: status >= 200 && status < 300,
      status,
      type: "basic",
      headers: { get: (name) => headers[name] || null },
      clone() {
        return makeResponse(body, status, headers);
      },
      body,
    };
  }

  function getStore(name) {
    if (!stores.has(name)) stores.set(name, new Map());
    return stores.get(name);
  }

  function cacheKey(request) {
    return new URL(
      typeof request === "string" ? request : request.url,
      "https://learn.example.test",
    ).href;
  }

  const context = {
    console: { warn() {} },
    URL,
    Response: { error: () => makeResponse("", 0) },
    Request,
    self: {
      location: { origin: "https://learn.example.test" },
      clients: { claim: async () => {} },
      addEventListener(type, handler) {
        listeners[type] = handler;
      },
    },
    caches: {
      open: async (name) => ({
        async match(request) {
          return getStore(name).get(cacheKey(request));
        },
        async put(request, response) {
          getStore(name).set(cacheKey(request), response);
        },
      }),
      keys: async () => [...stores.keys()],
      delete: async (name) => {
        deletedCaches.push(name);
        return stores.delete(name);
      },
    },
    fetch: async (request) => {
      const url = typeof request === "string" ? request : request.url;
      fetchCalls.push(url);
      if (!networkAvailable) throw new Error("offline");
      return makeResponse(url);
    },
    Promise,
    Set,
  };

  vm.runInNewContext(workerSource, context);

  return {
    listeners,
    stores,
    fetchCalls,
    deletedCaches,
    makeResponse,
    setNetworkAvailable(value) {
      networkAvailable = value;
    },
  };
}

function eventRequest(url, options = {}) {
  if (options.mode === "navigate") {
    return {
      url: `https://learn.example.test${url}`,
      method: options.method || "GET",
      mode: "navigate",
      headers: new Headers(options.headers),
    };
  }
  return new Request(`https://learn.example.test${url}`, {
    method: options.method || "GET",
    headers: options.headers,
  });
}

test("install caches the explicit shell assets", async () => {
  const harness = createWorkerHarness();
  let waited;

  harness.listeners.install({
    waitUntil(promise) {
      waited = promise;
    },
  });
  await waited;

  const shell = harness.stores.get("learn-app-shell-v1");
  assert.ok(shell.has("https://learn.example.test/offline.html"));
  assert.ok(shell.has("https://learn.example.test/css/a1-site.css?v=2"));
  assert.ok(shell.has("https://learn.example.test/images/logo.svg"));
});

test("the shared layout registers the Learn-scoped worker", () => {
  assert.match(baseSource, /navigator\.serviceWorker\.register\('\/service-worker\.js'/);
  assert.match(baseSource, /scope: '\/'/);
});

test("activation deletes old Learn shell caches", async () => {
  const harness = createWorkerHarness();
  harness.stores.set("learn-app-shell-old", new Map());
  harness.stores.set("other-cache", new Map());
  let waited;

  harness.listeners.activate({
    waitUntil(promise) {
      waited = promise;
    },
  });
  await waited;

  assert.deepEqual(harness.deletedCaches, ["learn-app-shell-old"]);
  assert.ok(harness.stores.has("other-cache"));
});

test("static assets use the shell cache before the network", async () => {
  const harness = createWorkerHarness();
  let waited;
  harness.listeners.install({ waitUntil: (promise) => (waited = promise) });
  await waited;
  const networkCallsAfterInstall = harness.fetchCalls.length;
  const request = eventRequest("/images/logo.svg");
  let response;

  harness.listeners.fetch({
    request,
    respondWith(promise) {
      response = promise;
    },
  });
  await response;

  assert.equal(harness.fetchCalls.length, networkCallsAfterInstall);
});

test("API and authenticated requests are not intercepted", () => {
  const harness = createWorkerHarness();
  const events = [
    { request: eventRequest("/api/activities") },
    { request: eventRequest("/images/logo.svg", { headers: { Authorization: "Bearer token" } }) },
  ];

  for (const event of events) {
    let intercepted = false;
    harness.listeners.fetch({
      ...event,
      respondWith() {
        intercepted = true;
      },
    });
    assert.equal(intercepted, false);
  }
});

test("offline public navigation returns the cached page", async () => {
  const harness = createWorkerHarness();
  const shell = new Map();
  shell.set("https://learn.example.test/offline.html", harness.makeResponse("offline"));
  shell.set("https://learn.example.test/about", harness.makeResponse("cached about"));
  harness.stores.set("learn-app-shell-v1", shell);
  harness.setNetworkAvailable(false);
  let response;
  harness.listeners.fetch({
    request: eventRequest("/about", { mode: "navigate" }),
    respondWith(promise) {
      response = promise;
    },
  });
  assert.equal((await response).body, "cached about");
});

test("uncached offline navigation returns the offline fallback", async () => {
  const harness = createWorkerHarness();
  const shell = new Map();
  shell.set("https://learn.example.test/offline.html", harness.makeResponse("offline"));
  harness.stores.set("learn-app-shell-v1", shell);
  harness.setNetworkAvailable(false);
  let response;

  harness.listeners.fetch({
    request: eventRequest("/about", { mode: "navigate" }),
    respondWith(promise) {
      response = promise;
    },
  });

  assert.equal((await response).body, "offline");
});

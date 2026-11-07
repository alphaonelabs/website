const CACHE_PREFIX = "learn-app-shell";
const CACHE_VERSION = "v1";
const SHELL_CACHE = `${CACHE_PREFIX}-${CACHE_VERSION}`;
const OFFLINE_URL = "/offline.html";

const CORE_ASSETS = [
  OFFLINE_URL,
  "/css/a1-site.css?v=2",
  "/js/a1-tailwind-theme.js?v=1",
  "/js/layout.js?v=2",
  "/images/logo.svg",
  "/images/logo.png",
];

const PUBLIC_NAVIGATION_PATHS = new Set([
  "/",
  "/about",
  "/activity",
  "/activity-detail",
  "/blog",
  "/classes-map",
  "/contributors",
  "/cookies",
  "/features",
  "/forum",
  "/gsoc",
  "/index.html",
  "/privacy",
  "/status",
  "/study-groups",
  "/success-stories",
  "/terms",
]);

const CORE_ASSET_URLS = new Set(
  CORE_ASSETS.map((asset) => new URL(asset, self.location.origin).href),
);

function isSameOrigin(request) {
  return new URL(request.url).origin === self.location.origin;
}

function isProtectedOrApiRequest(request, url) {
  return (
    url.pathname.startsWith("/api/") ||
    url.pathname === "/api" ||
    url.pathname.startsWith("/admin") ||
    url.pathname.startsWith("/media/") ||
    url.pathname.startsWith("/ref/") ||
    Boolean(request.headers.get("Authorization"))
  );
}

function isCacheableResponse(response) {
  if (!response || !response.ok || response.type !== "basic") return false;
  const cacheControl = response.headers.get("Cache-Control") || "";
  return !/\bno-store\b/i.test(cacheControl);
}

async function cacheFirst(request) {
  try {
    const cache = await caches.open(SHELL_CACHE);
    const cached = await cache.match(request);
    if (cached) return cached;

    const response = await fetch(request);
    if (isCacheableResponse(response)) {
      await cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    console.warn("Learn static asset request failed", error);
    return Response.error();
  }
}

async function networkFirstNavigation(request) {
  let cache;
  try {
    cache = await caches.open(SHELL_CACHE);
  } catch (error) {
    console.warn("Learn navigation cache unavailable", error);
    return Response.error();
  }

  try {
    const response = await fetch(request);
    if (isCacheableResponse(response)) {
      await cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    const cached = await cache.match(request);
    if (cached) return cached;
    return cache.match(OFFLINE_URL);
  }
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then(async (cache) => {
      const results = await Promise.allSettled(
        CORE_ASSETS.map(async (asset) => {
          try {
            const response = await fetch(asset, { cache: "no-cache" });
            if (!isCacheableResponse(response)) {
              throw new Error(`Non-cacheable response for ${asset}`);
            }
            await cache.put(asset, response);
          } catch (error) {
            console.warn(`Learn shell asset was not cached: ${asset}`, error);
          }
        }),
      );
      return results;
    }).catch((error) => {
      console.warn("Learn shell cache installation failed", error);
    }),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((cacheNames) =>
        Promise.all(
          cacheNames
            .filter(
              (cacheName) =>
                cacheName.startsWith(`${CACHE_PREFIX}-`) &&
                cacheName !== SHELL_CACHE,
            )
            .map((cacheName) => caches.delete(cacheName)),
        ),
      )
      .then(() => self.clients.claim())
      .catch((error) => {
        console.warn("Learn shell cache activation failed", error);
      }),
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET" || !isSameOrigin(request)) return;

  const url = new URL(request.url);
  if (isProtectedOrApiRequest(request, url)) return;

  if (CORE_ASSET_URLS.has(url.href)) {
    event.respondWith(cacheFirst(request));
    return;
  }

  if (
    request.mode === "navigate" &&
    PUBLIC_NAVIGATION_PATHS.has(url.pathname.replace(/\/+$/, "") || "/")
  ) {
    event.respondWith(networkFirstNavigation(request));
  }
});

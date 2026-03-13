/**
 * GraceFinance Service Worker v1.0
 *
 * Strategy:
 *   - App shell (HTML, CSS, JS, fonts): Cache-first, update in background
 *   - API calls: Network-first, never cached (financial data must be fresh)
 *   - Images/icons: Cache-first with network fallback
 *   - Offline: Serves cached app shell so the UI loads even without internet
 */

var CACHE_NAME = "gracefinance-v1"

var PRECACHE_URLS = [
  "/",
  "/dashboard",
  "/manifest.json",
  "/icons/icon-192x192.png",
  "/icons/icon-512x512.png",
]

/* ── Install: precache app shell ── */
self.addEventListener("install", function (event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function (cache) {
      return cache.addAll(PRECACHE_URLS)
    }).then(function () {
      return self.skipWaiting()
    })
  )
})

/* ── Activate: clean old caches ── */
self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys().then(function (cacheNames) {
      return Promise.all(
        cacheNames.filter(function (name) {
          return name !== CACHE_NAME
        }).map(function (name) {
          return caches.delete(name)
        })
      )
    }).then(function () {
      return self.clients.claim()
    })
  )
})

/* ── Fetch: route by request type ── */
self.addEventListener("fetch", function (event) {
  var url = new URL(event.request.url)

  /* Skip non-GET requests */
  if (event.request.method !== "GET") return

  /* API calls: network only, never cache financial data */
  if (url.pathname.startsWith("/api/") ||
      url.pathname.startsWith("/checkin/") ||
      url.pathname.startsWith("/index/") ||
      url.pathname.startsWith("/grace/") ||
      url.pathname.startsWith("/bsi/") ||
      url.pathname.startsWith("/feed/") ||
      url.pathname.startsWith("/dashboard/") ||
      url.hostname === "gracefinance-production.up.railway.app") {
    return
  }

  /* Everything else: cache-first with network fallback */
  event.respondWith(
    caches.match(event.request).then(function (cached) {
      if (cached) {
        /* Serve from cache, update in background */
        var fetchPromise = fetch(event.request).then(function (response) {
          if (response && response.status === 200 && response.type === "basic") {
            var responseClone = response.clone()
            caches.open(CACHE_NAME).then(function (cache) {
              cache.put(event.request, responseClone)
            })
          }
          return response
        }).catch(function () { /* offline, cached version already served */ })
        return cached
      }

      /* Not in cache: fetch from network and cache it */
      return fetch(event.request).then(function (response) {
        if (!response || response.status !== 200 || response.type !== "basic") {
          return response
        }
        var responseClone = response.clone()
        caches.open(CACHE_NAME).then(function (cache) {
          cache.put(event.request, responseClone)
        })
        return response
      }).catch(function () {
        /* Offline and not cached: return the cached index for SPA routing */
        if (event.request.headers.get("accept") &&
            event.request.headers.get("accept").includes("text/html")) {
          return caches.match("/")
        }
      })
    })
  )
})
/* Aspect Coffee service worker. Static files only — never cart, orders or account. */
var STATIC_CACHE = "aspect-static-v1";
var PRECACHE = [
  "/offline/",
  "/static/asset/images/logo-aspect.svg",
  "/static/asset/images/favicon-aspect.svg",
  "/static/pwa/icon-192.png",
  "/static/pwa/icon-512.png"
];

self.addEventListener("install", function (event) {
  event.waitUntil(
    caches.open(STATIC_CACHE).then(function (cache) {
      return cache.addAll(PRECACHE);
    }).then(function () {
      return self.skipWaiting();
    })
  );
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (key) {
        return key !== STATIC_CACHE;
      }).map(function (key) {
        return caches.delete(key);
      }));
    }).then(function () {
      return self.clients.claim();
    })
  );
});

function isDynamic(url) {
  var path = url.pathname;
  var prefixes = [
    "/basket",
    "/account",
    "/admin",
    "/api",
    "/order",
    "/login",
    "/logout",
    "/register",
    "/users"
  ];
  return prefixes.some(function (prefix) {
    return path === prefix || path.indexOf(prefix + "/") === 0;
  });
}

function isStaticAsset(url) {
  if (url.origin === self.location.origin && url.pathname.indexOf("/static/") === 0) return true;
  return url.hostname === "fonts.googleapis.com" || url.hostname === "fonts.gstatic.com";
}

self.addEventListener("fetch", function (event) {
  var request = event.request;
  if (request.method !== "GET") return;

  var url = new URL(request.url);

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(function () {
        return caches.match("/offline/");
      })
    );
    return;
  }

  if (isDynamic(url)) return;

  if (!isStaticAsset(url)) return;

  event.respondWith(
    caches.match(request).then(function (cached) {
      var network = fetch(request).then(function (response) {
        if (response && response.ok) {
          var copy = response.clone();
          caches.open(STATIC_CACHE).then(function (cache) {
            cache.put(request, copy);
          });
        }
        return response;
      }).catch(function () {
        return cached;
      });
      return cached || network;
    })
  );
});

self.addEventListener("push", function (event) {
  var payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch (error) {
    payload = { body: event.data ? event.data.text() : "" };
  }
  var title = payload.title || "Aspect Coffee";
  var options = {
    body: payload.body || "",
    icon: "/static/pwa/icon-192.png",
    badge: "/static/pwa/icon-192.png",
    tag: payload.tag || "aspect-notification",
    renotify: true,
    data: {
      url: payload.url || "/account/notifications/",
      notificationId: payload.notification_id || null
    }
  };
  event.waitUntil(
    Promise.all([
      self.registration.showNotification(title, options),
      clients.matchAll({ type: "window", includeUncontrolled: true }).then(function (windows) {
        windows.forEach(function (client) {
          client.postMessage({
            type: "aspect-new-notification",
            notificationId: payload.notification_id || null
          });
        });
      })
    ])
  );
});

self.addEventListener("notificationclick", function (event) {
  event.notification.close();
  var targetUrl = new URL(
    (event.notification.data && event.notification.data.url) || "/account/notifications/",
    self.location.origin
  ).href;
  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then(function (windows) {
      for (var i = 0; i < windows.length; i++) {
        if (windows[i].url === targetUrl && "focus" in windows[i]) return windows[i].focus();
      }
      return clients.openWindow ? clients.openWindow(targetUrl) : undefined;
    })
  );
});

self.addEventListener("push", (event) => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch (error) {
    payload = { body: event.data ? event.data.text() : "" };
  }

  const title = payload.title || "Aspect Coffee";
  const options = {
    body: payload.body || "",
    icon: "/static/asset/images/favicon-aspect.svg",
    badge: "/static/asset/images/favicon-aspect.svg",
    tag: payload.tag || "aspect-notification",
    renotify: true,
    data: {
      url: payload.url || "/account/notifications/",
      notificationId: payload.notification_id || null,
    },
  };
  event.waitUntil(
    Promise.all([
      self.registration.showNotification(title, options),
      clients.matchAll({ type: "window", includeUncontrolled: true }).then((windows) => {
        windows.forEach((client) => client.postMessage({
          type: "aspect-new-notification",
          notificationId: payload.notification_id || null,
        }));
      }),
    ])
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl = new URL(
    event.notification.data?.url || "/account/notifications/",
    self.location.origin
  ).href;

  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((windows) => {
      for (const client of windows) {
        if (client.url === targetUrl && "focus" in client) return client.focus();
      }
      return clients.openWindow ? clients.openWindow(targetUrl) : undefined;
    })
  );
});

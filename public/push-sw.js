/* RAN1 Live! push messaging worker. Messaging only — no offline caching. */

self.addEventListener("push", (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch {
    data = { title: "RAN1 Live!", body: event.data ? event.data.text() : "" };
  }
  const title = data.title || "Colleague needed";
  const options = {
    body: data.body || "",
    icon: "/icon-192.png",
    badge: "/icon-64.png",
    tag: data.tag || "ran1live-alert",
    renotify: true,
    data: { url: data.url || "/" },
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || "/";
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
      for (const client of clients) {
        if ("focus" in client) {
          client.navigate(url);
          return client.focus();
        }
      }
      return self.clients.openWindow(url);
    }),
  );
});

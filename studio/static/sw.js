/* FrameFactory SW — keeps episode downloads going when you leave the tab (Chrome/Android). */
self.addEventListener("install", (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("backgroundfetchsuccess", (event) => {
  event.waitUntil(
    (async () => {
      try {
        const records = await event.registration.matchAll();
        const cache = await caches.open("ff-downloads");
        for (const record of records) {
          const res = await record.responseReady;
          if (res && res.ok) {
            await cache.put(record.request, res.clone());
          }
        }
      } catch (_) {
        /* ignore */
      }
      if (self.registration.showNotification) {
        try {
          await self.registration.showNotification("FrameFactory", {
            body: "El video terminó de descargarse.",
            icon: "/assets/logo.png",
          });
        } catch (_) {
          /* permission optional */
        }
      }
    })()
  );
});

self.addEventListener("backgroundfetchfail", (event) => {
  event.waitUntil(
    (async () => {
      if (self.registration.showNotification) {
        try {
          await self.registration.showNotification("FrameFactory", {
            body: "Falló la descarga en segundo plano. Reintentá desde Video.",
            icon: "/assets/logo.png",
          });
        } catch (_) {
          /* ignore */
        }
      }
    })()
  );
});

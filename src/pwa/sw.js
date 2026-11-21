// Minimal service worker: makes the dashboards installable. It caches nothing,
// since the pages are live views of the sheet driven over a websocket and
// stale copies would be misleading, so every request goes to the network.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));
self.addEventListener("fetch", () => {});

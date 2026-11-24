/* Dossard Péi : notifications (et seulement ça : pas de cache hors ligne, le site reste servi normalement). */
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));

self.addEventListener("push", e => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch (er) { d = { body: e.data ? e.data.text() : "" }; }
  const opt = {
    body: d.body || "",
    icon: "/icon-192.png",
    badge: "/icon-192.png",
    tag: d.tag || undefined,
    renotify: !!d.tag,
    data: { url: d.url || "/", ins: d.ins || "" },
    lang: "fr",
  };
  if (d.image) opt.image = d.image;   // affiche en grand (Android)
  if (d.ins) opt.actions = [{ action: "ins", title: "S'inscrire" }, { action: "voir", title: "Voir la course" }];
  e.waitUntil(self.registration.showNotification(d.title || "Dossard Péi", opt));
});

self.addEventListener("notificationclick", e => {
  e.notification.close();
  const d = e.notification.data || {};
  const url = e.action === "ins" && d.ins ? d.ins : new URL(d.url || "/", self.location.origin).href;
  e.waitUntil((async () => {
    if (e.action !== "ins") {
      const wins = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
      for (const w of wins) if (new URL(w.url).origin === self.location.origin && "focus" in w) {
        try { await w.navigate(url); } catch (er) { }
        return w.focus();
      }
    }
    return self.clients.openWindow(url);
  })());
});

// abonnement renouvelé par le navigateur : on prévient le service (les favoris seront renvoyés à la prochaine ouverture du site)
self.addEventListener("pushsubscriptionchange", e => {
  e.waitUntil((async () => {
    try {
      const k = await (await fetch("/api/push/key")).json();
      const s = await self.registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: k.key });
      await fetch("/api/push/sub", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ subscription: s.toJSON(), old: e.oldSubscription ? e.oldSubscription.endpoint : "" }) });
    } catch (er) { }
  })());
});

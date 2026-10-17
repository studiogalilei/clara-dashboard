// Il pezzo del service worker che riceve le notifiche (7/9/2026, rivisto il 17/10).
// Lo importa il service worker generato da vite-plugin-pwa (workbox.importScripts).
// Il cloud (scripts/avvisa.py) manda {titolo, testo, url, tag}: qui si mostra, e al tocco si apre
// l'indirizzo (la scheda del lead nella versione snella, o Oggi).
// Il tag: due notifiche sullo stesso lead si sostituiscono, due lead diversi restano tutti e due
// (prima il tag era uno solo per tutte, e la seconda cancellava la prima).
self.addEventListener('push', (evento) => {
  let dati = { titolo: 'Clara', testo: '', url: './' }
  try { dati = { ...dati, ...evento.data.json() } } catch { dati.testo = evento.data ? evento.data.text() : '' }
  evento.waitUntil(self.registration.showNotification(dati.titolo, {
    body: dati.testo,
    icon: new URL('icon-192.png', self.registration.scope).href,
    badge: new URL('icon-192.png', self.registration.scope).href,
    data: { url: dati.url },
    tag: dati.tag || dati.url || 'clara',
    renotify: true,
  }))
})

self.addEventListener('notificationclick', (evento) => {
  evento.notification.close()
  const url = new URL((evento.notification.data && evento.notification.data.url) || './', self.registration.scope).href
  evento.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(async (finestre) => {
    const aperta = finestre.find((f) => f.url.startsWith(self.registration.scope))
    if (aperta) {
      // la pagina aperta si sposta da sola (ascoltaNotifiche in src/lib/notifiche.ts): un cambio
      // d'indirizzo nella stessa app, senza ricaricare
      aperta.postMessage({ apri: url })
      try { await aperta.focus() } catch { /* su alcuni telefoni il focus non si da' */ }
      return
    }
    return self.clients.openWindow(url)
  }))
})

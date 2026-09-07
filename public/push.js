// Il pezzo del service worker che riceve le notifiche (7/9/2026).
// Lo importa il service worker generato da vite-plugin-pwa (workbox.importScripts).
// Il cloud manda {titolo, testo, url}; qui si mostra e al tocco si apre la Dashboard.
self.addEventListener('push', (evento) => {
  let dati = { titolo: 'Clara', testo: '', url: './' }
  try { dati = { ...dati, ...evento.data.json() } } catch { dati.testo = evento.data ? evento.data.text() : '' }
  evento.waitUntil(self.registration.showNotification(dati.titolo, {
    body: dati.testo, icon: './icon-192.png', badge: './icon-192.png', data: { url: dati.url }, tag: 'clara',
  }))
})

self.addEventListener('notificationclick', (evento) => {
  evento.notification.close()
  const url = new URL((evento.notification.data && evento.notification.data.url) || './', self.location.href).href
  evento.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((finestre) => {
    const aperta = finestre.find((f) => f.url.startsWith(self.registration.scope))
    if (aperta) return aperta.focus().then((f) => (f.navigate ? f.navigate(url) : f))
    return self.clients.openWindow(url)
  }))
})

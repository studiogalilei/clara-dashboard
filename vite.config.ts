import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

// GitHub Pages serve la dashboard sotto /clara/ (BASE_PATH), in locale sotto /
export default defineConfig({
  base: process.env.BASE_PATH || '/',
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      // la copia di prova nel laboratorio (gold, 6/10) non installa un secondo service worker
      disable: Boolean(process.env.SENZA_PWA),
      registerType: 'autoUpdate',
      // le notifiche le riceve public/push.js, importato dentro il service worker
      // 21/10 sera (Dre: «la cosa delle due alternative non c'e' in app sul telefono»): il service worker nuovo
      // prende il posto del vecchio appena scaricato (skipWaiting, clientsClaim); l'app ricarica da sola quando
      // e' ferma, se no mostra «Nuova versione: tocca per aggiornare» (src/Aggiorna.tsx), cosi' sul telefono non resta la versione vecchia fino al giorno dopo.
      workbox: { skipWaiting: true, clientsClaim: true, importScripts: ['push.js'], globIgnores: ['**/brand/**', '**/lab/**', '**/documento-*.js', '**/CompilaPdf-*.js', '**/pdf.worker*'], navigateFallbackDenylist: [/\/lab\//] },   // i pezzi pesanti si scaricano quando servono, non all'installazione
      // LA WEB APP SUL TELEFONO (17/10): l'icona sulla Home apre la versione snella su Oggi
      // (chi non e' ceo viene portato da li' al Workspace completo, src/snella/Snella.tsx).
      // Bianca come la snella: la barra in alto e lo schermo d'apertura non lampeggiano di blu.
      manifest: {
        id: './',
        start_url: './#/s/oggi',
        scope: './',
        name: 'SG Oggi · Studio Galilei',
        short_name: 'SG Oggi',
        description: 'Il Workspace di Studio Galilei: chi chiamare, le call, i lead, le campagne',
        lang: 'it',
        theme_color: '#ffffff',
        background_color: '#ffffff',
        display: 'standalone',
        orientation: 'any',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
          { src: 'apple-touch-icon.png', sizes: '180x180', type: 'image/png', purpose: 'any' },
        ],
      },
    }),
  ],
})

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
      // 21/10 sera (Dre: «la cosa delle due alternative non c'e' in app sul telefono»): il service worker nuovo
      // prende il posto del vecchio appena scaricato (skipWaiting, clientsClaim); l'app ricarica da sola quando
      // e' ferma, se no mostra «Nuova versione: tocca per aggiornare» (src/Aggiorna.tsx), cosi' sul telefono non resta la versione vecchia fino al giorno dopo.
      workbox: { skipWaiting: true, clientsClaim: true, globIgnores: ['**/brand/**', '**/lab/**'] },
      // LA WEB APP SUL TELEFONO: l'icona sulla Home apre il LinkedIn Desk sui post (27/11).
      manifest: {
        id: './',
        start_url: './#/d/post',
        scope: './',
        name: 'LinkedIn Desk, Studio Galilei',
        short_name: 'LinkedIn Desk',
        description: 'I post LinkedIn e le persone del giorno del team di Studio Galilei',
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

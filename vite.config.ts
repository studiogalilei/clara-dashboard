import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

// Vercel serve la dashboard su workspace.studiogalilei.com alla radice, come in locale; GitHub Pages (riserva) sotto /clara/ con BASE_PATH
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
      workbox: { importScripts: ['push.js'], globIgnores: ['**/brand/**', '**/lab/**', '**/documento-*.js', '**/CompilaPdf-*.js', '**/pdf.worker*'], navigateFallbackDenylist: [/\/lab\//] },   // i pezzi pesanti si scaricano quando servono, non all'installazione
      manifest: {
        start_url: './',
        scope: './',
        name: 'SG Workspace',
        short_name: 'SG Workspace',
        description: 'Il workspace di Studio Galilei, con Clara',
        theme_color: '#061773',
        background_color: '#061773',
        display: 'standalone',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png' },
        ],
      },
    }),
  ],
})

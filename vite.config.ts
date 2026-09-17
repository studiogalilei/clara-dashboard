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
      registerType: 'autoUpdate',
      // le notifiche le riceve public/push.js, importato dentro il service worker
      workbox: { importScripts: ['push.js'], globIgnores: ['**/brand/**', '**/documento-*.js', '**/CompilaPdf-*.js', '**/pdf.worker*'] },   // i pezzi pesanti si scaricano quando servono, non all'installazione
      manifest: {
        start_url: './',
        scope: './',
        name: 'SG Workspace',
        short_name: 'SG Workspace',
        description: 'Il workspace di Studio Galilei, con Clara',
        theme_color: '#111827',
        background_color: '#ffffff',
        display: 'standalone',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png' },
        ],
      },
    }),
  ],
})

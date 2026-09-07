import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      // le notifiche le riceve public/push.js, importato dentro il service worker
      workbox: { importScripts: ['push.js'] },
      manifest: {
        name: 'Clara — Studio Galilei',
        short_name: 'Clara',
        description: 'La dashboard di Studio Galilei, con Clara',
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

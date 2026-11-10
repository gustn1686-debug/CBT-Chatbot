/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'
import { manifest } from './pwa.manifest.ts'

const DAY = 60 * 60 * 24

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      // 새 버전이 나와도 쓰고 있는 화면을 강제로 새로고침하지 않는다. (대화·위기 안내 중에 끊기면 안 된다)
      // 새 서비스 워커는 대기했다가 앱을 다시 열 때 적용된다.
      registerType: 'prompt',
      includeAssets: ['favicon-32.png', 'favicon-64.png', 'icons/apple-touch-icon.png'],
      manifest,
      workbox: {
        // 마스코트 이미지(webp)와 아이콘까지 미리 받아 두어야 오프라인에서도 화면이 그대로 나온다.
        globPatterns: ['**/*.{js,css,html,svg,png,webp,ico,woff2}'],
        cleanupOutdatedCaches: true,
        navigateFallback: 'index.html',
        navigateFallbackDenylist: [/^\/api\//],
        runtimeCaching: [
          {
            // 글꼴 CSS (Noto Sans KR). 한 번 받으면 오프라인에서도 쓴다.
            urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/i,
            handler: 'StaleWhileRevalidate',
            options: { cacheName: 'google-fonts-styles' },
          },
          {
            urlPattern: /^https:\/\/fonts\.gstatic\.com\/.*/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'google-fonts-files',
              expiration: { maxEntries: 30, maxAgeSeconds: 365 * DAY },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
        ],
      },
    }),
  ],
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    globals: true,
  },
})

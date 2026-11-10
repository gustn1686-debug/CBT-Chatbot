import type { ManifestOptions } from 'vite-plugin-pwa'

// 홈 화면에 설치할 때 쓰이는 앱 정보. 아이콘은 public/icons 에 있다.
// 임시 아이콘: 마스코트(main)를 앱 대표색 위에 올린 것이며, 디자이너의 최종 앱 아이콘이 나오면 교체한다.
export const manifest: Partial<ManifestOptions> = {
  id: '/',
  name: 'Synap',
  short_name: 'Synap',
  description: 'CBT 원리 기반 대화형 자기 정리 도구',
  lang: 'ko',
  dir: 'ltr',
  start_url: '/',
  scope: '/',
  display: 'standalone',
  orientation: 'portrait',
  theme_color: '#5170b8',
  background_color: '#ffffff',
  categories: ['health', 'lifestyle'],
  icons: [
    { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
    { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
    // maskable: 기기가 원형·둥근 사각형으로 잘라도 마스코트가 잘리지 않는 여백 포함 버전
    { src: '/icons/icon-maskable-192.png', sizes: '192x192', type: 'image/png', purpose: 'maskable' },
    { src: '/icons/icon-maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
  ],
  shortcuts: [
    {
      name: '대화 시작하기',
      short_name: '대화',
      url: '/chat',
      icons: [{ src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' }],
    },
  ],
}

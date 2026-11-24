// 상담 시간 알림(웹 푸시)을 받아 보여주고, 누르면 앱을 연다.
// 배포 빌드에서는 PWA 서비스 워커가 이 파일을 불러오고(vite.config.ts workbox.importScripts),
// 개발 서버(npm run dev)에서는 이 파일을 서비스 워커로 직접 등록한다(src/lib/push.ts).
// 이 파일에서 skipWaiting 을 부르지 않는다. 배포 워커는 새 버전을 앱을 다시 열 때 적용한다 (vite.config.ts registerType).

self.addEventListener('push', (event) => {
  let data = {}
  try {
    data = event.data ? event.data.json() : {}
  } catch {
    data = { body: event.data ? event.data.text() : '' }
  }
  const title = data.title || 'Synap'
  event.waitUntil(
    self.registration.showNotification(title, {
      body: data.body || '',
      icon: '/icons/icon-192.png',
      badge: '/favicon-64.png',
      tag: data.tag || 'synap',
      data: { url: data.url || '/' },
    }),
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const target = new URL(event.notification.data?.url || '/', self.location.origin).href
  event.waitUntil(
    (async () => {
      const windows = await self.clients.matchAll({ type: 'window', includeUncontrolled: true })
      const open = windows.find((w) => new URL(w.url).origin === self.location.origin)
      if (open) {
        await open.focus()
        if ('navigate' in open) await open.navigate(target).catch(() => {})
        return
      }
      await self.clients.openWindow(target)
    })(),
  )
})


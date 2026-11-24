// 상담 시간 알림(웹 푸시) 켜기·끄기. 서버 API: docs/api-spec.md §7
//
// - 배포 빌드: PWA 서비스 워커가 public/push-sw.js 를 불러와 알림을 처리한다.
// - 개발 서버(npm run dev): PWA 워커가 없으므로 push-sw.js 를 직접 서비스 워커로 등록한다.
// - 아이폰·아이패드는 Safari 에서 "홈 화면에 추가"로 설치한 앱에서만 알림을 받을 수 있다 (iOS 16.4+).
import { request, useMock } from '../api/client'

export type PushState =
  | 'on' // 이 기기에서 알림을 받고 있다
  | 'off' // 켤 수 있다
  | 'denied' // 브라우저에서 알림을 막았다 (브라우저 설정에서 풀어야 한다)
  | 'ios-install' // 아이폰: 홈 화면에 추가해야 받을 수 있다
  | 'unsupported' // 이 브라우저는 웹 푸시를 지원하지 않는다
  | 'server-off' // 서버에 알림 키가 없다 (또는 목업 모드)

const isIos = () =>
  /iPhone|iPad|iPod/.test(navigator.userAgent) ||
  (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
const isStandalone = () =>
  window.matchMedia?.('(display-mode: standalone)').matches ||
  (navigator as Navigator & { standalone?: boolean }).standalone === true

const supported = () =>
  typeof window !== 'undefined' &&
  'serviceWorker' in navigator &&
  'PushManager' in window &&
  'Notification' in window

async function registration(): Promise<ServiceWorkerRegistration> {
  const existing = await navigator.serviceWorker.getRegistration()
  if (!existing && import.meta.env.DEV) await navigator.serviceWorker.register('/push-sw.js')
  return navigator.serviceWorker.ready
}

let publicKeyCache: string | null | undefined
async function publicKey(): Promise<string | null> {
  if (useMock) return null
  if (publicKeyCache !== undefined) return publicKeyCache
  const res = await request('/push/public-key', {}, false)
  const key: string | null = (await res.json()).public_key ?? null
  publicKeyCache = key
  return key
}

function keyBytes(base64url: string): Uint8Array<ArrayBuffer> {
  const pad = '='.repeat((4 - (base64url.length % 4)) % 4)
  const raw = atob((base64url + pad).replace(/-/g, '+').replace(/_/g, '/'))
  const bytes = new Uint8Array(new ArrayBuffer(raw.length))
  for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i)
  return bytes
}

export async function getPushState(): Promise<PushState> {
  if (!supported()) return isIos() && !isStandalone() ? 'ios-install' : 'unsupported'
  if (Notification.permission === 'denied') return 'denied'
  try {
    if (!(await publicKey())) return 'server-off'
  } catch {
    return 'server-off'
  }
  const existing = await navigator.serviceWorker.getRegistration()
  const sub = await existing?.pushManager.getSubscription()
  return sub && Notification.permission === 'granted' ? 'on' : 'off'
}

// 버튼을 누른 직후에 불러야 한다 (브라우저가 사용자 동작 없이 띄운 권한 요청을 막는다).
export async function enablePush(): Promise<PushState> {
  if (!supported()) return isIos() && !isStandalone() ? 'ios-install' : 'unsupported'
  const permission = await Notification.requestPermission()
  if (permission !== 'granted') return permission === 'denied' ? 'denied' : 'off'
  const key = await publicKey().catch(() => null)
  if (!key) return 'server-off'

  const reg = await registration()
  const sub =
    (await reg.pushManager.getSubscription()) ??
    (await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes(key) }))
  const json = sub.toJSON()
  await request('/push/subscriptions', {
    method: 'POST',
    body: JSON.stringify({ endpoint: json.endpoint, keys: json.keys }),
  })
  return 'on'
}

export async function disablePush(): Promise<PushState> {
  if (!supported()) return 'unsupported'
  const reg = await navigator.serviceWorker.getRegistration()
  const sub = await reg?.pushManager.getSubscription()
  if (sub) {
    await request('/push/subscriptions', { method: 'DELETE', body: JSON.stringify({ endpoint: sub.endpoint }) }).catch(
      () => {},
    )
    await sub.unsubscribe()
  }
  return 'off'
}

export async function sendTestPush(): Promise<number> {
  const res = await request('/push/test', { method: 'POST' })
  return (await res.json()).sent
}

export const pushStateMessage: Record<PushState, string> = {
  on: '상담 시간에 알림을 보내 드려요',
  off: '알림을 켜면 상담 시간에 알려 드려요',
  denied: '브라우저에서 알림이 차단돼 있어요. 브라우저 설정에서 허용해 주세요',
  'ios-install': '아이폰은 Safari 공유 버튼 → "홈 화면에 추가"로 설치한 앱에서 알림을 받을 수 있어요',
  unsupported: '이 브라우저에서는 알림을 받을 수 없어요',
  'server-off': '서버에 알림 설정이 아직 없어요',
}

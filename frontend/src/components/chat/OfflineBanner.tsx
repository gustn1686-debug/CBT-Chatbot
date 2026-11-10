// Figma: EX_4_네트워크오류 — 화면 맨 위의 연결 안내
export function OfflineBanner() {
  return (
    <div role="alert" className="flex items-center gap-2 bg-offline-bg px-4 py-2.5">
      <span aria-hidden className="text-[13px]/[normal]">
        📶
      </span>
      <p className="text-[12px]/[normal] font-bold text-offline-ink">인터넷 연결을 확인해주세요</p>
    </div>
  )
}

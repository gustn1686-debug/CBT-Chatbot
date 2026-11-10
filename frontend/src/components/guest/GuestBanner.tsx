import { Link } from 'react-router-dom'

type GuestBannerProps = { used: number; limit: number }

// Figma: GuestBanner — 홈 상단의 비회원 체험 안내(무료 대화 사용량 + 가입하기)
export function GuestBanner({ used, limit }: GuestBannerProps) {
  const shown = Math.min(used, limit)
  return (
    <section
      aria-label="비회원 체험 안내"
      className="flex items-center gap-3 rounded-button bg-guest-bg py-3.5 pr-3.5 pl-4"
    >
      <div className="flex flex-1 flex-col gap-1.5">
        <p className="text-[13px]/[normal] font-bold text-bubble-user-ink">비회원으로 체험 중이에요</p>
        <div className="flex items-center gap-2">
          <div className="flex gap-1" aria-hidden>
            {Array.from({ length: limit }, (_, i) => (
              <span
                key={i}
                className={`h-[5px] w-[18px] rounded-[3px] ${i < shown ? 'bg-primary' : 'bg-guest-dot-off'}`}
              />
            ))}
          </div>
          <p className="text-[11px]/[normal] text-muted">
            {shown >= limit ? `무료 대화 ${limit}회 모두 사용` : `무료 대화 ${limit}회 중 ${shown}회 사용`}
          </p>
        </div>
      </div>
      <Link
        to="/signup"
        className="rounded-[20px] bg-white px-3 py-2 text-[12px]/[normal] font-bold text-primary"
      >
        가입하기
      </Link>
    </section>
  )
}

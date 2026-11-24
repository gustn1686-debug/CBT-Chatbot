import { Link } from 'react-router-dom'
import { Mascot } from '../Mascot'

// 상담 계획은 회원만 쓸 수 있다. 비회원이 들어오면 가입을 안내한다.
export function MemberOnly() {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="px-4 pt-5 pb-2.5">
        <Link to="/" className="text-[13px]/[normal] text-muted">
          ‹ 대화
        </Link>
      </header>
      <main className="flex flex-1 flex-col items-center justify-center gap-5 px-6 pb-16 text-center">
        <Mascot variant="thinking" width={84} height={100} />
        <div className="flex flex-col gap-2">
          <h1 className="text-[19px]/[normal] font-bold">상담 계획은 가입 후에 쓸 수 있어요</h1>
          <p className="text-[12.5px]/[1.6] text-muted">
            정해 둔 시간에 알림을 받고, 회기마다 나눈 이야기를
            <br />
            요약으로 모아 볼 수 있어요.
          </p>
        </div>
        <Link to="/signup" className="w-full rounded-button bg-primary py-4 text-[15px]/[normal] font-bold text-white">
          가입하기
        </Link>
      </main>
    </div>
  )
}

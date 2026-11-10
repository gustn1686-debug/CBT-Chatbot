import { Link } from 'react-router-dom'
import { version } from '../../package.json'
import { useDocumentTitle } from '../hooks/useDocumentTitle'

// 임시 화면: 피그마에 "앱 정보" 화면이 아직 없다. 디자인이 나오면 교체한다.
export function About() {
  useDocumentTitle('앱 정보')
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="px-4 pt-5 pb-2.5">
        <Link to="/settings" className="text-[13px]/[normal] text-muted">
          ‹ 설정
        </Link>
      </header>

      <main className="flex flex-col gap-3.5 px-5 pt-1 pb-4">
        <h1 className="text-[19px]/[normal] font-bold">앱 정보</h1>

        <dl className="overflow-hidden rounded-xl bg-white shadow-card">
          <div className="flex items-center justify-between px-4 py-3.5 text-[13px]/[16px]">
            <dt>앱 이름</dt>
            <dd className="text-[12px]/[16px] text-muted">Synap</dd>
          </div>
          <div className="h-px bg-line" />
          <div className="flex items-center justify-between px-4 py-3.5 text-[13px]/[16px]">
            <dt>버전</dt>
            <dd className="text-[12px]/[16px] text-muted">{version}</dd>
          </div>
        </dl>

        <p className="px-1 text-[11.5px]/[normal] text-muted">
          이 서비스는 전문적인 심리 치료나 상담을 대체하지 않아요.
        </p>
      </main>
    </div>
  )
}

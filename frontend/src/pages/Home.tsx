import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getUsage, type Usage } from '../api/auth'
import { listRecords, type ThoughtRecord } from '../api/records'
import { GuestBanner } from '../components/guest/GuestBanner'
import { GuestSignupSheet } from '../components/guest/GuestSignupSheet'
import { Mascot } from '../components/Mascot'
import { TabBar } from '../components/TabBar'
import { formatDate } from '../lib/format'
import { getSession } from '../lib/session'
import { useDocumentTitle } from '../hooks/useDocumentTitle'

const RECENT_COUNT = 2

// Figma: HiFi_2_홈 / EX_7_홈_빈상태 / GUEST_1_홈_비회원체험 / GUEST_2_가입유도_대화시작시
export function Home() {
  useDocumentTitle('홈')
  const navigate = useNavigate()
  const isGuest = getSession()?.kind === 'guest'
  const [records, setRecords] = useState<ThoughtRecord[] | null>(null)
  const [usage, setUsage] = useState<Usage | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)

  useEffect(() => {
    listRecords().then((all) => setRecords(all.slice(0, RECENT_COUNT)))
  }, [])

  useEffect(() => {
    if (isGuest) getUsage().then(setUsage)
  }, [isGuest])

  const isFirstVisit = records !== null && records.length === 0
  const limitReached = isGuest && usage?.signupRequired === true

  return (
    <div className="flex min-h-dvh flex-col">
      <main className="flex flex-1 flex-col gap-[18px] px-5 pt-10 pb-4">
        <header className="flex items-center gap-2">
          <div className="flex flex-1 flex-col gap-1">
            <h1 className="text-[18px]/[normal] font-bold">오늘은 어떤 하루였나요</h1>
            <p className="text-[11.5px]/[normal] text-muted">
              {isFirstVisit ? '처음이시네요. 편하게 이야기해보세요' : '마음이 복잡할 때, 잠시 정리해볼까요'}
            </p>
          </div>
          {!isFirstVisit && <Mascot variant="waving" width={56} height={68} />}
        </header>

        {isGuest && usage && <GuestBanner used={usage.sessionCount} limit={usage.limit} />}

        <Link
          to="/chat"
          onClick={(e) => {
            if (!limitReached) return
            e.preventDefault() // 무료 대화를 다 쓴 비회원에게는 먼저 가입을 안내한다
            setSheetOpen(true)
          }}
          className="flex flex-col items-center justify-center gap-2 rounded-hero bg-primary py-8 text-white shadow-card"
        >
          <span className="text-[26px]/[normal]" aria-hidden>
            💬
          </span>
          <span className="text-[16px]/[normal] font-bold">대화 시작하기</span>
        </Link>

        {isFirstVisit && (
          <div className="flex flex-col items-center gap-2.5 py-9">
            <Mascot variant="waving" width={84} height={100} />
            <p className="text-[13.5px]/[normal] font-bold">아직 기록이 없어요</p>
            <p className="text-center text-[11.5px]/[normal] text-muted">첫 대화를 나누면 이곳에 정리한 기록이 쌓여요</p>
          </div>
        )}

        {records !== null && records.length > 0 && (
          <>
            <h2 className="text-[13px]/[normal] font-bold text-muted">최근 기록</h2>
            <ul className="flex flex-col gap-[18px]">
              {records.map((record) => (
                <li key={record.id}>
                  <Link
                    to={`/records/${record.id}`}
                    className="flex items-center gap-2 rounded-card bg-white px-3.5 py-3 shadow-card"
                  >
                    <span className="flex flex-1 flex-col gap-0.5">
                      <span className="text-[12.5px]/[15px]">{record.title}</span>
                      <span className="text-[10.5px]/[13px] text-muted">{formatDate(record.date)}</span>
                    </span>
                    <span className="text-[15px]/[normal] text-muted" aria-hidden>
                      ›
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </>
        )}
      </main>
      <TabBar />

      {sheetOpen && usage && (
        <GuestSignupSheet
          limit={usage.limit}
          onJoin={() => navigate('/signup')}
          onLater={() => navigate('/chat')}
        />
      )}
    </div>
  )
}

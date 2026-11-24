import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { getSession as getPlanSession, retrySessionSummary, type SessionResult } from '../api/plans'
import { MemberOnly } from '../components/plan/MemberOnly'
import { SessionStamps } from '../components/plan/SessionStamps'
import { SummaryCard } from '../components/plan/SummaryCard'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { SUMMARY_POLL_MS } from '../hooks/usePlan'
import { formatMonthDay, formatMonthDayTime } from '../lib/format'
import { getSession } from '../lib/session'

// 한 회기를 마친 화면(/plan/session/:id). "상담 마치기" 직후에는 도장이 찍히는 움직임을 보여준다.
export function SessionDone() {
  useDocumentTitle('회기 요약')
  if (getSession()?.kind !== 'user') return <MemberOnly />
  return <SessionDoneScreen />
}

function SessionDoneScreen() {
  const { id = '' } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const justCompleted = (location.state as { justCompleted?: boolean } | null)?.justCompleted === true
  const [result, setResult] = useState<SessionResult | null>(null)

  const load = useCallback(
    () =>
      getPlanSession(id)
        .then(setResult)
        .catch(() => navigate('/plan', { replace: true })),
    [id, navigate],
  )

  useEffect(() => {
    void load()
  }, [load])

  const pending =
    result?.session.summaryStatus === 'pending' ||
    (result?.plan.status === 'completed' && result.plan.summaryStatus === 'pending')
  useEffect(() => {
    if (!pending) return
    const timer = setTimeout(load, SUMMARY_POLL_MS)
    return () => clearTimeout(timer)
  }, [pending, result, load])

  if (!result) return <div aria-busy className="min-h-dvh" />
  const { session, plan } = result
  const isLast = plan.status === 'completed' && session.number === plan.totalSessions

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="px-4 pt-5 pb-2.5">
        <Link to="/plan" className="text-[13px]/[normal] text-muted">
          ‹ 상담 계획
        </Link>
      </header>

      <main className="flex flex-1 flex-col gap-3.5 px-5 pt-1 pb-8">
        <section aria-label="회기 완료" className="flex flex-col items-center gap-3.5 py-3 text-center">
          <p className="text-[12px]/[normal] font-bold text-primary">
            {session.number}회기 · {formatMonthDay(session.completedAt)}
          </p>
          <h1 className="text-[20px]/[normal] font-bold">
            {justCompleted ? (isLast ? '마지막 회기까지 마쳤어요!' : '오늘 상담을 마쳤어요') : `${session.number}회기 요약`}
          </h1>
          <SessionStamps
            total={plan.totalSessions}
            completed={plan.completedSessions}
            justStamped={justCompleted ? session.number : undefined}
          />
        </section>

        <SummaryCard
          heading="오늘 나눈 이야기"
          meta={`${session.number} / ${plan.totalSessions}회기`}
          status={session.summaryStatus ?? 'pending'}
          summary={session.summary}
          onRetry={async () => setResult(await retrySessionSummary(id))}
        />

        {isLast ? (
          <Link
            to="/plan"
            className="flex items-center justify-between rounded-xl bg-guest-bg px-4 py-3.5 text-[13px]/[normal] font-bold text-primary-ink"
          >
            <span>
              {plan.summaryStatus === 'done' ? '전체 회기 요약이 준비됐어요' : '전체 회기 요약을 정리하고 있어요'}
            </span>
            <span aria-hidden>›</span>
          </Link>
        ) : (
          plan.status === 'active' &&
          plan.nextReminderAt && (
            <p className="px-1 text-center text-[12px]/[1.6] text-muted">
              다음 상담은 {formatMonthDayTime(plan.nextReminderAt, plan.timezone)}에 알려 드릴게요
            </p>
          )
        )}

        <div className="mt-auto flex flex-col gap-2 pt-4">
          <Link to="/" className="w-full rounded-button bg-primary py-4 text-center text-[15px]/[normal] font-bold text-white">
            확인
          </Link>
          <Link to={`/chat/${session.conversationId}`} className="py-2.5 text-center text-[12.5px]/[normal] text-muted">
            대화 다시 보기
          </Link>
        </div>
      </main>
    </div>
  )
}

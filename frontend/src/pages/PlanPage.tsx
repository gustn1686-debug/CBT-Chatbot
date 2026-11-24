import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { cancelPlan, retryPlanSummary, type Plan, type PlanSession } from '../api/plans'
import { ConfirmModal } from '../components/ConfirmModal'
import { Mascot } from '../components/Mascot'
import { MemberOnly } from '../components/plan/MemberOnly'
import { SessionStamps } from '../components/plan/SessionStamps'
import { SummaryCard } from '../components/plan/SummaryCard'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { useCurrentPlan } from '../hooks/usePlan'
import { formatMonthDay, formatMonthDayTime } from '../lib/format'
import { disablePush, enablePush, getPushState, sendTestPush, type PushState } from '../lib/push'
import { getSession } from '../lib/session'
import { daysLabel, formatTime, pushHint } from '../lib/plan'

const card = 'rounded-hero bg-white p-5 shadow-card'

// 상담 계획(/plan): 진행 상황(도장), 다음 상담 시각, 알림, 마친 회기 목록, 다 마치면 전체 요약.
export function PlanPage() {
  useDocumentTitle('상담 계획')
  if (getSession()?.kind !== 'user') return <MemberOnly />
  return <PlanScreen />
}

type SavedState = { saved?: 'new' | 'edit'; push?: PushState | null } | null

function PlanScreen() {
  const navigate = useNavigate()
  const location = useLocation()
  const saved = location.state as SavedState
  const { plan, setPlan, loaded } = useCurrentPlan()
  const [confirmCancel, setConfirmCancel] = useState(false)

  const retry = async () => {
    if (plan) setPlan(await retryPlanSummary(plan.id))
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="px-4 pt-5 pb-2.5">
        <Link to="/" className="text-[13px]/[normal] text-muted">
          ‹ 대화
        </Link>
      </header>

      <main aria-busy={!loaded} className="flex flex-1 flex-col gap-3.5 px-5 pt-1 pb-8">
        <h1 className="text-[19px]/[normal] font-bold">상담 계획</h1>
        {saved?.saved && (
          <p role="status" className="rounded-xl bg-guest-bg px-4 py-3 text-[12.5px]/[1.6] text-primary-ink">
            {saved.saved === 'new' ? '상담 계획을 시작했어요.' : '일정을 바꿨어요.'}
            {saved.push && saved.push !== 'on' && pushHint(saved.push) && ` ${pushHint(saved.push)}`}
          </p>
        )}

        {!loaded ? null : !plan ? (
          <EmptyPlan />
        ) : plan.status === 'completed' ? (
          <CompletedPlan plan={plan} onRetry={retry} />
        ) : (
          <ActivePlan plan={plan} onCancel={() => setConfirmCancel(true)} />
        )}
      </main>

      {confirmCancel && plan && (
        <ConfirmModal
          title="상담 계획을 그만둘까요?"
          description={'알림이 더 이상 오지 않아요.\n마친 회기의 대화와 요약은 그대로 남아요.'}
          confirmLabel="그만두기"
          tone="danger"
          onCancel={() => setConfirmCancel(false)}
          onConfirm={async () => {
            setConfirmCancel(false)
            await cancelPlan(plan.id)
            setPlan(null)
            navigate('/plan', { replace: true, state: null })
          }}
        />
      )}
    </div>
  )
}

function EmptyPlan() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-5 pb-10 text-center">
      <Mascot variant="main" width={96} height={112} />
      <div className="flex flex-col gap-2">
        <h2 className="text-[17px]/[normal] font-bold">상담 일정을 정해 볼까요?</h2>
        <p className="text-[12.5px]/[1.7] text-muted">
          원하는 요일과 시간에 알림을 보내 드려요.
          <br />
          회기를 마칠 때마다 도장이 찍히고, 나눈 이야기를 요약해 드려요.
        </p>
      </div>
      <Link to="/plan/new" className="w-full rounded-button bg-primary py-4 text-[15px]/[normal] font-bold text-white">
        상담 계획 세우기
      </Link>
    </div>
  )
}

function ActivePlan({ plan, onCancel }: { plan: Plan; onCancel: () => void }) {
  const next = plan.completedSessions + 1
  return (
    <>
      <section aria-label="진행 상황" className={`${card} flex flex-col items-center gap-4 text-center`}>
        <div className="flex flex-col gap-1">
          <p className="text-[12px]/[normal] font-bold text-primary">
            {daysLabel(plan.weekdays)} {formatTime(plan.time)}
          </p>
          <p className="text-[22px]/[normal] font-bold">
            {plan.completedSessions}
            <span className="text-[15px] text-muted"> / {plan.totalSessions}회기</span>
          </p>
        </div>
        <SessionStamps total={plan.totalSessions} completed={plan.completedSessions} size="lg" />
        {plan.nextReminderAt && (
          <p className="text-[12px]/[normal] text-muted">
            다음 알림 · {formatMonthDayTime(plan.nextReminderAt, plan.timezone)}
          </p>
        )}
        <Link to="/" className="w-full rounded-button bg-primary py-3.5 text-[14px]/[normal] font-bold text-white">
          {next}회기 상담 시작하기
        </Link>
      </section>

      <PushCard />

      <SessionList sessions={plan.sessions} />

      <div className="mt-2 flex justify-center gap-4 text-[12.5px]/[normal]">
        <Link to="/plan/edit" className="px-2 py-2 text-primary-ink">
          일정 바꾸기
        </Link>
        <span aria-hidden className="py-2 text-line">
          |
        </span>
        <button type="button" onClick={onCancel} className="px-2 py-2 text-muted">
          계획 그만두기
        </button>
      </div>
    </>
  )
}

function CompletedPlan({ plan, onRetry }: { plan: Plan; onRetry: () => void }) {
  return (
    <>
      <section aria-label="계획 완료" className={`${card} flex flex-col items-center gap-3.5 text-center`}>
        <Mascot variant="playing" width={84} height={96} />
        <div className="flex flex-col gap-1">
          <h2 className="text-[18px]/[normal] font-bold">{plan.totalSessions}번의 상담을 모두 마쳤어요</h2>
          {plan.completedAt && (
            <p className="text-[12px]/[normal] text-muted">{formatMonthDay(plan.completedAt)} 완료</p>
          )}
        </div>
        <SessionStamps total={plan.totalSessions} completed={plan.completedSessions} />
      </section>

      <SummaryCard
        heading="전체 회기 요약"
        meta={`${plan.totalSessions}회기`}
        status={plan.summaryStatus ?? 'pending'}
        summary={plan.summary}
        onRetry={onRetry}
        pendingText="모든 회기를 돌아보며 정리하고 있어요"
      />

      <SessionList sessions={plan.sessions} />

      <Link
        to="/plan/new"
        className="mt-2 w-full rounded-button bg-primary py-4 text-center text-[15px]/[normal] font-bold text-white"
      >
        새 상담 계획 세우기
      </Link>
    </>
  )
}

function SessionList({ sessions }: { sessions: PlanSession[] }) {
  if (sessions.length === 0) return null
  return (
    <nav aria-label="마친 회기" className="flex flex-col gap-2">
      <h2 className="px-1 pt-1.5 text-[13px]/[normal] font-bold text-muted">마친 회기</h2>
      <ul className="overflow-hidden rounded-xl bg-white shadow-card">
        {sessions.map((s, i) => (
          <li key={s.conversationId}>
            {i > 0 && <div className="mx-4 h-px bg-line" />}
            <Link to={`/plan/session/${s.conversationId}`} className="flex items-center gap-3 px-4 py-3.5">
              <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-tag-bg text-[12px] font-bold text-primary-ink">
                {s.number}
              </span>
              <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                <span className="truncate text-[13px]/[16px]">{s.title ?? `${s.number}회기 상담`}</span>
                <span className="text-[10.5px]/[13px] text-muted">
                  {formatMonthDay(s.completedAt)}
                  {s.summaryStatus === 'pending' && ' · 요약 정리 중'}
                  {s.summaryStatus === 'failed' && ' · 요약 실패'}
                </span>
              </span>
              <span aria-hidden className="text-[15px]/[16px] text-muted">
                ›
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  )
}

// 이 기기의 알림 상태와 켜기·테스트
function PushCard() {
  const [state, setState] = useState<PushState | null>(null)
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState('')

  useEffect(() => {
    getPushState().then(setState)
  }, [])

  if (state === null) return null

  const turnOn = async () => {
    setBusy(true)
    setNote('')
    const next = await enablePush().catch(() => 'off' as const)
    setState(next)
    if (next !== 'on') setNote(pushHint(next) || '알림을 켜지 못했어요.')
    setBusy(false)
  }

  const turnOff = async () => {
    setBusy(true)
    setState(await disablePush().catch(() => state))
    setBusy(false)
  }

  const test = async () => {
    setBusy(true)
    try {
      const sent = await sendTestPush()
      setNote(sent > 0 ? '테스트 알림을 보냈어요.' : '알림을 받을 기기가 없어요. 알림을 다시 켜 주세요.')
    } catch {
      setNote('테스트 알림을 보내지 못했어요.')
    }
    setBusy(false)
  }

  return (
    <section aria-label="알림" className="flex flex-col gap-2 rounded-xl bg-white px-4 py-3.5 shadow-card">
      <div className="flex items-center justify-between gap-3">
        <div className="flex flex-col gap-0.5">
          <h2 className="text-[13px]/[16px] font-bold">상담 시간 알림</h2>
          <p className="text-[11.5px]/[1.5] text-muted">
            {state === 'on' ? '이 기기로 알림을 보내 드려요' : state === 'off' ? '꺼져 있어요' : pushHint(state)}
          </p>
        </div>
        {state === 'off' && (
          <button
            type="button"
            disabled={busy}
            onClick={turnOn}
            className="shrink-0 rounded-full bg-primary px-4 py-2 text-[12.5px]/[normal] font-bold text-white"
          >
            알림 켜기
          </button>
        )}
      </div>
      {state === 'on' && (
        <div className="flex gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={test}
            className="rounded-full bg-tag-bg px-3.5 py-2 text-[12px]/[normal] font-bold text-primary-ink"
          >
            테스트 알림 보내기
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={turnOff}
            className="rounded-full bg-surface-muted px-3.5 py-2 text-[12px]/[normal] text-muted"
          >
            알림 끄기
          </button>
        </div>
      )}
      <p role="status" className="text-[11.5px]/[1.5] text-primary-ink empty:hidden">
        {note}
      </p>
    </section>
  )
}

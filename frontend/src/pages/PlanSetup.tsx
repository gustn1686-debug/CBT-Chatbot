import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { createPlan, deviceTimezone, getCurrentPlan, updateSchedule, type Plan } from '../api/plans'
import { Toggle } from '../components/Toggle'
import { MemberOnly } from '../components/plan/MemberOnly'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { ALL_DAYS, DAYS, daysLabel, DEFAULT_SESSIONS, formatTime, pushHint, SESSION_OPTIONS } from '../lib/plan'
import { enablePush, getPushState, type PushState } from '../lib/push'
import { getSession } from '../lib/session'

const chip = (on: boolean) =>
  `rounded-full px-4 py-2.5 text-[13px]/[normal] font-bold transition-colors ${
    on ? 'bg-primary text-white' : 'bg-surface-muted text-ink'
  }`

// 상담 계획 세우기(/plan/new) · 일정 바꾸기(/plan/edit)
export function PlanSetup({ mode }: { mode: 'new' | 'edit' }) {
  useDocumentTitle(mode === 'new' ? '상담 계획 세우기' : '상담 일정 바꾸기')
  if (getSession()?.kind !== 'user') return <MemberOnly />
  return <PlanForm mode={mode} />
}

function PlanForm({ mode }: { mode: 'new' | 'edit' }) {
  const navigate = useNavigate()
  const [existing, setExisting] = useState<Plan | null>(null)
  const [total, setTotal] = useState<number>(DEFAULT_SESSIONS)
  const [weekdays, setWeekdays] = useState<number[]>(ALL_DAYS)
  const [time, setTime] = useState('22:00')
  const [notify, setNotify] = useState(true)
  const [pushState, setPushState] = useState<PushState | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    getPushState().then(setPushState)
  }, [])

  useEffect(() => {
    if (mode !== 'edit') return
    getCurrentPlan().then((plan) => {
      if (!plan || plan.status !== 'active') {
        navigate('/plan', { replace: true })
        return
      }
      setExisting(plan)
      setWeekdays(plan.weekdays)
      setTime(plan.time)
    })
  }, [mode, navigate])

  const toggleDay = (day: number) =>
    setWeekdays((list) => (list.includes(day) ? list.filter((d) => d !== day) : [...list, day].sort()))

  const canAskPush = pushState === 'off'
  const valid = weekdays.length > 0 && /^\d{2}:\d{2}$/.test(time)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!valid || submitting) return
    setSubmitting(true)
    setError('')
    // 알림 권한은 버튼을 누른 직후에 물어야 브라우저가 막지 않는다. 실패해도 계획은 만든다.
    let push = pushState
    if (notify && canAskPush) push = await enablePush().catch(() => pushState)
    try {
      const schedule = { weekdays, time, timezone: deviceTimezone() }
      if (mode === 'edit' && existing) await updateSchedule(existing.id, schedule)
      else await createPlan({ ...schedule, totalSessions: total })
      navigate('/plan', { replace: true, state: { saved: mode, push } })
    } catch (err) {
      if (err instanceof ApiError && err.code === 'plan_exists') {
        navigate('/plan', { replace: true })
        return
      }
      setError(err instanceof ApiError ? err.message : '저장하지 못했어요. 잠시 후 다시 시도해 주세요.')
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="px-4 pt-5 pb-2.5">
        <Link to={mode === 'edit' ? '/plan' : '/'} className="text-[13px]/[normal] text-muted">
          ‹ {mode === 'edit' ? '상담 계획' : '대화'}
        </Link>
      </header>

      <form onSubmit={submit} className="flex flex-1 flex-col gap-6 px-5 pt-1 pb-8">
        <div className="flex flex-col gap-1.5">
          <h1 className="text-[19px]/[normal] font-bold">
            {mode === 'new' ? '상담 계획 세우기' : '상담 일정 바꾸기'}
          </h1>
          <p className="text-[12.5px]/[1.6] text-muted">
            {mode === 'new'
              ? '정해 둔 시간에 알려 드릴게요. 한 번의 대화를 마칠 때마다 한 회기가 채워져요.'
              : '바꾼 일정은 다음 알림부터 적용돼요.'}
          </p>
        </div>

        {mode === 'new' && (
          <fieldset className="flex flex-col gap-2.5">
            <legend className="pb-2.5 text-[14px]/[normal] font-bold">몇 번 상담할까요?</legend>
            <div className="flex flex-wrap gap-2">
              {SESSION_OPTIONS.map((n) => (
                <button
                  key={n}
                  type="button"
                  aria-pressed={total === n}
                  onClick={() => setTotal(n)}
                  className={chip(total === n)}
                >
                  {n}회
                </button>
              ))}
            </div>
          </fieldset>
        )}

        <fieldset className="flex flex-col gap-2.5">
          <legend className="pb-2.5 text-[14px]/[normal] font-bold">어느 요일에 할까요?</legend>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              aria-pressed={weekdays.length === 7}
              onClick={() => setWeekdays(weekdays.length === 7 ? [] : ALL_DAYS)}
              className={chip(weekdays.length === 7)}
            >
              매일
            </button>
            {DAYS.map((label, day) => (
              <button
                key={label}
                type="button"
                aria-pressed={weekdays.includes(day)}
                aria-label={`${label}요일`}
                onClick={() => toggleDay(day)}
                className={`${chip(weekdays.includes(day))} min-w-11 px-0`}
              >
                {label}
              </button>
            ))}
          </div>
          {weekdays.length === 0 && <p className="text-[11.5px]/[normal] text-danger">요일을 하나 이상 골라 주세요</p>}
        </fieldset>

        <label className="flex flex-col gap-2.5">
          <span className="text-[14px]/[normal] font-bold">몇 시에 알려 드릴까요?</span>
          <input
            type="time"
            required
            value={time}
            onChange={(e) => setTime(e.target.value)}
            className="w-full rounded-xl bg-field px-4 py-3.5 text-[15px]/[normal] outline-none focus-visible:ring-2 focus-visible:ring-primary"
          />
        </label>

        {mode === 'new' && pushState !== 'on' && pushState !== null && (
          <div className="overflow-hidden rounded-xl bg-white shadow-card">
            {canAskPush ? (
              <Toggle
                checked={notify}
                onChange={setNotify}
                className="w-full justify-between px-4 py-3.5 text-left text-[13px]/[16px]"
              >
                <span>상담 시간에 알림 받기</span>
              </Toggle>
            ) : (
              <p className="px-4 py-3.5 text-[12px]/[1.6] text-muted">{pushHint(pushState)}</p>
            )}
          </div>
        )}

        <div className="mt-auto flex flex-col gap-2.5">
          {valid && (
            <p className="text-center text-[12.5px]/[1.6] text-muted">
              {daysLabel(weekdays)} {formatTime(time)}
              {mode === 'new' && `에 ${total}번의 상담을 함께해요`}
            </p>
          )}
          {error && (
            <p role="alert" className="text-center text-[12px]/[normal] text-danger">
              {error}
            </p>
          )}
          <button
            type="submit"
            disabled={!valid || submitting}
            className="w-full rounded-button bg-primary py-4 text-[15px]/[normal] font-bold text-white disabled:bg-disabled"
          >
            {mode === 'new' ? '계획 시작하기' : '일정 저장'}
          </button>
        </div>
      </form>
    </div>
  )
}

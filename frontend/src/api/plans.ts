// 상담 계획 API. docs/api-spec.md §6
// VITE_USE_MOCK=false 이면 실제 API, 그 외에는 목업(mockPlans)을 쓴다.
import { request, useMock } from './client'
import {
  mockCancelPlan,
  mockCompleteSession,
  mockCreatePlan,
  mockGetCurrentPlan,
  mockGetSession,
  mockRetryPlanSummary,
  mockRetrySessionSummary,
  mockUpdateSchedule,
} from './mockPlans'

export type SummaryStatus = 'pending' | 'done' | 'failed' | null

export type PlanSession = {
  number: number
  total: number
  conversationId: string
  title: string | null
  completedAt: string
  summaryStatus: SummaryStatus
  summary: string | null
}

export type Plan = {
  id: string
  status: 'active' | 'completed'
  totalSessions: number
  completedSessions: number
  weekdays: number[] // 0=월 … 6=일
  time: string // "22:00"
  timezone: string
  scheduleLabel: string
  nextReminderAt: string | null
  completedAt: string | null
  sessions: PlanSession[]
  summaryStatus: SummaryStatus
  summary: string | null
}

export type Schedule = { weekdays: number[]; time: string; timezone: string }
export type NewPlan = Schedule & { totalSessions: number }
export type SessionResult = { session: PlanSession; plan: Plan }

type RawSession = {
  number: number
  total: number
  conversation_id: string
  title: string | null
  completed_at: string
  summary_status: SummaryStatus
  summary: string | null
}

type RawPlan = {
  id: string
  status: Plan['status']
  total_sessions: number
  completed_sessions: number
  weekdays: number[]
  time: string
  timezone: string
  schedule_label: string
  next_reminder_at: string | null
  completed_at: string | null
  sessions: RawSession[]
  summary_status: SummaryStatus
  summary: string | null
}

const toSession = (s: RawSession): PlanSession => ({
  number: s.number,
  total: s.total,
  conversationId: s.conversation_id,
  title: s.title,
  completedAt: s.completed_at,
  summaryStatus: s.summary_status,
  summary: s.summary,
})

const toPlan = (p: RawPlan): Plan => ({
  id: p.id,
  status: p.status,
  totalSessions: p.total_sessions,
  completedSessions: p.completed_sessions,
  weekdays: p.weekdays,
  time: p.time,
  timezone: p.timezone,
  scheduleLabel: p.schedule_label,
  nextReminderAt: p.next_reminder_at,
  completedAt: p.completed_at,
  sessions: p.sessions.map(toSession),
  summaryStatus: p.summary_status,
  summary: p.summary,
})

const toResult = (body: { session: RawSession; plan: RawPlan }): SessionResult => ({
  session: toSession(body.session),
  plan: toPlan(body.plan),
})

export const deviceTimezone = () => Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Seoul'

// 진행 중인 계획. 없으면 가장 최근에 마친 계획, 그것도 없으면 null
export async function getCurrentPlan(): Promise<Plan | null> {
  if (useMock) return mockGetCurrentPlan()
  const res = await request('/plans/current')
  const { plan } = await res.json()
  return plan ? toPlan(plan) : null
}

export async function createPlan(input: NewPlan): Promise<Plan> {
  if (useMock) return mockCreatePlan(input)
  const res = await request('/plans', {
    method: 'POST',
    body: JSON.stringify({
      total_sessions: input.totalSessions,
      weekdays: input.weekdays,
      time: input.time,
      timezone: input.timezone,
    }),
  })
  return toPlan((await res.json()).plan)
}

export async function updateSchedule(planId: string, schedule: Schedule): Promise<Plan> {
  if (useMock) return mockUpdateSchedule(schedule)
  const res = await request(`/plans/${planId}`, { method: 'PATCH', body: JSON.stringify(schedule) })
  return toPlan((await res.json()).plan)
}

export async function cancelPlan(planId: string): Promise<void> {
  if (useMock) return mockCancelPlan()
  await request(`/plans/${planId}/cancel`, { method: 'POST' })
}

export async function retryPlanSummary(planId: string): Promise<Plan> {
  if (useMock) return mockRetryPlanSummary()
  const res = await request(`/plans/${planId}/summary/retry`, { method: 'POST' })
  return toPlan((await res.json()).plan)
}

// 대화를 계획의 다음 회기로 마친다 ("상담 마치기")
export async function completeSession(conversationId: string): Promise<SessionResult> {
  if (useMock) return mockCompleteSession(conversationId)
  const res = await request(`/conversations/${conversationId}/complete`, { method: 'POST' })
  return toResult(await res.json())
}

export async function getSession(conversationId: string): Promise<SessionResult> {
  if (useMock) return mockGetSession(conversationId)
  const res = await request(`/conversations/${conversationId}/session`)
  return toResult(await res.json())
}

export async function retrySessionSummary(conversationId: string): Promise<SessionResult> {
  if (useMock) return mockRetrySessionSummary(conversationId)
  const res = await request(`/conversations/${conversationId}/session/summary/retry`, { method: 'POST' })
  return toResult(await res.json())
}

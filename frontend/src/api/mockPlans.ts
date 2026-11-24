// 백엔드 없이 상담 계획 화면을 개발하기 위한 목업. 요약은 잠깐 뒤에 "만들어진" 것으로 바뀐다.
import { ApiError } from './client'
import { mockGetConversation } from './mockChat'
import type { NewPlan, Plan, PlanSession, Schedule, SessionResult } from './plans'

const DAYS = ['월', '화', '수', '목', '금', '토', '일']

export const mockPlanOptions = { summaryDelayMs: 1200 }

let plan: Plan | null = null
let readyAt = new Map<string, number>() // 요약이 완성되는 시각 (회기 conversationId / 'plan')

export function resetMockPlans(next: Plan | null = null) {
  plan = next ? structuredClone(next) : null
  readyAt = new Map()
}

const label = (s: Schedule) =>
  `${s.weekdays.length === 7 ? '매일' : '매주 ' + [...s.weekdays].sort().map((d) => DAYS[d]).join('·')} ${s.time}`

function nextReminder(s: Schedule): string | null {
  const [h, m] = s.time.split(':').map(Number)
  const now = new Date()
  for (let i = 0; i < 8; i++) {
    const d = new Date(now)
    d.setDate(now.getDate() + i)
    d.setHours(h, m, 0, 0)
    if (s.weekdays.includes((d.getDay() + 6) % 7) && d > now) return d.toISOString()
  }
  return null
}

function sessionSummary(conversationTitle: string | null) {
  return [
    `오늘은 '${conversationTitle ?? '마음이 복잡했던 일'}'에 대해 이야기를 나누셨어요.`,
    '그 순간 떠오른 생각과 감정을 차분히 살펴보셨어요.',
    '다음 회기까지 비슷한 순간이 오면 떠오른 생각을 한 줄 적어 보기로 했어요.',
  ].join('\n')
}

// 시간이 지나면 pending 인 요약을 완성한다.
function settle(): Plan | null {
  if (!plan) return null
  const now = Date.now()
  for (const s of plan.sessions) {
    if (s.summaryStatus === 'pending' && now >= (readyAt.get(s.conversationId) ?? 0)) {
      s.summaryStatus = 'done'
      s.summary = sessionSummary(s.title)
    }
  }
  const allDone =
    plan.status === 'completed' && plan.sessions.every((s) => s.summaryStatus === 'done')
  if (allDone && plan.summaryStatus === null) {
    plan.summaryStatus = 'pending'
    readyAt.set('plan', now + mockPlanOptions.summaryDelayMs)
  }
  if (plan.summaryStatus === 'pending' && now >= (readyAt.get('plan') ?? 0)) {
    plan.summaryStatus = 'done'
    plan.summary = [
      `${plan.totalSessions}번의 상담을 끝까지 마치셨어요.`,
      ...plan.sessions.map((s) => `${s.number}회기: ${s.title ?? '이야기를 나눴어요'}`),
      '회기를 거듭하며 떠오른 생각을 알아차리고 다르게 바라보는 연습을 이어 오셨어요.',
    ].join('\n')
  }
  return structuredClone(plan)
}

export async function mockGetCurrentPlan(): Promise<Plan | null> {
  return settle()
}

export async function mockCreatePlan(input: NewPlan): Promise<Plan> {
  if (plan?.status === 'active') throw new ApiError('plan_exists', '이미 진행 중인 상담 계획이 있어요.')
  readyAt = new Map()
  plan = {
    id: `plan-${Date.now()}`,
    status: 'active',
    totalSessions: input.totalSessions,
    completedSessions: 0,
    weekdays: [...input.weekdays].sort(),
    time: input.time,
    timezone: input.timezone,
    scheduleLabel: label(input),
    nextReminderAt: nextReminder(input),
    completedAt: null,
    sessions: [],
    summaryStatus: null,
    summary: null,
  }
  return structuredClone(plan)
}

export async function mockUpdateSchedule(schedule: Schedule): Promise<Plan> {
  if (!plan) throw new ApiError('not_found', '상담 계획을 찾을 수 없습니다.')
  Object.assign(plan, {
    weekdays: [...schedule.weekdays].sort(),
    time: schedule.time,
    timezone: schedule.timezone,
    scheduleLabel: label(schedule),
    nextReminderAt: nextReminder(schedule),
  })
  return structuredClone(plan)
}

export async function mockCancelPlan(): Promise<void> {
  plan = null
}

export async function mockRetryPlanSummary(): Promise<Plan> {
  return settle()!
}

function result(session: PlanSession): SessionResult {
  const current = settle()!
  return { session: current.sessions.find((s) => s.number === session.number)!, plan: current }
}

export async function mockCompleteSession(conversationId: string): Promise<SessionResult> {
  const existing = plan?.sessions.find((s) => s.conversationId === conversationId)
  if (existing) return result(existing)
  if (!plan || plan.status !== 'active') throw new ApiError('no_active_plan', '진행 중인 상담 계획이 없어요.')
  const conversation = await mockGetConversation(conversationId)
  if (!conversation.messages.some((m) => m.role === 'user')) {
    throw new ApiError('empty_session', '이야기를 나눈 뒤에 상담을 마칠 수 있어요.')
  }
  const session: PlanSession = {
    number: plan.sessions.length + 1,
    total: plan.totalSessions,
    conversationId,
    title: conversation.title,
    completedAt: new Date().toISOString(),
    summaryStatus: 'pending',
    summary: null,
  }
  readyAt.set(conversationId, Date.now() + mockPlanOptions.summaryDelayMs)
  plan.sessions.push(session)
  plan.completedSessions = plan.sessions.length
  if (plan.completedSessions >= plan.totalSessions) {
    plan.status = 'completed'
    plan.completedAt = session.completedAt
    plan.nextReminderAt = null
  }
  return result(session)
}

export async function mockGetSession(conversationId: string): Promise<SessionResult> {
  const found = plan?.sessions.find((s) => s.conversationId === conversationId)
  if (!found) throw new ApiError('not_found', '상담 계획으로 마친 대화가 아니에요.')
  return result(found)
}

export async function mockRetrySessionSummary(conversationId: string): Promise<SessionResult> {
  return mockGetSession(conversationId)
}

// 대화 화면이 "이미 마친 회기"인지 알 수 있게 (실제로는 GET /conversations/{id} 의 session)
export function mockSessionOf(conversationId: string): { number: number; completedAt: string } | null {
  const found = plan?.sessions.find((s) => s.conversationId === conversationId)
  return found ? { number: found.number, completedAt: found.completedAt } : null
}

import { useCallback, useEffect, useState } from 'react'
import { getCurrentPlan, type Plan } from '../api/plans'

export const SUMMARY_POLL_MS = 3000

// 요약이 만들어지는 중이면(pending) 잠깐마다 다시 불러온다.
export const hasPending = (plan: Plan | null) =>
  !!plan && (plan.summaryStatus === 'pending' || plan.sessions.some((s) => s.summaryStatus === 'pending'))

export function useCurrentPlan(enabled = true) {
  const [plan, setPlan] = useState<Plan | null>(null)
  const [loaded, setLoaded] = useState(false)

  const reload = useCallback(
    () =>
      getCurrentPlan()
        .then((p) => {
          setPlan(p)
          setLoaded(true)
        })
        .catch(() => setLoaded(true)),
    [],
  )

  useEffect(() => {
    if (enabled) void reload()
  }, [enabled, reload])

  useEffect(() => {
    if (!hasPending(plan)) return
    const timer = setTimeout(reload, SUMMARY_POLL_MS)
    return () => clearTimeout(timer)
  }, [plan, reload])

  return { plan, setPlan, loaded, reload }
}

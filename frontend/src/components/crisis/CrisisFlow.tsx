import { useState } from 'react'
import type { CrisisResource } from '../../api/chat'
import { withDefaultResources } from '../../lib/crisis'
import { CallFailedScreen, CallingScreen } from './CallScreen'
import { CrisisSheet } from './CrisisSheet'

type CrisisFlowProps = {
  resources: CrisisResource[]
  onClose: () => void
}

type Step = { name: 'sheet' } | { name: 'calling' | 'failed'; resource: CrisisResource }

// 위기 안내 시트 → 전화 연결 중 → (실패 시) 연결 실패. 닫으면 일반 대화로 돌아간다.
export function CrisisFlow({ resources, onClose }: CrisisFlowProps) {
  const [step, setStep] = useState<Step>({ name: 'sheet' })
  const backToSheet = () => setStep({ name: 'sheet' })

  if (step.name === 'calling') {
    return (
      <CallingScreen
        resource={step.resource}
        onFail={() => setStep({ name: 'failed', resource: step.resource })}
        onEnd={backToSheet}
      />
    )
  }

  if (step.name === 'failed') {
    return (
      <CallFailedScreen
        resource={step.resource}
        onRetry={() => setStep({ name: 'calling', resource: step.resource })}
        onClose={backToSheet}
      />
    )
  }

  return (
    <CrisisSheet
      resources={withDefaultResources(resources)}
      onCall={(resource) => setStep({ name: 'calling', resource })}
      onClose={onClose}
    />
  )
}

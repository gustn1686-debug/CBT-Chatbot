import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Mascot, type MascotVariant } from '../components/Mascot'
import { Toggle } from '../components/Toggle'
import { completeOnboarding } from '../lib/preferences'
import { useDocumentTitle } from '../hooks/useDocumentTitle'

type Step = {
  title: string
  body: string[]
  mascot: { variant: MascotVariant; width: number; height: number }
}

// Figma: HiFi_1_온보딩_STEP1~4
const steps: Step[] = [
  {
    title: '이 서비스는 무엇인가요?',
    body: ['CBT(인지행동치료) 원리를 바탕으로 생각을 정리하도록', '돕는 대화형 자기 정리 도구예요.'],
    mascot: { variant: 'waving', width: 190, height: 232 },
  },
  {
    title: '이것만은 분명히 알려드릴게요',
    body: ['이 서비스는 전문적인 심리 치료나 상담을', '대체하지 않아요.'],
    mascot: { variant: 'thinking', width: 210, height: 210 },
  },
  {
    title: '혹시 위급한 상황이라면',
    body: ['위기 상황이 감지되면 대화를 잠시 멈추고,', '전문기관과 연결되는 화면으로 안내해드려요.'],
    mascot: { variant: 'playing', width: 230, height: 178 },
  },
  {
    title: '기록을 남길까요?',
    body: ['나눈 대화를 저장해두면 다음에 이어보기 편해요.', '저장 여부는 언제든 바꿀 수 있어요.'],
    mascot: { variant: 'main', width: 200, height: 244 },
  },
]

export function Onboarding() {
  useDocumentTitle('시작하기')
  const navigate = useNavigate()
  const [index, setIndex] = useState(0)
  const [saveHistory, setSaveHistory] = useState(true)

  const step = steps[index]
  const isLast = index === steps.length - 1

  const finish = () => {
    completeOnboarding(saveHistory)
    navigate('/start', { replace: true })
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <div className="flex justify-end px-6 py-1 pt-5">
        {!isLast && (
          <button type="button" onClick={finish} className="-m-3 p-3 text-[12px]/[normal] text-muted">
            건너뛰기
          </button>
        )}
      </div>

      <main className="flex flex-1 flex-col items-center justify-center gap-[18px] px-7 pt-2.5 pb-5">
        <ol className="flex gap-1.5" aria-label={`STEP ${index + 1}/${steps.length}`}>
          {steps.map((_, i) => (
            <li
              key={i}
              aria-current={i === index ? 'step' : undefined}
              className={`h-1.5 rounded-[3px] ${i === index ? 'w-[18px] bg-primary' : 'w-1.5 bg-line'}`}
            />
          ))}
        </ol>

        <Mascot {...step.mascot} />

        <h1 className="text-center text-[22px]/[normal] font-bold">{step.title}</h1>
        <p className="text-center text-[13px]/[normal] text-muted">
          {step.body.map((line) => (
            <span key={line} className="block">
              {line}
            </span>
          ))}
        </p>

        {isLast && (
          <Toggle
            checked={saveHistory}
            onChange={setSaveHistory}
            iconPosition="start"
            className="gap-2.5 rounded-xl bg-white px-4 py-3 shadow-card"
          >
            <span className="text-[12.5px]/[normal]">대화 기록 저장하기</span>
          </Toggle>
        )}
      </main>

      <div className="px-7 pt-2 pb-5">
        <button
          type="button"
          onClick={isLast ? finish : () => setIndex(index + 1)}
          className="w-full rounded-button bg-primary py-4 text-[15px]/[normal] font-bold text-white"
        >
          {isLast ? '시작하기' : '다음'}
        </button>
      </div>
    </div>
  )
}

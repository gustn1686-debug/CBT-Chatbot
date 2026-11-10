// 생각 기록(피그마 "기록")에 대응한다. docs/api-spec.md §6 의 /thought-records 는 아직 미확정이라
// 모델은 Figma(기록목록·기록상세) 기준으로 정했고, 지금은 목업 데이터를 돌려준다.
// 실제 API 연동 시 이 파일만 교체한다.
import { ApiError } from './client'

export const RECORD_TAGS = ['불안', '자기비판', '관계', '업무'] as const
export type RecordTag = (typeof RECORD_TAGS)[number]

export type ThoughtRecord = {
  id: string
  date: string // YYYY-MM-DD
  title: string
  tag: RecordTag
  situation: string
  firstThought: string
  emotions: string[]
  findings: string
  alternative: string
  nextAction: string
}

export type RecordPatch = Partial<
  Pick<ThoughtRecord, 'situation' | 'firstThought' | 'emotions' | 'findings' | 'alternative' | 'nextAction'>
>

const seed = (): ThoughtRecord[] => [
  {
    id: 'r-4',
    date: '2025-03-12',
    title: '발표 자료 오타 관련 생각 정리',
    tag: '업무',
    situation: '어제 팀 회의에서 발표 자료에 오타가 있었어요.',
    firstThought: '나는 왜 이렇게 매번 실수할까. 사람들이 날 무능하다고 생각할 것 같아.',
    emotions: ['불안', '부끄러움', '속상함'],
    findings: '돌이켜보면 오타 하나로 전체 발표를 망친 건 아니었어요.',
    alternative: '실수는 누구나 할 수 있고, 다음에 다시 확인하는 습관을 만들면 될 것 같아요.',
    nextAction: '중요한 자료는 제출 전에 한 번 더 소리 내어 읽어보기',
  },
  // 아래 3건은 목록 화면용 목업이며 상세 본문은 임의의 예시다.
  {
    id: 'r-3',
    date: '2025-03-09',
    title: '친구와의 약속 취소, 마음이 쓰였던 날',
    tag: '관계',
    situation: '친구가 약속을 당일에 취소했어요.',
    firstThought: '내가 중요하지 않은 사람인가 보다.',
    emotions: ['서운함'],
    findings: '친구가 야근 때문에 어쩔 수 없었다고 사과했어요.',
    alternative: '약속을 취소한 것과 나를 가볍게 보는 것은 별개일 수 있어요.',
    nextAction: '서운했던 마음을 친구에게 차분히 말해보기',
  },
  {
    id: 'r-2',
    date: '2025-03-05',
    title: '면접 결과를 기다리며 든 생각',
    tag: '자기비판',
    situation: '면접을 본 뒤 결과를 기다리고 있어요.',
    firstThought: '그때 그렇게 대답하지 말았어야 했는데.',
    emotions: ['초조함', '자책'],
    findings: '답변 중 잘한 부분도 분명히 있었어요.',
    alternative: '결과와 상관없이 준비한 과정은 의미가 있었어요.',
    nextAction: '결과를 기다리는 동안 산책하며 환기하기',
  },
  {
    id: 'r-1',
    date: '2025-02-27',
    title: '발표 전 긴장했던 순간',
    tag: '불안',
    situation: '발표 직전에 심장이 빠르게 뛰었어요.',
    firstThought: '말을 더듬으면 어쩌지.',
    emotions: ['불안', '긴장'],
    findings: '막상 시작하니 처음보다 훨씬 편해졌어요.',
    alternative: '긴장은 준비하고 있다는 신호일 수도 있어요.',
    nextAction: '발표 전에 천천히 숨 세 번 쉬기',
  },
]

// 화면 확인용: 주소에 ?mock=empty 를 붙여 열면 기록이 없는 상태로 시작한다.
const startEmpty = new URLSearchParams(window.location.search).get('mock') === 'empty'
let store: ThoughtRecord[] = startEmpty ? [] : seed()

const copy = (record: ThoughtRecord): ThoughtRecord => ({ ...record, emotions: [...record.emotions] })

// 테스트에서 상태를 되돌리거나 원하는 기록으로 채울 때 쓴다.
export function resetMockRecords(records: ThoughtRecord[] = seed()) {
  store = records.map(copy)
}

export async function listRecords(): Promise<ThoughtRecord[]> {
  return store.map(copy).sort((a, b) => b.date.localeCompare(a.date))
}

export async function getRecord(id: string): Promise<ThoughtRecord | null> {
  const found = store.find((record) => record.id === id)
  return found ? copy(found) : null
}

export async function updateRecord(id: string, patch: RecordPatch): Promise<ThoughtRecord> {
  const index = store.findIndex((record) => record.id === id)
  if (index === -1) throw new ApiError('not_found', '기록을 찾을 수 없어요.')
  store[index] = copy({ ...store[index], ...patch })
  return copy(store[index])
}

export async function deleteAllRecords(): Promise<void> {
  store = []
}

import { useEffect, useState, type KeyboardEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { getRecord, updateRecord, type ThoughtRecord } from '../api/records'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { formatDate } from '../lib/format'

type Field = 'situation' | 'firstThought' | 'emotions' | 'findings' | 'alternative' | 'nextAction'
type Draft = Pick<ThoughtRecord, Field>

// Figma: HiFi_5_기록상세
const SECTIONS: { key: Field; label: string }[] = [
  { key: 'situation', label: '상황' },
  { key: 'firstThought', label: '처음 떠오른 생각' },
  { key: 'emotions', label: '감정' },
  { key: 'findings', label: '대화에서 확인한 점' },
  { key: 'alternative', label: '다른 해석' },
  { key: 'nextAction', label: '다음에 해볼 행동' },
]

const pickDraft = (r: ThoughtRecord): Draft => ({
  situation: r.situation,
  firstThought: r.firstThought,
  emotions: [...r.emotions],
  findings: r.findings,
  alternative: r.alternative,
  nextAction: r.nextAction,
})

const cardIcon = 'text-muted'

export function RecordDetail() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const [record, setRecord] = useState<ThoughtRecord | null | undefined>(undefined) // undefined: 불러오는 중, null: 없음
  const [draft, setDraft] = useState<Draft | null>(null)
  const [editing, setEditing] = useState<Field | null>(null)
  const [status, setStatus] = useState<'saved' | 'error' | null>(null)

  useDocumentTitle(record ? record.title : '기록')

  useEffect(() => {
    let cancelled = false
    getRecord(id).then((found) => {
      if (cancelled) return
      setRecord(found)
      setDraft(found ? pickDraft(found) : null)
    })
    return () => {
      cancelled = true
    }
  }, [id])

  if (record === undefined) return null

  if (record === null || draft === null) {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center gap-3 px-5">
        <p className="text-[13px]/[normal]">기록을 찾을 수 없어요</p>
        <Link to="/records" className="text-[12px]/[normal] text-primary">
          목록으로
        </Link>
      </div>
    )
  }

  const dirty = JSON.stringify(pickDraft(record)) !== JSON.stringify(draft)

  const change = (field: Field, value: string | string[]) => {
    setDraft({ ...draft, [field]: value })
    setStatus(null)
  }

  const save = async () => {
    try {
      const next = await updateRecord(record.id, draft)
      setRecord(next)
      setDraft(pickDraft(next))
      setStatus('saved')
    } catch {
      setStatus('error')
    }
  }

  const stopOnEscape = (e: KeyboardEvent) => e.key === 'Escape' && setEditing(null)

  return (
    <div className="flex h-dvh flex-col">
      <header className="flex items-center justify-between px-4 pt-5 pb-2.5 text-muted">
        <Link to="/records" className="-m-3 p-3 text-[13px]/[normal]">
          ‹ 목록으로
        </Link>
        <span className="text-[11.5px]/[normal]">{formatDate(record.date)}</span>
      </header>

      <main className="flex flex-1 flex-col gap-3 overflow-y-auto px-5 pt-1 pb-4">
        <h1 className="sr-only">{record.title}</h1>
        {SECTIONS.map(({ key, label }) => (
          <section key={key} aria-label={label} className="flex flex-col gap-2 rounded-xl bg-white p-3.5 shadow-card">
            <div className="flex items-center justify-between text-muted">
              <h2 className="text-[11.5px]/[14px] font-bold">{label}</h2>
              <div className="flex">
                <button
                  type="button"
                  aria-label={`${label} 수정`}
                  onClick={() => setEditing(key)}
                  className={`-my-3 px-2 py-3 text-[12px]/[14px] ${cardIcon}`}
                >
                  ✎
                </button>
                <button
                  type="button"
                  aria-label={`${label} 비우기`}
                  onClick={() => change(key, key === 'emotions' ? [] : '')}
                  className={`-my-3 px-2 py-3 text-[11px]/[14px] ${cardIcon}`}
                >
                  ✕
                </button>
              </div>
            </div>

            {key === 'emotions' ? (
              <EmotionChips
                emotions={draft.emotions}
                editing={editing === key}
                onChange={(next) => change(key, next)}
                onDone={() => setEditing(null)}
              />
            ) : editing === key ? (
              <textarea
                autoFocus
                rows={3}
                value={draft[key]}
                aria-label={label}
                onChange={(e) => change(key, e.target.value)}
                onBlur={() => setEditing(null)}
                onKeyDown={stopOnEscape}
                className="w-full resize-none rounded-lg border border-line p-2 text-[12.5px]/[15px] outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
              />
            ) : (
              <p className="text-[12.5px]/[15px]">
                {draft[key] || <span className="text-placeholder">내용이 없어요</span>}
              </p>
            )}
          </section>
        ))}
      </main>

      <footer className="flex flex-col gap-2.5 px-5 pt-2.5 pb-4">
        <button
          type="button"
          onClick={() => navigate('/chat', { state: { record: { id: record.id, title: record.title } } })}
          className="rounded-button bg-primary py-3.5 text-[13.5px]/[normal] font-bold text-white"
        >
          이 기록에서 대화 이어가기
        </button>
        <button
          type="button"
          onClick={save}
          disabled={!dirty}
          className="rounded-button border border-line bg-white py-3.5 text-[13px]/[normal] disabled:opacity-40"
        >
          수정 내용 저장
        </button>
        <p role="status" className="min-h-4 text-center text-[11px]/[normal] text-muted">
          {status === 'saved' && '저장했어요'}
          {status === 'error' && '저장하지 못했어요. 잠시 후 다시 시도해 주세요'}
        </p>
      </footer>
    </div>
  )
}

type EmotionChipsProps = {
  emotions: string[]
  editing: boolean
  onChange: (next: string[]) => void
  onDone: () => void
}

function EmotionChips({ emotions, editing, onChange, onDone }: EmotionChipsProps) {
  const [text, setText] = useState('')

  const add = () => {
    const value = text.trim()
    if (value && !emotions.includes(value)) onChange([...emotions, value])
    setText('')
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {emotions.length === 0 && !editing && <span className="text-[12.5px]/[15px] text-placeholder">내용이 없어요</span>}
      {emotions.map((emotion) => (
        <span
          key={emotion}
          className="flex items-center gap-1 rounded-[14px] bg-tag-bg px-2.5 py-1.5 text-[11.5px]/[14px] text-primary-ink"
        >
          {emotion}
          <button
            type="button"
            aria-label={`${emotion} 제거`}
            onClick={() => onChange(emotions.filter((e) => e !== emotion))}
            className="-m-2 p-2 text-[9px]/[14px]"
          >
            ✕
          </button>
        </span>
      ))}
      {editing && (
        <input
          autoFocus
          value={text}
          aria-label="감정 추가"
          placeholder="감정 추가"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.nativeEvent.isComposing) {
              e.preventDefault()
              add()
            } else if (e.key === 'Escape') onDone()
          }}
          onBlur={() => {
            add()
            onDone()
          }}
          className="w-24 rounded-[14px] border border-line px-2.5 py-1.5 text-[11.5px]/[14px] outline-none placeholder:text-placeholder focus-visible:ring-2 focus-visible:ring-primary/40"
        />
      )}
    </div>
  )
}

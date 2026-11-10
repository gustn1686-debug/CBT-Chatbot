import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listRecords, RECORD_TAGS, type RecordTag, type ThoughtRecord } from '../api/records'
import { Mascot } from '../components/Mascot'
import { TabBar } from '../components/TabBar'
import { formatDate } from '../lib/format'
import { useDocumentTitle } from '../hooks/useDocumentTitle'

type Filter = '전체' | RecordTag

const chip = 'rounded-2xl px-3.5 py-2 text-[11.5px]/[14px]'

// Figma: HiFi_5_기록목록 / EX_8_기록목록_빈상태
export function Records() {
  useDocumentTitle('내 기록')
  const [records, setRecords] = useState<ThoughtRecord[] | null>(null)
  const [filter, setFilter] = useState<Filter>('전체')

  useEffect(() => {
    listRecords().then(setRecords)
  }, [])

  const visible = records?.filter((r) => filter === '전체' || r.tag === filter) ?? []
  const noRecordsAtAll = records !== null && records.length === 0

  return (
    <div className="flex min-h-dvh flex-col">
      <main className="flex flex-1 flex-col gap-3.5 px-5 pt-5 pb-4">
        <h1 className="text-[19px]/[normal] font-bold">내 기록</h1>

        {records !== null && (
          <div className="flex flex-wrap gap-2" role="group" aria-label="분류">
            {(noRecordsAtAll ? (['전체'] as const) : (['전체', ...RECORD_TAGS] as const)).map((name) => {
              const selected = filter === name
              return (
                <button
                  key={name}
                  type="button"
                  aria-pressed={selected}
                  onClick={() => setFilter(name)}
                  className={`${chip} ${selected ? 'bg-primary text-white' : 'bg-white shadow-card'}`}
                >
                  {name}
                </button>
              )
            })}
          </div>
        )}

        {noRecordsAtAll ? (
          <div className="flex flex-col items-center gap-2.5 pt-[60px] pb-10">
            <Mascot variant="main" width={120} height={148} />
            <p className="text-[14px]/[normal] font-bold">아직 기록이 없어요</p>
            <p className="text-center text-[11.5px]/[normal] text-muted">
              대화를 나누면 여기에
              <br />
              생각을 정리한 기록이 쌓여요
            </p>
          </div>
        ) : records !== null && visible.length === 0 ? (
          <p className="pt-10 text-center text-[11.5px]/[normal] text-muted">이 분류의 기록이 없어요</p>
        ) : (
          <ul className="flex flex-col gap-3.5">
            {visible.map((record) => (
              <li key={record.id}>
                <Link
                  to={`/records/${record.id}`}
                  className="flex items-center gap-2 rounded-xl bg-white px-3.5 py-3 shadow-card"
                >
                  <span className="flex flex-1 flex-col items-start gap-1">
                    <span className="text-[10.5px]/[13px] text-muted">{formatDate(record.date)}</span>
                    <span className="text-[12.5px]/[15px]">{record.title}</span>
                    <span className="rounded-[10px] bg-tag-bg px-2 py-[3px] text-[10px]/[12px] text-primary-ink">
                      {record.tag}
                    </span>
                  </span>
                  <span className="text-[15px]/[normal] text-muted" aria-hidden>
                    ›
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </main>
      <TabBar />
    </div>
  )
}

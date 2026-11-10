import { useState } from 'react'
import { Link } from 'react-router-dom'
import { deleteAllRecords } from '../api/records'
import { ConfirmModal } from '../components/ConfirmModal'
import { TabBar } from '../components/TabBar'
import { Toggle } from '../components/Toggle'
import {
  getRetentionDays,
  isNotificationsOn,
  isSaveHistory,
  RETENTION_OPTIONS,
  setNotificationsOn,
  setRetentionDays,
  setSaveHistory,
  type RetentionDays,
} from '../lib/preferences'
import { useDocumentTitle } from '../hooks/useDocumentTitle'

const retentionLabel = (days: RetentionDays) => (days === 365 ? '1년' : `${days}일`)

const card = 'overflow-hidden rounded-xl bg-white shadow-card'
const row = 'flex w-full items-center justify-between px-4 py-3.5 text-left text-[13px]/[16px]'

type Dialog = 'delete-all' | 'withdraw' | null

// Figma: HiFi_7_설정 / EX_2_기록삭제_확인모달 / EX_3_동의철회_확인모달
// 보관 기간·동의 철회는 서버 정책(docs/api-spec.md §7-5)이 정해지기 전까지 이 기기의 설정으로만 동작한다.
export function Settings() {
  useDocumentTitle('설정')
  const [days, setDays] = useState(getRetentionDays)
  const [saveHistory, setSaveHistoryState] = useState(isSaveHistory)
  const [notifications, setNotificationsState] = useState(isNotificationsOn)
  const [dialog, setDialog] = useState<Dialog>(null)
  const [deletedAll, setDeletedAll] = useState(false)

  const changeRetention = (value: number) => {
    const next = RETENTION_OPTIONS.find((option) => option === value)
    if (!next) return
    setRetentionDays(next)
    setDays(next)
  }

  const changeSaveHistory = (next: boolean) => {
    if (!next) {
      setDialog('withdraw') // 철회는 확인을 거친다. 다시 켜는 건 바로 적용한다.
      return
    }
    setSaveHistory(true)
    setSaveHistoryState(true)
  }

  const withdraw = () => {
    setSaveHistory(false)
    setSaveHistoryState(false)
    setDialog(null)
  }

  const deleteAll = async () => {
    setDialog(null)
    await deleteAllRecords()
    setDeletedAll(true)
  }

  const changeNotifications = (next: boolean) => {
    setNotificationsOn(next)
    setNotificationsState(next)
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <main className="flex flex-1 flex-col gap-3.5 px-5 pt-5 pb-4">
        <h1 className="text-[19px]/[normal] font-bold">설정</h1>

        <div className={card}>
          <label className={row}>
            <span>기록 저장 기간</span>
            <span className="flex items-center text-[12px]/[16px] text-muted">
              <select
                aria-label="기록 저장 기간"
                value={days}
                onChange={(e) => changeRetention(Number(e.target.value))}
                className="-my-3.5 -ml-3 cursor-pointer appearance-none bg-transparent py-3.5 pl-3 text-right outline-none"
              >
                {RETENTION_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {retentionLabel(option)}
                  </option>
                ))}
              </select>
              <span aria-hidden className="pl-1 text-[8px]">
                ▾
              </span>
            </span>
          </label>
        </div>

        <div>
          <div className={card}>
            <button type="button" onClick={() => setDialog('delete-all')} className={row}>
              <span>전체 기록 삭제</span>
              <span aria-hidden className="text-[15px]/[16px] text-muted">
                ›
              </span>
            </button>
          </div>
          <p role="status" className="px-1 pt-1.5 text-[10px]/[normal] text-muted empty:hidden">
            {deletedAll && '모든 기록을 삭제했어요'}
          </p>
        </div>

        <div className={card}>
          <Toggle checked={saveHistory} onChange={changeSaveHistory} className={`${row} justify-between`}>
            <span>데이터 수집 동의 철회</span>
          </Toggle>
        </div>

        <div className={card}>
          <Toggle checked={notifications} onChange={changeNotifications} className={`${row} justify-between`}>
            <span>알림</span>
          </Toggle>
          <div className="h-px bg-line" />
          <Link to="/settings/about" className={row}>
            <span>앱 정보</span>
            <span aria-hidden className="text-[15px]/[16px] text-muted">
              ›
            </span>
          </Link>
        </div>
      </main>
      <TabBar />

      {dialog === 'delete-all' && (
        <ConfirmModal
          title="모든 기록을 삭제할까요?"
          description="삭제된 기록은 복구할 수 없어요."
          confirmLabel="삭제하기"
          tone="danger"
          onCancel={() => setDialog(null)}
          onConfirm={deleteAll}
        />
      )}
      {dialog === 'withdraw' && (
        <ConfirmModal
          title="데이터 수집 동의를 철회할까요?"
          description="철회 시 앞으로의 대화는 저장되지 않아요. 기존 기록은 그대로 유지돼요."
          confirmLabel="철회하기"
          onCancel={() => setDialog(null)}
          onConfirm={withdraw}
        />
      )}
    </div>
  )
}

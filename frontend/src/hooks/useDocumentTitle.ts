import { useEffect } from 'react'

// 탭 제목과 스크린리더가 화면 이동을 알리는 데 쓰인다. 예) "로그인 · Synap"
export function useDocumentTitle(title: string) {
  useEffect(() => {
    document.title = `${title} · Synap`
  }, [title])
}

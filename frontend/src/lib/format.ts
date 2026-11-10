// 2025-03-12 → 2025.03.12 (Figma 표기)
export const formatDate = (iso: string) => iso.replaceAll('-', '.')

// 서버의 ISO 시각(2026-11-10T06:49:29Z)을 이 기기의 날짜(YYYY-MM-DD)로 바꾼다.
export function toLocalDate(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso.slice(0, 10)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

// 2025-03-12 → 2025.03.12 (Figma 표기)
export const formatDate = (iso: string) => iso.replaceAll('-', '.')

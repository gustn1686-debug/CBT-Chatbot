import type { CrisisResource } from '../api/chat'

// Figma: HiFi_6_위기대응. 서버가 crisis_resources 를 주지 않아도 반드시 안내할 수 있도록 둔다.
export const DEFAULT_CRISIS_RESOURCES: CrisisResource[] = [
  { name: '정신건강 위기상담전화', tel: '1577-0199' },
  { name: '생명의전화', tel: '1588-9191' },
]

export const withDefaultResources = (resources: CrisisResource[]) =>
  resources.length > 0 ? resources : DEFAULT_CRISIS_RESOURCES

export const telHref = (tel: string) => `tel:${tel.replaceAll('-', '')}`

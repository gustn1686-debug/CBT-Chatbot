import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { manifest } from '../pwa.manifest.ts'

// 테스트는 frontend/ 에서 실행된다.
const root = process.cwd()
const publicFile = (src: string) => join(root, 'public', src)

function pngSize(path: string) {
  const buf = readFileSync(path)
  return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) }
}

describe('PWA 설치 정보', () => {
  it('설치에 필요한 기본 항목이 있다', () => {
    expect(manifest.name).toBe('Synap')
    expect(manifest.short_name).toBeTruthy()
    expect(manifest.start_url).toBe('/')
    expect(manifest.scope).toBe('/')
    expect(manifest.display).toBe('standalone')
    expect(manifest.lang).toBe('ko')
    expect(manifest.theme_color).toBe('#5170b8')
    expect(manifest.background_color).toBeTruthy()
  })

  it('192·512 아이콘과 512 maskable 아이콘이 있다', () => {
    const icons = manifest.icons ?? []
    const has = (sizes: string, purpose: string) =>
      icons.some((icon) => icon.sizes === sizes && icon.purpose === purpose && icon.type === 'image/png')
    expect(has('192x192', 'any')).toBe(true)
    expect(has('512x512', 'any')).toBe(true)
    expect(has('512x512', 'maskable')).toBe(true)
  })

  it('선언한 아이콘 파일이 실제로 있고, 크기가 선언과 같다', () => {
    for (const icon of manifest.icons ?? []) {
      const file = publicFile(icon.src)
      expect(existsSync(file), icon.src).toBe(true)
      const [w, h] = icon.sizes!.split('x').map(Number)
      expect(pngSize(file), icon.src).toEqual({ width: w, height: h })
    }
  })

  it('바로가기는 앱 범위 안의 주소이고 아이콘 파일이 있다', () => {
    for (const shortcut of manifest.shortcuts ?? []) {
      expect(shortcut.url.startsWith('/')).toBe(true)
      for (const icon of shortcut.icons ?? []) expect(existsSync(publicFile(icon.src))).toBe(true)
    }
  })

  it('index.html 에 한국어 설정, iOS 아이콘, 테마색이 있다', () => {
    const html = readFileSync(join(root, 'index.html'), 'utf8')
    expect(html).toContain('<html lang="ko">')
    expect(html).toContain('rel="apple-touch-icon"')
    expect(html).toContain('name="theme-color" content="#5170b8"')
    expect(pngSize(publicFile('icons/apple-touch-icon.png'))).toEqual({ width: 180, height: 180 })
    expect(existsSync(publicFile('favicon-32.png'))).toBe(true)
  })
})

describe('이미지 용량', () => {
  const dir = join(root, 'src/assets/mascot')
  const files = readdirSync(dir)

  it('마스코트는 모두 webp 이고 PNG 원본은 남아 있지 않다', () => {
    expect(files.length).toBeGreaterThan(0)
    expect(files.filter((f) => !f.endsWith('.webp'))).toEqual([])
  })

  it('마스코트 하나는 100KB, 전부 합쳐 300KB 를 넘지 않는다 (오프라인 캐시와 첫 설치 용량)', () => {
    const sizes = files.map((f) => statSync(join(dir, f)).size)
    for (const [i, size] of sizes.entries()) expect(size, files[i]).toBeLessThan(100 * 1024)
    expect(sizes.reduce((a, b) => a + b, 0)).toBeLessThan(300 * 1024)
  })
})

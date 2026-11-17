import settingsIcon from '../assets/icons/settings.png'

// 설정 아이콘. 이미지는 모양(투명도)만 쓰고 색은 글자색을 따른다.
export function SettingsIcon({ size = 24 }: { size?: number }) {
  return (
    <span
      aria-hidden
      className="block shrink-0 bg-current"
      style={{
        width: size,
        height: size,
        maskImage: `url(${settingsIcon})`,
        WebkitMaskImage: `url(${settingsIcon})`,
        maskSize: 'contain',
        WebkitMaskSize: 'contain',
        maskRepeat: 'no-repeat',
        WebkitMaskRepeat: 'no-repeat',
        maskPosition: 'center',
        WebkitMaskPosition: 'center',
      }}
    />
  )
}

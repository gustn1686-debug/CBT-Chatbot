import { Link } from 'react-router-dom'
import settingsIcon from '../assets/icons/settings.png'

// 홈 우측 상단의 설정 버튼. 아이콘 이미지는 모양(투명도)만 쓰고 색은 글자색을 따른다.
export function SettingsButton() {
  return (
    <Link to="/settings" aria-label="설정" className="-mr-2 flex size-11 items-center justify-center text-ink">
      <span
        aria-hidden
        className="block size-6 bg-current"
        style={{
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
    </Link>
  )
}

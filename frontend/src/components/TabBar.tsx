import { NavLink } from 'react-router-dom'
import homeIcon from '../assets/icons/tab-home.png'
import settingsIcon from '../assets/icons/tab-settings.png'

const tabs = [
  { to: '/', label: '홈', icon: homeIcon },
  { to: '/settings', label: '설정', icon: settingsIcon },
]

// 아이콘 이미지는 모양(투명도)만 쓰고 색은 탭의 글자색을 따른다. (선택된 탭은 primary, 아니면 muted)
function TabIcon({ src }: { src: string }) {
  return (
    <span
      aria-hidden
      className="block size-[22px] bg-current"
      style={{
        maskImage: `url(${src})`,
        WebkitMaskImage: `url(${src})`,
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

export function TabBar() {
  return (
    <nav className="flex justify-between bg-white px-5 pt-2.5 pb-1.5" aria-label="주요 메뉴">
      {tabs.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          end={tab.to === '/'}
          className={({ isActive }) =>
            `-mx-3 flex flex-col items-center gap-0.5 px-3 text-[10px]/[normal] ${
              isActive ? 'font-bold text-primary' : 'text-muted'
            }`
          }
        >
          <TabIcon src={tab.icon} />
          {tab.label}
        </NavLink>
      ))}
    </nav>
  )
}

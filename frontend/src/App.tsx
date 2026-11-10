import type { ReactNode } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { getSession } from './lib/session'
import { isOnboarded } from './lib/preferences'
import { About } from './pages/About'
import { Chat } from './pages/Chat'
import { Home } from './pages/Home'
import { Login } from './pages/Login'
import { Onboarding } from './pages/Onboarding'
import { RecordDetail } from './pages/RecordDetail'
import { Records } from './pages/Records'
import { Settings } from './pages/Settings'
import { Signup } from './pages/Signup'
import { Start } from './pages/Start'

// 온보딩을 마쳐야 시작 선택·로그인·가입 화면을 볼 수 있다.
function RequireOnboarding({ children }: { children: ReactNode }) {
  return isOnboarded() ? children : <Navigate to="/onboarding" replace />
}

// 앱 본 화면은 비회원이든 회원이든 세션(시작 선택 결과)이 있어야 볼 수 있다.
function RequireSession({ children }: { children: ReactNode }) {
  if (!isOnboarded()) return <Navigate to="/onboarding" replace />
  return getSession() ? children : <Navigate to="/start" replace />
}

const protectedRoutes: { path: string; element: ReactNode }[] = [
  { path: '/', element: <Home /> },
  { path: '/chat', element: <Chat /> },
  { path: '/records', element: <Records /> },
  { path: '/records/:id', element: <RecordDetail /> },
  { path: '/settings', element: <Settings /> },
  { path: '/settings/about', element: <About /> },
]

const authRoutes: { path: string; element: ReactNode }[] = [
  { path: '/start', element: <Start /> },
  { path: '/login', element: <Login /> },
  { path: '/signup', element: <Signup /> },
]

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/onboarding" element={<Onboarding />} />
        {authRoutes.map(({ path, element }) => (
          <Route key={path} path={path} element={<RequireOnboarding>{element}</RequireOnboarding>} />
        ))}
        {protectedRoutes.map(({ path, element }) => (
          <Route key={path} path={path} element={<RequireSession>{element}</RequireSession>} />
        ))}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  )
}

# Synap 프론트엔드

CBT 기반 대화형 자기 정리 도구 **Synap**의 웹(PWA) 앱. React + TypeScript + Vite + Tailwind CSS.
디자인은 Figma(상담챗봇_와이어프레임)를 기준으로 한다.

## 실행

```bash
npm install
npm run dev        # 개발 서버 (http://localhost:5173)
npm run build      # 타입 검사 + 배포용 빌드 (dist/)
npm run preview    # 빌드 결과 확인 (서비스 워커·설치·오프라인은 이쪽에서 확인)
npm test           # 단위·화면 테스트 (Vitest + Testing Library)
npm run lint       # oxlint
npm run typecheck  # tsc -b
```

## 환경 변수

`.env.example`(저장소 루트)을 참고한다.

| 변수 | 기본값 | 설명 |
|---|---|---|
| `VITE_USE_MOCK` | `true` | `false`로 두면 목업 대신 실제 API(`docs/api-spec.md`)를 호출한다 |
| `VITE_API_BASE_URL` | `/api/v1` | 실제 API 주소 |

## 백엔드 없이 확인하기 (목업)

`VITE_USE_MOCK`이 켜져 있으면 `src/api/mock*.ts`가 API를 대신한다. 화면 상태를 확인하는 입력값:

| 확인할 것 | 방법 |
|---|---|
| 위기 안내 시트·전화 연결 | 채팅에 `죽고 싶`, `죽고싶`, `자살` 중 하나를 보낸다 |
| 전송 실패·다시 시도 | 채팅 메시지에 `[실패]`를 넣는다 (처음 한 번만 실패) |
| 로그인 실패 | 비밀번호를 `wrongpass1`로 입력 |
| 이미 가입된 이메일 | 가입 이메일을 `taken@example.com`으로 입력 |
| 기록이 없는 상태 | 주소 끝에 `?mock=empty` |
| 무료 대화 소진(비회원) | 개발자 도구에서 `localStorage['synap.mock.sessionCount'] = '3'` |
| 네트워크 오류 | 개발자 도구 Network → Offline |

실제 API는 `src/api/{auth,chat}.ts`에서 호출하고, 생각 기록 API(`records.ts`)는 명세가 확정되기 전이라 목업만 있다.

## 폴더

```
src/
  api/          API 호출과 목업 (화면은 이 계층만 안다)
  components/   공통 컴포넌트 (chat/, crisis/, guest/, auth/ 포함)
  hooks/        useChat, useDialogFocus, useOnlineStatus, useDocumentTitle
  lib/          세션·설정 저장, 위기 상담 번호, 검증
  pages/        화면 (라우트 하나당 파일 하나)
  assets/       마스코트(webp), 토글 SVG
public/         아이콘(icons/), 파비콘
pwa.manifest.ts 설치 정보 (이름·아이콘·바로가기)
```

디자인 토큰(색·반경·그림자)은 `src/index.css`의 `@theme`에 모여 있다.
일부 색은 접근성(WCAG AA 4.5:1)을 위해 Figma 값보다 조금 진하게 조정했고, 이유는 해당 파일의 주석에 있다.

## PWA

- **설치**: Chrome/Edge/Android는 주소창·메뉴의 "설치", iOS Safari는 공유 → "홈 화면에 추가". 아이콘은 `public/icons/`에 있고, 지금은 마스코트로 만든 **임시 아이콘**이다. 최종 아이콘이 나오면 같은 파일명·크기로 교체하면 된다.
  `icon-192.png`, `icon-512.png`(any) · `icon-maskable-192.png`, `icon-maskable-512.png`(maskable, 가장자리 여백 포함) · `apple-touch-icon.png`(180) · `favicon-32.png`, `favicon-64.png`
- **오프라인**: 앱 화면·스크립트·이미지는 서비스 워커가 미리 저장한다. 오프라인에서도 앱이 열리고, 채팅은 "인터넷 연결을 확인해주세요" 안내와 함께 입력이 잠긴다.
  - 글꼴(Noto Sans KR)은 Google Fonts에서 받으며, 한 번 열어 본 화면의 글자만 저장된다. 오프라인에서 처음 보는 글자는 시스템 글꼴로 보일 수 있다.
- **업데이트**: 새 버전이 나와도 쓰던 화면을 강제로 새로고침하지 않는다(대화·위기 안내 중 끊김 방지). 앱을 완전히 닫았다가 다시 열면 새 버전이 적용된다.
- **이미지 용량**: 마스코트는 화면 표시 크기의 3배 이하 webp로 두었다(전체 약 120KB). `src/pwa.test.ts`가 용량 상한과 아이콘 크기를 확인한다.

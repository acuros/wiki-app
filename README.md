# Wiki App

클라이언트와 서버를 하나의 리포지토리에서 함께 관리하는 프로젝트입니다.

## 구성

향후 최상단 디렉터리를 다음과 같이 구성합니다.

```text
wiki-app/
├── client/  # React Native 앱
└── server/  # Python 서버
```

## 기술 스택

- 클라이언트: React Native
- 서버: Python

### 클라이언트

- Expo SDK 57 / React Native 0.86 / React 19.2
- TypeScript와 Expo Router
- TanStack Query와 표준 `fetch` 기반 API 계층
- Node.js 24 LTS / npm

클라이언트 개발 방법과 검증 명령은 [`client/README.md`](client/README.md)를 참고합니다.

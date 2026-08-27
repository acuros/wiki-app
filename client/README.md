# WikiApp Client

Expo SDK 57와 React Native로 만든 WikiApp 클라이언트입니다. 네이티브 프로젝트는 CNG로
생성하므로 `ios/`와 `android/`를 직접 수정하거나 커밋하지 않습니다.

## 로컬 개발

```bash
nvm use
npm ci
cp .env.example .env.local
npm run ios
```

iOS Simulator에서는 `localhost`가 개발 Mac을 가리킵니다. 실제 기기에서는
`EXPO_PUBLIC_API_URL`을 Mac의 LAN 주소로 변경해야 합니다. `EXPO_PUBLIC_*` 값은 앱 번들에
포함되므로 비밀값을 저장하면 안 됩니다.

## 구조

- `src/app`: Expo Router 화면과 layout
- `src/components`: 공용 UI 컴포넌트
- `src/config`: 환경 설정
- `src/lib/api`: HTTP 클라이언트
- `src/providers`: 전역 provider
- `src/theme`: 디자인 토큰

## 검증

```bash
npm run verify
npx expo-doctor
npx expo export --platform ios
```

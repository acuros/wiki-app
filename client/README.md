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

배포 API를 사용할 때는 `.env.example`의 Tailnet URL을 그대로 사용합니다. 실제 기기는 같은
Tailnet에 연결되어 있어야 합니다. 로컬 서버를 사용할 때만 Simulator에서는 `localhost`, 실제
기기에서는 개발 Mac의 LAN 주소로 `EXPO_PUBLIC_API_URL`을 변경합니다.

음성 입력은 앱에서 `https://transcription.joshua.kim/v1/audio/transcriptions`로 직접 요청합니다.
로컬 빌드는 `app.config.js`가 `/etc/transcription-api.env`의 `TRANSCRIPTION_API_KEY`를 읽어 앱
설정에 포함합니다. 다른 환경에서는 `.env.local`의 `EXPO_PUBLIC_TRANSCRIPTION_API_KEY`를
사용합니다. 이 키는 앱 번들에서 추출할 수 있으므로 현재의 개인용 배포에만 사용하는 전제입니다.

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

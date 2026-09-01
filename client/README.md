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

Release 앱은 별도 설정 없이 Tailnet API를 사용합니다. 실제 기기는 같은 Tailnet에 연결되어
있어야 합니다. 개발 모드에서는 `EXPO_PUBLIC_API_URL`로 API 주소를 바꿀 수 있고, 기본값은
Simulator의 `localhost:8000`입니다. `EXPO_PUBLIC_*` 값은 앱 번들에 포함되므로 비밀값을
저장하면 안 됩니다.

음성 입력은 앱에서 `https://transcription.joshua.kim/v1/audio/transcriptions`로 직접 요청합니다.
API 키는 `.env.local`의 `EXPO_PUBLIC_TRANSCRIPTION_API_KEY`에서만 읽고, 번들을 만드는 시점에
값이 있어야 하므로 release 빌드 전에도 채워두어야 합니다. 이 키는 앱 번들에서 추출할 수
있으므로 현재의 개인용 배포에만 사용하는 전제입니다.

## OTA 업데이트 (EAS Update)

App Store 배포 없이 직접 설치한 내부 배포 빌드도 Expo의 호스팅 업데이트를 받을 수 있습니다.
처음 한 번 Expo 계정으로 설정한 뒤 `preview` iOS 빌드를 설치하면, 이후
JavaScript/스타일/이미지 변경은 저장소 최상단에서 다음 명령으로 배포합니다.

```bash
make deploy-front UPDATE_MESSAGE="변경 내용"
```

이 명령은 `npm run verify`를 통과한 뒤 `preview` 채널에 iOS JavaScript 번들과 에셋만
발행합니다. 네이티브 iOS 빌드를 다시 만들지 않습니다.

최초 설정은 Expo 계정 로그인 후 한 번만 실행합니다. 이 명령은 프로젝트 ID, 업데이트 URL,
runtime version을 앱 설정에 추가합니다.

```bash
npx eas-cli@latest login
npx eas-cli@latest update:configure
npx eas-cli@latest build --platform ios --profile preview
```

`expo-updates` 또는 앱 설정 자체를 바꾸거나, 새 네이티브 모듈·iOS 권한을 추가한 경우에는
OTA로 배포할 수 없으므로 새 `preview` 빌드를 설치해야 합니다. Expo Go 개발 실행은 이 내부
배포 채널을 검증하는 대상이 아닙니다.

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

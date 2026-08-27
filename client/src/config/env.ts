const apiUrl = process.env.EXPO_PUBLIC_API_URL;

if (!apiUrl) {
  throw new Error('EXPO_PUBLIC_API_URL 환경변수가 필요합니다.');
}

export const env = {
  apiUrl: apiUrl.replace(/\/+$/, ''),
} as const;

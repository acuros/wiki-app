import Constants from 'expo-constants';

const apiUrl = process.env.EXPO_PUBLIC_API_URL;
const configuredTranscriptionKey = Constants.expoConfig?.extra?.transcriptionApiKey;
const transcriptionApiKey =
  process.env.EXPO_PUBLIC_TRANSCRIPTION_API_KEY ||
  (typeof configuredTranscriptionKey === 'string' ? configuredTranscriptionKey : '');

if (!apiUrl) {
  throw new Error('EXPO_PUBLIC_API_URL 환경변수가 필요합니다.');
}

export const env = {
  apiUrl: apiUrl.replace(/\/+$/, ''),
  transcriptionApiKey,
  transcriptionApiUrl: 'https://transcription.joshua.kim/v1/audio/transcriptions',
} as const;

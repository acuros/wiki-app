import Constants from 'expo-constants';

const RELEASE_API_URL = 'https://joshua-desktop.bagrid-corn.ts.net';
const DEVELOPMENT_API_URL = 'http://localhost:8000';
const configuredTranscriptionKey = Constants.expoConfig?.extra?.transcriptionApiKey;
const transcriptionApiKey =
  process.env.EXPO_PUBLIC_TRANSCRIPTION_API_KEY ||
  (typeof configuredTranscriptionKey === 'string' ? configuredTranscriptionKey : '');

// Release builds must be usable on a phone without inheriting a local
// development override from .env.local.
const apiUrl = __DEV__ ? process.env.EXPO_PUBLIC_API_URL || DEVELOPMENT_API_URL : RELEASE_API_URL;

export const env = {
  apiUrl: apiUrl.replace(/\/+$/, ''),
  transcriptionApiKey,
  transcriptionApiUrl: 'https://transcription.joshua.kim/v1/audio/transcriptions',
} as const;

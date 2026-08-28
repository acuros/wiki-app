process.env.EXPO_PUBLIC_API_URL = 'http://localhost:8000';
process.env.EXPO_PUBLIC_TRANSCRIPTION_API_KEY = 'test-transcription-key';

jest.mock('expo-audio', () => {
  const recorder = {
    prepareToRecordAsync: jest.fn(async () => undefined),
    record: jest.fn(),
    stop: jest.fn(async () => undefined),
    uri: 'file:///recording.m4a',
  };
  return {
    RecordingPresets: { HIGH_QUALITY: {} },
    requestRecordingPermissionsAsync: jest.fn(async () => ({ granted: true })),
    setAudioModeAsync: jest.fn(async () => undefined),
    useAudioRecorder: jest.fn(() => recorder),
  };
});

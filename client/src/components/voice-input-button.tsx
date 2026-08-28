import {
  RecordingPresets,
  requestRecordingPermissionsAsync,
  setAudioModeAsync,
  useAudioRecorder,
} from 'expo-audio';
import { useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text } from 'react-native';

import { TranscriptionError, transcribeRecording } from '@/lib/api/transcriptions';
import { colors } from '@/theme/tokens';

export type VoiceInputState = 'idle' | 'preparing' | 'recording' | 'transcribing';

type VoiceInputButtonProps = {
  disabled: boolean;
  onError: (message: string | null) => void;
  onStateChange: (state: VoiceInputState) => void;
  onTranscript: (text: string) => void;
};

function errorMessage(error: unknown) {
  if (error instanceof TranscriptionError) {
    if (error.reason === 'missing_key') return '음성 입력 키가 설정되지 않았습니다.';
    if (error.reason === 'too_large') return '녹음이 너무 깁니다. 짧게 나눠주세요.';
    if (error.reason === 'busy')
      return '음성 변환 서버가 사용 중입니다. 잠시 후 다시 시도해주세요.';
    if (error.reason === 'unauthorized') return '음성 입력 인증에 실패했습니다.';
    if (error.reason === 'invalid_audio') return '녹음된 음성을 확인할 수 없습니다.';
    if (error.reason === 'timeout') return '음성 변환 시간이 초과되었습니다.';
  }
  return '음성을 문자로 변환하지 못했습니다. 다시 시도해주세요.';
}

export function VoiceInputButton({
  disabled,
  onError,
  onStateChange,
  onTranscript,
}: VoiceInputButtonProps) {
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const [state, setState] = useState<VoiceInputState>('idle');

  const updateState = (nextState: VoiceInputState) => {
    setState(nextState);
    onStateChange(nextState);
  };

  const finish = () => {
    updateState('idle');
    void setAudioModeAsync({ allowsRecording: false }).catch(() => undefined);
  };

  const stopAndTranscribe = async () => {
    updateState('transcribing');
    try {
      await recorder.stop();
      if (!recorder.uri) {
        throw new TranscriptionError('invalid_audio');
      }
      const text = (await transcribeRecording(recorder.uri)).trim();
      if (!text) {
        onError('인식된 음성이 없습니다.');
        return;
      }
      onTranscript(text);
      onError(null);
    } catch (error) {
      onError(errorMessage(error));
    } finally {
      finish();
    }
  };

  const startRecording = async () => {
    onError(null);
    updateState('preparing');
    try {
      const permission = await requestRecordingPermissionsAsync();
      if (!permission.granted) {
        onError('음성 입력을 사용하려면 마이크 권한이 필요합니다.');
        finish();
        return;
      }
      await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
      await recorder.prepareToRecordAsync();
      recorder.record();
      updateState('recording');
    } catch {
      onError('녹음을 시작하지 못했습니다. 다시 시도해주세요.');
      finish();
    }
  };

  const isWaiting = state === 'preparing' || state === 'transcribing';
  const accessibilityLabel =
    state === 'recording'
      ? '음성 녹음 중지'
      : state === 'transcribing'
        ? '음성 변환 중'
        : state === 'preparing'
          ? '마이크 준비 중'
          : '음성 입력 시작';

  return (
    <Pressable
      accessibilityLabel={accessibilityLabel}
      accessibilityRole="button"
      disabled={disabled || isWaiting}
      onPress={() => void (state === 'recording' ? stopAndTranscribe() : startRecording())}
      style={({ pressed }) => [
        styles.button,
        state === 'recording' && styles.recordingButton,
        (disabled || isWaiting) && styles.disabled,
        pressed && styles.pressed,
      ]}
    >
      {isWaiting ? (
        <ActivityIndicator color={colors.primary} size="small" />
      ) : (
        <Text style={styles.icon}>{state === 'recording' ? '■' : '🎙'}</Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    width: 44,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 14,
    backgroundColor: colors.background,
  },
  recordingButton: {
    borderColor: colors.danger,
    backgroundColor: colors.dangerSoft,
  },
  disabled: {
    opacity: 0.5,
  },
  pressed: {
    opacity: 0.55,
  },
  icon: {
    color: colors.danger,
    fontSize: 20,
    lineHeight: 24,
  },
});

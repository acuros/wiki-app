import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { PrimaryButton } from '@/components/primary-button';
import { colors, spacing, typography } from '@/theme/tokens';

export default function HomeScreen() {
  const [message, setMessage] = useState('기본 환경이 연결되었습니다.');

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.card}>
        <Text style={styles.eyebrow}>WIKI APP</Text>
        <Text style={styles.title}>클라이언트 준비 완료</Text>
        <Text style={styles.description}>{message}</Text>
        <PrimaryButton
          label="시작하기"
          onPress={() => setMessage('첫 번째 기능을 추가할 준비가 되었습니다.')}
        />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    justifyContent: 'center',
    backgroundColor: colors.background,
    padding: spacing.lg,
  },
  card: {
    gap: spacing.md,
    padding: spacing.xl,
    borderRadius: 20,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  eyebrow: {
    ...typography.caption,
    color: colors.primary,
  },
  title: {
    ...typography.title,
    color: colors.text,
  },
  description: {
    ...typography.body,
    color: colors.textMuted,
    marginBottom: spacing.sm,
  },
});

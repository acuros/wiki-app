import Constants from 'expo-constants';
import { router } from 'expo-router';
import * as Updates from 'expo-updates';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { colors, spacing, typography } from '@/theme/tokens';

export default function SettingsScreen() {
  const appVersion = Constants.expoConfig?.version || '알 수 없음';
  const updateId = Updates.updateId || '내장 빌드';
  const updateEnvironment = Updates.channel
    ? `${Updates.channel} · runtime ${Updates.runtimeVersion || appVersion}`
    : `runtime ${Updates.runtimeVersion || appVersion}`;

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.header}>
        <Pressable
          accessibilityLabel="뒤로가기"
          accessibilityRole="button"
          hitSlop={12}
          onPress={() => router.back()}
          style={({ pressed }) => [styles.backButton, pressed && styles.pressed]}
        >
          <Text style={styles.backIcon}>‹</Text>
        </Pressable>
        <Text style={styles.title}>설정</Text>
        <View style={styles.headerSpacer} />
      </View>
      <View style={styles.content} />
      <View style={styles.versionSection}>
        <Text style={styles.version}>버전 {appVersion}</Text>
        <Text selectable style={styles.updateId}>
          실행 업데이트 {updateId}
        </Text>
        <Text style={styles.updateEnvironment}>{updateEnvironment}</Text>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    minHeight: 56,
    flexDirection: 'row',
    alignItems: 'center',
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    backgroundColor: colors.surface,
    paddingHorizontal: spacing.sm,
  },
  backButton: {
    width: 44,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pressed: {
    opacity: 0.55,
  },
  backIcon: {
    color: colors.primary,
    fontSize: 38,
    lineHeight: 40,
  },
  title: {
    ...typography.body,
    flex: 1,
    fontWeight: '700',
    textAlign: 'center',
    color: colors.text,
  },
  headerSpacer: {
    width: 44,
  },
  content: {
    flex: 1,
  },
  versionSection: {
    alignItems: 'center',
    gap: 4,
    padding: spacing.lg,
  },
  version: {
    ...typography.caption,
    color: colors.text,
    letterSpacing: 0,
  },
  updateId: {
    ...typography.caption,
    color: colors.textMuted,
    letterSpacing: 0,
  },
  updateEnvironment: {
    ...typography.caption,
    color: colors.textMuted,
    letterSpacing: 0,
  },
});

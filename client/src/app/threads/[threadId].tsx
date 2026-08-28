import { useQuery } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import { useMemo } from 'react';
import { ActivityIndicator, FlatList, Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { PrimaryButton } from '@/components/primary-button';
import { ApiError } from '@/lib/api/client';
import { getThread, ReferenceContent, ThreadEntry } from '@/lib/api/threads';
import { colors, spacing, typography } from '@/theme/tokens';

type ConversationItem = {
  key: string;
  entry: ThreadEntry;
};

const referenceLabels: Record<string, string> = {
  image: '이미지',
  local_image: '로컬 이미지',
  audio: '오디오',
  local_audio: '로컬 오디오',
  skill: '스킬',
  mention: '멘션',
};

function entryLabel(entry: ThreadEntry) {
  if (entry.type === 'user_message') {
    return '나';
  }
  if (entry.type === 'plan') {
    return '계획';
  }
  if (entry.phase === 'commentary') {
    return '진행';
  }
  return '답변';
}

function referenceTypeLabel(content: ReferenceContent) {
  return referenceLabels[content.reference_type] || content.reference_type;
}

function ConversationEntry({ entry }: { entry: ThreadEntry }) {
  const isUser = entry.type === 'user_message';
  const isPlan = entry.type === 'plan';

  return (
    <View style={[styles.entryRow, isUser && styles.userEntryRow]} testID="conversation-entry">
      <View style={[styles.bubble, isUser && styles.userBubble, isPlan && styles.planBubble]}>
        <Text style={[styles.entryLabel, isUser && styles.userText]}>{entryLabel(entry)}</Text>
        {entry.content.map((content, index) =>
          content.type === 'text' ? (
            <Text
              key={`${entry.id}-text-${index}`}
              style={[styles.message, isUser && styles.userText]}
            >
              {content.text}
            </Text>
          ) : (
            <View key={`${entry.id}-reference-${index}`} style={styles.referenceCard}>
              <Text style={styles.referenceName}>{content.name || '이름 없는 첨부'}</Text>
              <Text style={styles.referenceType}>{referenceTypeLabel(content)}</Text>
              <Text numberOfLines={2} style={styles.referenceTarget}>
                {content.target}
              </Text>
            </View>
          ),
        )}
      </View>
    </View>
  );
}

function Header({ title }: { title: string }) {
  return (
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
      <Text numberOfLines={1} style={styles.headerTitle}>
        {title}
      </Text>
      <View style={styles.headerSpacer} />
    </View>
  );
}

function DetailState({ message, retry }: { message?: string; retry?: () => void }) {
  return (
    <View style={styles.state}>
      {message ? (
        <>
          <Text style={styles.stateTitle}>{message}</Text>
          {retry ? <PrimaryButton label="다시 시도" onPress={retry} /> : null}
        </>
      ) : (
        <ActivityIndicator accessibilityLabel="대화 불러오는 중" color={colors.primary} />
      )}
    </View>
  );
}

function detailErrorMessage(error: Error) {
  if (error instanceof ApiError && error.status === 404) {
    return '스레드를 찾을 수 없습니다.';
  }
  return '대화를 불러오지 못했습니다.';
}

export default function ThreadDetailScreen() {
  const params = useLocalSearchParams<{ threadId?: string | string[] }>();
  const threadId = Array.isArray(params.threadId) ? params.threadId[0] : params.threadId;
  const query = useQuery({
    queryKey: ['thread', threadId],
    queryFn: () => getThread(threadId || ''),
    enabled: Boolean(threadId),
  });

  const items = useMemo<ConversationItem[]>(
    () =>
      query.data?.turns.flatMap((turn) =>
        turn.entries.map((entry) => ({
          key: `${turn.id}:${entry.id}`,
          entry,
        })),
      ) ?? [],
    [query.data],
  );

  if (!threadId) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <Header title="Thread" />
        <DetailState message="스레드 주소가 올바르지 않습니다." />
      </SafeAreaView>
    );
  }

  if (query.isPending) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <Header title="Thread" />
        <DetailState />
      </SafeAreaView>
    );
  }

  if (query.isError) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <Header title="Thread" />
        <DetailState message={detailErrorMessage(query.error)} retry={() => void query.refetch()} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <Header title={query.data.title || '제목 없는 스레드'} />
      <FlatList
        contentContainerStyle={[
          styles.conversation,
          items.length === 0 && styles.emptyConversation,
        ]}
        data={items}
        keyExtractor={(item) => item.key}
        ListEmptyComponent={<Text style={styles.stateTitle}>표시할 대화가 없습니다.</Text>}
        renderItem={({ item }) => <ConversationEntry entry={item.entry} />}
      />
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
  headerTitle: {
    ...typography.body,
    flex: 1,
    fontWeight: '700',
    textAlign: 'center',
    color: colors.text,
  },
  headerSpacer: {
    width: 44,
  },
  conversation: {
    gap: spacing.md,
    padding: spacing.md,
  },
  emptyConversation: {
    flexGrow: 1,
    justifyContent: 'center',
  },
  entryRow: {
    flexDirection: 'row',
    justifyContent: 'flex-start',
  },
  userEntryRow: {
    justifyContent: 'flex-end',
  },
  bubble: {
    maxWidth: '86%',
    gap: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 16,
    borderBottomLeftRadius: 4,
    backgroundColor: colors.surface,
    padding: spacing.md,
  },
  userBubble: {
    borderColor: colors.primary,
    borderBottomLeftRadius: 16,
    borderBottomRightRadius: 4,
    backgroundColor: colors.primary,
  },
  planBubble: {
    borderColor: colors.primarySoft,
    backgroundColor: colors.primarySoft,
  },
  entryLabel: {
    ...typography.caption,
    color: colors.primary,
    letterSpacing: 0,
  },
  message: {
    ...typography.body,
    color: colors.text,
  },
  userText: {
    color: colors.onPrimary,
  },
  referenceCard: {
    gap: 4,
    borderRadius: 10,
    backgroundColor: colors.surfaceMuted,
    padding: spacing.sm,
  },
  referenceName: {
    ...typography.caption,
    color: colors.text,
    letterSpacing: 0,
  },
  referenceType: {
    ...typography.caption,
    color: colors.primary,
    letterSpacing: 0,
  },
  referenceTarget: {
    ...typography.caption,
    color: colors.textMuted,
    letterSpacing: 0,
  },
  state: {
    flex: 1,
    justifyContent: 'center',
    gap: spacing.md,
    padding: spacing.lg,
  },
  stateTitle: {
    ...typography.body,
    fontWeight: '700',
    textAlign: 'center',
    color: colors.text,
  },
});

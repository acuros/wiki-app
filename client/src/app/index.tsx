import { useInfiniteQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useMemo } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { PrimaryButton } from '@/components/primary-button';
import { getThreads, ThreadSummary } from '@/lib/api/threads';
import { colors, spacing, typography } from '@/theme/tokens';

const PAGE_SIZE = 50;
const recencyFormatter = new Intl.DateTimeFormat('ko-KR', {
  month: 'short',
  day: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
});

function formatRecency(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '' : recencyFormatter.format(date);
}

function statusPresentation(status: string) {
  if (status === 'active') {
    return { label: '진행 중', error: false };
  }
  if (status === 'system_error') {
    return { label: '오류', error: true };
  }
  return null;
}

function ThreadCard({ thread }: { thread: ThreadSummary }) {
  const title = thread.title || '제목 없는 스레드';
  const status = statusPresentation(thread.status);

  return (
    <Pressable
      accessibilityLabel={`스레드 열기: ${title}`}
      accessibilityRole="button"
      onPress={() =>
        router.push({
          pathname: './threads/[threadId]',
          params: { threadId: thread.id },
        })
      }
      style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
    >
      <View style={styles.cardHeading}>
        <Text numberOfLines={1} style={styles.cardTitle}>
          {title}
        </Text>
        {status ? (
          <View style={[styles.status, status.error && styles.errorStatus]}>
            <Text style={[styles.statusText, status.error && styles.errorStatusText]}>
              {status.label}
            </Text>
          </View>
        ) : null}
      </View>
      <Text numberOfLines={2} style={styles.preview}>
        {thread.preview}
      </Text>
      <Text style={styles.recency}>{formatRecency(thread.recency_at)}</Text>
    </Pressable>
  );
}

function InitialState({ error, retry }: { error: boolean; retry: () => void }) {
  return (
    <View style={styles.initialState}>
      {error ? (
        <>
          <Text style={styles.stateTitle}>스레드 목록을 불러오지 못했습니다.</Text>
          <Text style={styles.stateDescription}>네트워크 연결을 확인하고 다시 시도해주세요.</Text>
          <PrimaryButton label="다시 시도" onPress={retry} />
        </>
      ) : (
        <ActivityIndicator accessibilityLabel="스레드 목록 불러오는 중" color={colors.primary} />
      )}
    </View>
  );
}

export default function HomeScreen() {
  const query = useInfiniteQuery({
    queryKey: ['threads'],
    initialPageParam: null as string | null,
    queryFn: ({ pageParam }) =>
      getThreads({
        archived: false,
        cursor: pageParam ?? undefined,
        limit: PAGE_SIZE,
      }),
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
  });

  const threads = useMemo(() => {
    const seen = new Set<string>();
    return (
      query.data?.pages.flatMap((page) =>
        page.threads.filter((thread) => {
          if (seen.has(thread.id)) {
            return false;
          }
          seen.add(thread.id);
          return true;
        }),
      ) ?? []
    );
  }, [query.data]);

  const retry = () => {
    void query.refetch();
  };

  if (query.isPending || query.isError) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.header}>
          <Text style={styles.eyebrow}>WIKI APP</Text>
          <Text style={styles.title}>Threads</Text>
        </View>
        <InitialState error={query.isError} retry={retry} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <FlatList
        contentContainerStyle={[styles.listContent, threads.length === 0 && styles.emptyList]}
        data={threads}
        keyExtractor={(thread) => thread.id}
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <Text style={styles.stateTitle}>표시할 스레드가 없습니다.</Text>
            <Text style={styles.stateDescription}>새 스레드가 생기면 여기에 표시됩니다.</Text>
          </View>
        }
        ListFooterComponent={
          query.hasNextPage ? (
            <View style={styles.footer}>
              <PrimaryButton
                disabled={query.isFetchingNextPage}
                label={query.isFetchingNextPage ? '불러오는 중...' : '더 보기'}
                onPress={() => void query.fetchNextPage()}
              />
            </View>
          ) : null
        }
        ListHeaderComponent={
          <View style={styles.header}>
            <Text style={styles.eyebrow}>WIKI APP</Text>
            <Text style={styles.title}>Threads</Text>
          </View>
        }
        refreshControl={
          <RefreshControl
            onRefresh={retry}
            refreshing={query.isRefetching && !query.isFetchingNextPage}
            tintColor={colors.primary}
          />
        }
        renderItem={({ item }) => <ThreadCard thread={item} />}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: colors.background,
  },
  listContent: {
    gap: spacing.md,
    padding: spacing.lg,
  },
  emptyList: {
    flexGrow: 1,
  },
  header: {
    gap: spacing.sm,
    marginBottom: spacing.sm,
  },
  card: {
    gap: spacing.sm,
    padding: spacing.md,
    borderRadius: 16,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  cardPressed: {
    opacity: 0.75,
  },
  cardHeading: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  cardTitle: {
    ...typography.body,
    flex: 1,
    fontWeight: '700',
    color: colors.text,
  },
  eyebrow: {
    ...typography.caption,
    color: colors.primary,
  },
  title: {
    ...typography.title,
    color: colors.text,
  },
  preview: {
    ...typography.body,
    fontSize: 13,
    lineHeight: 18,
    color: colors.textMuted,
  },
  recency: {
    ...typography.caption,
    color: colors.textMuted,
    letterSpacing: 0,
  },
  status: {
    borderRadius: 999,
    backgroundColor: colors.primarySoft,
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
  },
  errorStatus: {
    backgroundColor: colors.dangerSoft,
  },
  statusText: {
    ...typography.caption,
    color: colors.primary,
    letterSpacing: 0,
  },
  errorStatusText: {
    color: colors.danger,
  },
  initialState: {
    flex: 1,
    justifyContent: 'center',
    gap: spacing.md,
    padding: spacing.lg,
  },
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    gap: spacing.sm,
  },
  stateTitle: {
    ...typography.body,
    fontWeight: '700',
    textAlign: 'center',
    color: colors.text,
  },
  stateDescription: {
    ...typography.body,
    textAlign: 'center',
    color: colors.textMuted,
  },
  footer: {
    marginTop: spacing.sm,
  },
});

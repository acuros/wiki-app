import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useMemo, useRef, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { PrimaryButton } from '@/components/primary-button';
import { VoiceInputButton, VoiceInputState } from '@/components/voice-input-button';
import { ApiError } from '@/lib/api/client';
import {
  createThread,
  getThread,
  ReasoningEffort,
  ReferenceContent,
  sendMessage,
  ThreadDetail,
  ThreadEntry,
  ThreadModel,
  updateThreadSettings,
} from '@/lib/api/threads';
import { colors, spacing, typography } from '@/theme/tokens';

const POLL_INTERVAL_MS = 1_500;

type ConversationItem = {
  key: string;
  entry: ThreadEntry;
};

type ThreadConversationProps = {
  threadId?: string;
  onClose?: () => void;
};

type SettingsMenu = 'root' | 'model' | 'reasoning' | null;

const modelOptions: { label: string; value: ThreadModel }[] = [
  { label: 'Luna', value: 'gpt-5.6-luna' },
  { label: 'Terra', value: 'gpt-5.6-terra' },
  { label: 'Sol', value: 'gpt-5.6-sol' },
];

const reasoningOptions: { label: string; value: ReasoningEffort }[] = [
  { label: 'None', value: 'none' },
  { label: 'Low', value: 'low' },
  { label: 'Medium', value: 'medium' },
  { label: 'High', value: 'high' },
  { label: 'Extra high', value: 'xhigh' },
];

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

function Header({ onClose, title }: { onClose?: () => void; title: string }) {
  return (
    <View style={styles.header}>
      <Pressable
        accessibilityLabel="뒤로가기"
        accessibilityRole="button"
        hitSlop={12}
        onPress={() => onClose?.() ?? router.back()}
        style={({ pressed }) => [styles.backButton, pressed && styles.pressed]}
      >
        <Text style={styles.backIcon}>‹</Text>
      </Pressable>
      <Text numberOfLines={1} style={styles.headerTitle}>
        {title}
      </Text>
      {onSettingsPress ? (
        <Pressable
          accessibilityLabel="스레드 설정"
          accessibilityRole="button"
          hitSlop={12}
          onPress={onSettingsPress}
          style={({ pressed }) => [styles.settingsButton, pressed && styles.pressed]}
        >
          <Text style={styles.settingsIcon}>⋯</Text>
        </Pressable>
      ) : (
        <View style={styles.headerSpacer} />
      )}
    </View>
  );
}

function SettingsMenuPanel({
  error,
  menu,
  onClose,
  onSelect,
}: {
  error: string | null;
  menu: SettingsMenu;
  onClose: () => void;
  onSelect: (settings: { model?: ThreadModel; effort?: ReasoningEffort }) => void;
}) {
  if (!menu) {
    return null;
  }

  const options =
    menu === 'model'
      ? modelOptions.map((option) => ({
          ...option,
          onPress: () => onSelect({ model: option.value }),
        }))
      : menu === 'reasoning'
        ? reasoningOptions.map((option) => ({
            ...option,
            onPress: () => onSelect({ effort: option.value }),
          }))
        : [];

  return (
    <View accessibilityViewIsModal style={styles.settingsMenu}>
      {menu === 'root' ? (
        <>
          <Pressable
            accessibilityRole="button"
            onPress={() => onSelect({})}
            style={styles.menuItem}
          >
            <Text style={styles.menuItemText}>모델</Text>
          </Pressable>
          <Pressable
            accessibilityRole="button"
            onPress={() => onSelect({ effort: undefined })}
            style={styles.menuItem}
          >
            <Text style={styles.menuItemText}>Reasoning</Text>
          </Pressable>
        </>
      ) : (
        <>
          <Pressable
            accessibilityRole="button"
            onPress={() => onSelect({ model: undefined })}
            style={styles.menuBackItem}
          >
            <Text style={styles.menuBackText}>‹ 설정</Text>
          </Pressable>
          {options.map((option) => (
            <Pressable
              accessibilityLabel={option.label}
              accessibilityRole="button"
              key={option.value}
              onPress={option.onPress}
              style={styles.menuItem}
            >
              <Text style={styles.menuItemText}>{option.label}</Text>
            </Pressable>
          ))}
        </>
      )}
      {error ? <Text style={styles.settingsError}>{error}</Text> : null}
      <Pressable
        accessibilityLabel="설정 메뉴 닫기"
        accessibilityRole="button"
        onPress={onClose}
        style={styles.menuClose}
      >
        <Text style={styles.menuCloseText}>닫기</Text>
      </Pressable>
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

function submissionErrorMessage(error: Error) {
  if (error instanceof ApiError && error.status === 409) {
    return '현재 답변이 끝난 뒤 다시 보내주세요.';
  }
  if (error instanceof ApiError && error.status === 404) {
    return '스레드를 찾을 수 없습니다.';
  }
  if (error instanceof ApiError && error.status === 503) {
    return 'Codex에 연결할 수 없습니다.';
  }
  return '메시지를 보내지 못했습니다. 다시 시도해주세요.';
}

export function ThreadConversation({ onClose, threadId }: ThreadConversationProps) {
  const [activeThreadId, setActiveThreadId] = useState(threadId);
  const isNew = activeThreadId === undefined;
  const queryClient = useQueryClient();
  const listRef = useRef<FlatList<ConversationItem>>(null);
  const submissionInFlightRef = useRef(false);
  const [draft, setDraft] = useState('');
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [voiceState, setVoiceState] = useState<VoiceInputState>('idle');
  const [settingsMenu, setSettingsMenu] = useState<SettingsMenu>(null);
  const [settingsError, setSettingsError] = useState<string | null>(null);
  const query = useQuery({
    queryKey: ['thread', activeThreadId],
    queryFn: () => getThread(activeThreadId || ''),
    enabled: !isNew && Boolean(activeThreadId),
    refetchInterval: (currentQuery) =>
      currentQuery.state.data?.status === 'active' ? POLL_INTERVAL_MS : false,
  });

  const mutation = useMutation({
    mutationFn: (message: string) =>
      isNew ? createThread(message) : sendMessage(activeThreadId || '', message),
    onSuccess: (submission) => {
      setDraft('');
      void queryClient.invalidateQueries({ queryKey: ['threads'] });
      if (isNew) {
        setActiveThreadId(submission.thread_id);
        return;
      }
      queryClient.setQueryData<ThreadDetail>(['thread', activeThreadId], (current) =>
        current ? { ...current, status: 'active' } : current,
      );
      void queryClient.invalidateQueries({ queryKey: ['thread', activeThreadId] });
    },
    onSettled: () => {
      submissionInFlightRef.current = false;
    },
  });
  const settingsMutation = useMutation({
    mutationFn: (settings: { model?: ThreadModel; effort?: ReasoningEffort }) =>
      updateThreadSettings(activeThreadId || '', settings),
    onSuccess: () => {
      setSettingsMenu(null);
      setSettingsError(null);
    },
    onError: () => setSettingsError('설정을 변경하지 못했습니다. 다시 시도해주세요.'),
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

  if (!isNew && !activeThreadId) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <Header onClose={onClose} title="Thread" />
        <DetailState message="스레드 주소가 올바르지 않습니다." />
      </SafeAreaView>
    );
  }

  if (!isNew && query.isPending) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <Header onClose={onClose} title="Thread" />
        <DetailState />
      </SafeAreaView>
    );
  }

  if (!isNew && query.isError && !query.data) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <Header onClose={onClose} title="Thread" />
        <DetailState message={detailErrorMessage(query.error)} retry={() => void query.refetch()} />
      </SafeAreaView>
    );
  }

  const isActive = query.data?.status === 'active';
  const isSubmitting = mutation.isPending;
  const isUsingVoice = voiceState !== 'idle';
  const submissionError = mutation.error ? submissionErrorMessage(mutation.error) : null;
  const emptyMessage = isNew ? '첫 메시지를 입력해주세요.' : '표시할 대화가 없습니다.';
  const title = isNew ? '새 Thread' : query.data?.title || '제목 없는 스레드';
  const submit = () => {
    if (
      !draft.trim() ||
      isActive ||
      isSubmitting ||
      isUsingVoice ||
      submissionInFlightRef.current
    ) {
      return;
    }
    submissionInFlightRef.current = true;
    mutation.mutate(draft);
  };
  const appendTranscript = (text: string) => {
    setDraft((current) => `${current}${current && !/\s$/.test(current) ? ' ' : ''}${text}`);
  };
  const composerDisabled = isActive || isSubmitting || isUsingVoice;
  const selectSettings = (settings: { model?: ThreadModel; effort?: ReasoningEffort }) => {
    if ('model' in settings && settings.model === undefined) {
      setSettingsMenu('root');
      return;
    }
    if ('effort' in settings && settings.effort === undefined) {
      setSettingsMenu('reasoning');
      return;
    }
    if (!settings.model && !settings.effort) {
      setSettingsMenu('model');
      return;
    }
    settingsMutation.mutate(settings);
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <Header onClose={onClose} onSettingsPress={() => setSettingsMenu('root')} title={title} />
      <SettingsMenuPanel
        error={settingsError}
        menu={settingsMenu}
        onClose={() => {
          setSettingsMenu(null);
          setSettingsError(null);
        }}
        onSelect={selectSettings}
      />
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.keyboardAvoidingView}
      >
        <FlatList
          contentContainerStyle={[
            styles.conversation,
            items.length === 0 && styles.emptyConversation,
          ]}
          data={items}
          keyExtractor={(item) => item.key}
          ListEmptyComponent={<Text style={styles.stateTitle}>{emptyMessage}</Text>}
          onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: true })}
          ref={listRef}
          renderItem={({ item }) => <ConversationEntry entry={item.entry} />}
          testID="conversation-list"
        />
        <View style={styles.composer}>
          {query.isError && query.data ? (
            <Text style={styles.errorText}>대화를 갱신하지 못했습니다.</Text>
          ) : null}
          {submissionError ? <Text style={styles.errorText}>{submissionError}</Text> : null}
          {voiceError ? <Text style={styles.errorText}>{voiceError}</Text> : null}
          {isActive ? <Text style={styles.progressText}>답변 작성 중...</Text> : null}
          {voiceState === 'preparing' ? (
            <Text style={styles.progressText}>마이크 준비 중...</Text>
          ) : null}
          {voiceState === 'recording' ? (
            <Text style={styles.progressText}>녹음 중... 마이크 버튼을 다시 눌러 완료하세요.</Text>
          ) : null}
          {voiceState === 'transcribing' ? (
            <Text style={styles.progressText}>음성을 문자로 변환하는 중...</Text>
          ) : null}
          <View style={styles.composerRow}>
            <TextInput
              accessibilityLabel="메시지 입력"
              editable={!composerDisabled}
              multiline
              onChangeText={setDraft}
              placeholder="메시지를 입력하세요"
              placeholderTextColor={colors.textMuted}
              style={[styles.input, composerDisabled && styles.inputDisabled]}
              value={draft}
            />
            <VoiceInputButton
              disabled={isActive || isSubmitting}
              onError={setVoiceError}
              onStateChange={setVoiceState}
              onTranscript={appendTranscript}
            />
            <Pressable
              accessibilityLabel="메시지 보내기"
              accessibilityRole="button"
              disabled={!draft.trim() || composerDisabled}
              onPress={submit}
              style={({ pressed }) => [
                styles.sendButton,
                (!draft.trim() || composerDisabled) && styles.sendButtonDisabled,
                pressed && styles.pressed,
              ]}
            >
              {isSubmitting ? (
                <ActivityIndicator color={colors.onPrimary} size="small" />
              ) : (
                <Text style={styles.sendButtonText}>↑</Text>
              )}
            </Pressable>
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: colors.background,
  },
  keyboardAvoidingView: {
    flex: 1,
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
  settingsButton: {
    width: 44,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  settingsIcon: {
    color: colors.primary,
    fontSize: 27,
    lineHeight: 27,
    marginTop: -8,
  },
  settingsMenu: {
    position: 'absolute',
    zIndex: 10,
    top: 56,
    right: spacing.sm,
    minWidth: 180,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 12,
    backgroundColor: colors.surface,
    paddingVertical: spacing.sm,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.16,
    shadowRadius: 8,
    elevation: 6,
  },
  menuItem: {
    paddingHorizontal: spacing.md,
    paddingVertical: 12,
  },
  menuItemText: {
    ...typography.body,
    color: colors.text,
  },
  menuBackItem: {
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
  },
  menuBackText: {
    ...typography.caption,
    color: colors.primary,
    letterSpacing: 0,
  },
  menuClose: {
    borderTopWidth: 1,
    borderTopColor: colors.border,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
  },
  menuCloseText: {
    ...typography.caption,
    color: colors.textMuted,
    letterSpacing: 0,
  },
  settingsError: {
    ...typography.caption,
    color: colors.danger,
    letterSpacing: 0,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  conversation: {
    flexGrow: 1,
    gap: spacing.md,
    padding: spacing.md,
  },
  emptyConversation: {
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
  composer: {
    gap: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    backgroundColor: colors.surface,
    padding: spacing.md,
  },
  composerRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: spacing.sm,
  },
  input: {
    ...typography.body,
    minHeight: 44,
    maxHeight: 132,
    flex: 1,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 14,
    backgroundColor: colors.background,
    color: colors.text,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
  },
  inputDisabled: {
    opacity: 0.6,
  },
  sendButton: {
    width: 44,
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 14,
    backgroundColor: colors.primary,
  },
  sendButtonDisabled: {
    opacity: 0.45,
  },
  sendButtonText: {
    fontSize: 24,
    lineHeight: 28,
    color: colors.onPrimary,
  },
  progressText: {
    ...typography.caption,
    color: colors.primary,
    letterSpacing: 0,
  },
  errorText: {
    ...typography.caption,
    color: colors.danger,
    letterSpacing: 0,
  },
});

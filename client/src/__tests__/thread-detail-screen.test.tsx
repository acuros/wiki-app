import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, fireEvent, render, waitFor, within } from '@testing-library/react-native';
import { PropsWithChildren } from 'react';

import ThreadDetailScreen from '@/app/threads/[threadId]';
import { ApiError } from '@/lib/api/client';
import { getThread, sendMessage, TurnSubmission } from '@/lib/api/threads';

jest.mock('expo-router', () => ({
  router: {
    back: jest.fn(),
    replace: jest.fn(),
  },
  useLocalSearchParams: jest.fn(() => ({ threadId: 'thread-1' })),
}));

jest.mock('@/lib/api/threads', () => ({
  createThread: jest.fn(),
  getThread: jest.fn(),
  sendMessage: jest.fn(),
}));

const mockGetThread = getThread as jest.MockedFunction<typeof getThread>;
const mockSendMessage = sendMessage as jest.MockedFunction<typeof sendMessage>;
const mockRouter = jest.requireMock('expo-router').router as {
  back: jest.Mock;
};

const detail = {
  id: 'thread-1',
  title: 'Thread title',
  preview: 'Preview',
  source: 'app_server' as const,
  cwd: '/workspace',
  project_id: null,
  created_at: '2026-08-27T10:00:00Z',
  updated_at: '2026-08-27T11:00:00Z',
  recency_at: '2026-08-27T11:00:00Z',
  status: 'idle' as const,
  active_flags: [],
  turns: [
    {
      id: 'turn-1',
      status: 'completed',
      started_at: '2026-08-27T10:00:00Z',
      completed_at: '2026-08-27T11:00:00Z',
      duration_ms: 1000,
      omitted_item_count: 3,
      omitted_item_types: ['reasoning'],
      entries: [
        {
          id: 'user-1',
          type: 'user_message' as const,
          content: [
            { type: 'text' as const, text: 'First user message' },
            {
              type: 'reference' as const,
              reference_type: 'mention',
              target: '/workspace/AGENTS.md',
              name: 'AGENTS.md',
            },
          ],
        },
        {
          id: 'assistant-1',
          type: 'assistant_message' as const,
          phase: 'commentary',
          content: [{ type: 'text' as const, text: 'Assistant progress' }],
        },
        {
          id: 'assistant-2',
          type: 'assistant_message' as const,
          phase: 'final_answer',
          content: [{ type: 'text' as const, text: 'Assistant answer' }],
        },
        {
          id: 'plan-1',
          type: 'plan' as const,
          content: [{ type: 'text' as const, text: 'Implementation plan' }],
        },
      ],
    },
  ],
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false, gcTime: 0 },
    },
  });

  return function Wrapper({ children }: PropsWithChildren) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe('ThreadDetailScreen', () => {
  beforeEach(() => {
    mockGetThread.mockReset();
    mockSendMessage.mockReset();
    mockRouter.back.mockReset();
  });

  it('renders conversation entries in order with phase and reference labels', async () => {
    mockGetThread.mockResolvedValue(detail);

    const screen = await render(<ThreadDetailScreen />, { wrapper: createWrapper() });

    expect(await screen.findByText('Thread title')).toBeTruthy();
    const entries = screen.getAllByTestId('conversation-entry');
    expect(entries).toHaveLength(4);
    expect(within(entries[0]).getByText('나')).toBeTruthy();
    expect(within(entries[0]).getByText('First user message')).toBeTruthy();
    expect(within(entries[0]).getByText('AGENTS.md')).toBeTruthy();
    expect(within(entries[0]).getByText('멘션')).toBeTruthy();
    expect(within(entries[0]).getByText('/workspace/AGENTS.md')).toBeTruthy();
    expect(within(entries[1]).getByText('진행')).toBeTruthy();
    expect(within(entries[1]).getByText('Assistant progress')).toBeTruthy();
    expect(within(entries[2]).getByText('답변')).toBeTruthy();
    expect(within(entries[3]).getByText('계획')).toBeTruthy();
    expect(screen.queryByText('reasoning')).toBeNull();

    await fireEvent.press(screen.getByRole('button', { name: '뒤로가기' }));
    expect(mockRouter.back).toHaveBeenCalledTimes(1);
  });

  it('shows a not-found error and retries', async () => {
    mockGetThread
      .mockRejectedValueOnce(new ApiError('missing', 404))
      .mockResolvedValueOnce({ ...detail, title: null, turns: [] });

    const screen = await render(<ThreadDetailScreen />, { wrapper: createWrapper() });

    expect(await screen.findByText('스레드를 찾을 수 없습니다.')).toBeTruthy();
    await fireEvent.press(screen.getByRole('button', { name: '다시 시도' }));
    expect(await screen.findByText('제목 없는 스레드')).toBeTruthy();
    expect(screen.getByText('표시할 대화가 없습니다.')).toBeTruthy();
  });

  it('sends a message, clears the draft, and refreshes the conversation', async () => {
    mockGetThread.mockResolvedValue(detail);
    let resolveSubmission: (submission: TurnSubmission) => void = () => undefined;
    mockSendMessage.mockReturnValue(
      new Promise((resolve) => {
        resolveSubmission = resolve;
      }),
    );

    const screen = await render(<ThreadDetailScreen />, { wrapper: createWrapper() });
    const input = await screen.findByLabelText('메시지 입력');

    await fireEvent.changeText(input, 'Follow up');
    const sendButton = screen.getByRole('button', { name: '메시지 보내기' });
    await waitFor(() =>
      expect(sendButton.props.accessibilityState).toEqual(
        expect.objectContaining({ disabled: false }),
      ),
    );
    await fireEvent.press(sendButton);
    await fireEvent.press(sendButton);
    expect(mockSendMessage).toHaveBeenCalledTimes(1);

    await act(async () => {
      resolveSubmission({
        thread_id: 'thread-1',
        turn_id: 'turn-2',
        status: 'in_progress',
      });
    });

    await waitFor(() => expect(mockSendMessage).toHaveBeenCalledWith('thread-1', 'Follow up'));
    await waitFor(() => expect(screen.getByLabelText('메시지 입력').props.value).toBe(''));
    expect(mockGetThread.mock.calls.length).toBeGreaterThan(1);
  });

  it('keeps the draft and shows a conflict when submission fails', async () => {
    mockGetThread.mockResolvedValue(detail);
    mockSendMessage.mockRejectedValue(new ApiError('busy', 409));

    const screen = await render(<ThreadDetailScreen />, { wrapper: createWrapper() });
    const input = await screen.findByLabelText('메시지 입력');

    await fireEvent.changeText(input, 'Try later');
    const sendButton = screen.getByRole('button', { name: '메시지 보내기' });
    await waitFor(() =>
      expect(sendButton.props.accessibilityState).toEqual(
        expect.objectContaining({ disabled: false }),
      ),
    );
    await fireEvent.press(sendButton);

    expect(await screen.findByText('현재 답변이 끝난 뒤 다시 보내주세요.')).toBeTruthy();
    expect(screen.getByLabelText('메시지 입력').props.value).toBe('Try later');
  });

  it('disables composing while a turn is active', async () => {
    mockGetThread.mockResolvedValue({ ...detail, status: 'active' });

    const screen = await render(<ThreadDetailScreen />, { wrapper: createWrapper() });

    expect(await screen.findByText('답변 작성 중...')).toBeTruthy();
    expect(screen.getByLabelText('메시지 입력').props.editable).toBe(false);
    expect(screen.getByRole('button', { name: '메시지 보내기' }).props.accessibilityState).toEqual(
      expect.objectContaining({ disabled: true }),
    );
  });

  it('polls while active and stops after the thread becomes idle', async () => {
    jest.useFakeTimers();
    mockGetThread
      .mockResolvedValueOnce({ ...detail, status: 'active' })
      .mockResolvedValue({ ...detail, status: 'idle' });

    const screen = await render(<ThreadDetailScreen />, { wrapper: createWrapper() });
    expect(await screen.findByText('답변 작성 중...')).toBeTruthy();

    await act(async () => {
      jest.advanceTimersByTime(1_500);
    });
    expect(mockGetThread).toHaveBeenCalledTimes(2);

    await act(async () => {
      jest.advanceTimersByTime(3_000);
    });
    expect(mockGetThread).toHaveBeenCalledTimes(2);
    jest.useRealTimers();
  });
});

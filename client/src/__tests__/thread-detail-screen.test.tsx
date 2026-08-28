import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, within } from '@testing-library/react-native';
import { PropsWithChildren } from 'react';

import ThreadDetailScreen from '@/app/threads/[threadId]';
import { ApiError } from '@/lib/api/client';
import { getThread } from '@/lib/api/threads';

jest.mock('expo-router', () => ({
  router: {
    back: jest.fn(),
  },
  useLocalSearchParams: jest.fn(() => ({ threadId: 'thread-1' })),
}));

jest.mock('@/lib/api/threads', () => ({
  getThread: jest.fn(),
}));

const mockGetThread = getThread as jest.MockedFunction<typeof getThread>;
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
    },
  });

  return function Wrapper({ children }: PropsWithChildren) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe('ThreadDetailScreen', () => {
  beforeEach(() => {
    mockGetThread.mockReset();
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
});

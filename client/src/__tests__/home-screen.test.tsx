import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, fireEvent, render } from '@testing-library/react-native';
import { PropsWithChildren } from 'react';

import HomeScreen from '@/app/index';
import { ApiError } from '@/lib/api/client';
import { getThreads } from '@/lib/api/threads';

jest.mock('expo-router', () => ({
  router: {
    push: jest.fn(),
  },
}));

jest.mock('@/lib/api/threads', () => ({
  getThreads: jest.fn(),
}));

const mockGetThreads = getThreads as jest.MockedFunction<typeof getThreads>;
const mockRouter = jest.requireMock('expo-router').router as {
  push: jest.Mock;
};

const thread = {
  id: 'thread-1',
  title: 'Thread title',
  preview: 'The latest conversation preview',
  source: 'app_server' as const,
  cwd: '/workspace',
  project_id: null,
  created_at: '2026-08-27T10:00:00Z',
  updated_at: '2026-08-27T11:00:00Z',
  recency_at: '2026-08-27T11:00:00Z',
  status: 'active' as const,
  active_flags: [],
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

describe('HomeScreen', () => {
  beforeEach(() => {
    mockGetThreads.mockReset();
    mockRouter.push.mockReset();
  });

  it('renders threads, a title fallback, status, and opens a detail route', async () => {
    mockGetThreads.mockResolvedValue({
      threads: [thread, { ...thread, id: 'thread-2', title: null, status: 'not_loaded' }],
      next_cursor: null,
    });

    const screen = await render(<HomeScreen />, { wrapper: createWrapper() });

    expect(await screen.findByText('Thread title')).toBeTruthy();
    expect(screen.getByText('제목 없는 스레드')).toBeTruthy();
    expect(screen.getByText('진행 중')).toBeTruthy();
    expect(screen.getByText('+')).toBeTruthy();
    expect(screen.queryByText('not_loaded')).toBeNull();

    await fireEvent.press(screen.getByRole('button', { name: '설정 열기' }));
    expect(mockRouter.push).toHaveBeenCalledWith('/settings');

    await fireEvent.press(screen.getByRole('button', { name: '스레드 열기: Thread title' }));
    expect(mockRouter.push).toHaveBeenCalledWith({
      pathname: './threads/[threadId]',
      params: { threadId: 'thread-1' },
    });

    await fireEvent.press(screen.getByRole('button', { name: '새 Thread 시작하기' }));
    expect(screen.getByText('새 Thread')).toBeTruthy();
    expect(mockRouter.push).not.toHaveBeenCalledWith('/threads/new');
  });

  it('shows an empty state', async () => {
    mockGetThreads.mockResolvedValue({ threads: [], next_cursor: null });

    const screen = await render(<HomeScreen />, { wrapper: createWrapper() });

    expect(await screen.findByText('표시할 스레드가 없습니다.')).toBeTruthy();
  });

  it('retries a failed request', async () => {
    mockGetThreads
      .mockRejectedValueOnce(new ApiError('failed', 503))
      .mockResolvedValueOnce({ threads: [thread], next_cursor: null });

    const screen = await render(<HomeScreen />, { wrapper: createWrapper() });

    expect(await screen.findByText('스레드 목록을 불러오지 못했습니다.')).toBeTruthy();
    await fireEvent.press(screen.getByRole('button', { name: '다시 시도' }));
    expect(await screen.findByText('Thread title')).toBeTruthy();
  });

  it('loads the next page and removes duplicate threads', async () => {
    mockGetThreads
      .mockResolvedValueOnce({ threads: [thread], next_cursor: 'next cursor' })
      .mockResolvedValueOnce({
        threads: [thread, { ...thread, id: 'thread-2', title: 'Second thread' }],
        next_cursor: null,
      });

    const screen = await render(<HomeScreen />, { wrapper: createWrapper() });

    expect(await screen.findByText('Thread title')).toBeTruthy();
    expect(mockGetThreads).toHaveBeenNthCalledWith(1, {
      archived: false,
      cursor: undefined,
      limit: 20,
    });
    const list = screen.getByTestId('thread-list');
    await act(async () => {
      list.props.onEndReached();
      list.props.onEndReached();
    });

    expect(mockGetThreads).toHaveBeenCalledTimes(2);
    expect(await screen.findByText('Second thread')).toBeTruthy();
    expect(screen.getAllByText('Thread title')).toHaveLength(1);
    expect(mockGetThreads).toHaveBeenNthCalledWith(2, {
      archived: false,
      cursor: 'next cursor',
      limit: 20,
    });
  });

  it('keeps the current list and retries a failed next page', async () => {
    mockGetThreads
      .mockResolvedValueOnce({ threads: [thread], next_cursor: 'next cursor' })
      .mockRejectedValueOnce(new ApiError('failed', 503))
      .mockResolvedValueOnce({
        threads: [{ ...thread, id: 'thread-2', title: 'Second thread' }],
        next_cursor: null,
      });

    const screen = await render(<HomeScreen />, { wrapper: createWrapper() });

    expect(await screen.findByText('Thread title')).toBeTruthy();
    await fireEvent(screen.getByTestId('thread-list'), 'endReached');
    await fireEvent.press(await screen.findByRole('button', { name: '다음 목록 다시 시도' }));

    expect(await screen.findByText('Second thread')).toBeTruthy();
    expect(screen.getByText('Thread title')).toBeTruthy();
  });
});

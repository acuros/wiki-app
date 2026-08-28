import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import { PropsWithChildren } from 'react';

import NewThreadScreen from '@/app/threads/new';
import { ApiError } from '@/lib/api/client';
import { createThread } from '@/lib/api/threads';

jest.mock('expo-router', () => ({
  router: {
    back: jest.fn(),
    replace: jest.fn(),
  },
}));

jest.mock('@/lib/api/threads', () => ({
  createThread: jest.fn(),
  getThread: jest.fn(),
  sendMessage: jest.fn(),
}));

const mockCreateThread = createThread as jest.MockedFunction<typeof createThread>;
const mockRouter = jest.requireMock('expo-router').router as {
  back: jest.Mock;
  replace: jest.Mock;
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

describe('NewThreadScreen', () => {
  beforeEach(() => {
    mockCreateThread.mockReset();
    mockRouter.back.mockReset();
    mockRouter.replace.mockReset();
  });

  it('does not create a thread until the first message is sent', async () => {
    mockCreateThread.mockResolvedValue({
      thread_id: 'thread-new',
      turn_id: 'turn-new',
      status: 'in_progress',
    });

    const screen = await render(<NewThreadScreen />, { wrapper: createWrapper() });

    expect(screen.getByText('새 Thread')).toBeTruthy();
    expect(screen.getByText('첫 메시지를 입력해주세요.')).toBeTruthy();
    expect(mockCreateThread).not.toHaveBeenCalled();

    await fireEvent.changeText(screen.getByLabelText('메시지 입력'), 'First message');
    const sendButton = screen.getByRole('button', { name: '메시지 보내기' });
    await waitFor(() =>
      expect(sendButton.props.accessibilityState).toEqual(
        expect.objectContaining({ disabled: false }),
      ),
    );
    await fireEvent.press(sendButton);

    await waitFor(() => expect(mockCreateThread).toHaveBeenCalledWith('First message'));
    await waitFor(() =>
      expect(mockRouter.replace).toHaveBeenCalledWith({
        pathname: '/threads/[threadId]',
        params: { threadId: 'thread-new' },
      }),
    );
  });

  it('keeps the first message when creation fails', async () => {
    mockCreateThread.mockRejectedValue(new ApiError('unavailable', 503));

    const screen = await render(<NewThreadScreen />, { wrapper: createWrapper() });

    await fireEvent.changeText(screen.getByLabelText('메시지 입력'), 'Keep this');
    const sendButton = screen.getByRole('button', { name: '메시지 보내기' });
    await waitFor(() =>
      expect(sendButton.props.accessibilityState).toEqual(
        expect.objectContaining({ disabled: false }),
      ),
    );
    await fireEvent.press(sendButton);

    expect(await screen.findByText('Codex에 연결할 수 없습니다.')).toBeTruthy();
    expect(screen.getByLabelText('메시지 입력').props.value).toBe('Keep this');
    expect(mockRouter.replace).not.toHaveBeenCalled();
  });
});

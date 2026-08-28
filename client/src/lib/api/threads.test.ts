import { ApiError, fetchJson } from './client';
import { createThread, getThread, getThreads, sendMessage } from './threads';

jest.mock('./client', () => {
  const actual = jest.requireActual('./client');
  return { ...actual, fetchJson: jest.fn() };
});

const mockFetchJson = fetchJson as jest.MockedFunction<typeof fetchJson>;

describe('thread API', () => {
  beforeEach(() => {
    mockFetchJson.mockReset();
  });

  it('requests the first unarchived thread page', async () => {
    const response = { threads: [], next_cursor: null };
    mockFetchJson.mockResolvedValue(response);

    await expect(getThreads()).resolves.toBe(response);
    expect(mockFetchJson).toHaveBeenCalledWith('/api/v1/threads?limit=20&archived=false');
  });

  it('encodes a pagination cursor', async () => {
    mockFetchJson.mockResolvedValue({ threads: [], next_cursor: null });

    await getThreads({ cursor: 'next cursor/+', limit: 10, archived: true });

    expect(mockFetchJson).toHaveBeenCalledWith(
      '/api/v1/threads?limit=10&archived=true&cursor=next%20cursor%2F%2B',
    );
  });

  it('encodes a thread id', async () => {
    mockFetchJson.mockResolvedValue({ id: 'thread/id' });

    await getThread('thread/id');

    expect(mockFetchJson).toHaveBeenCalledWith('/api/v1/threads/thread%2Fid');
  });

  it('creates a thread with the first message', async () => {
    const response = { thread_id: 'thread-1', turn_id: 'turn-1', status: 'in_progress' as const };
    mockFetchJson.mockResolvedValue(response);

    await expect(createThread('hello')).resolves.toBe(response);
    expect(mockFetchJson).toHaveBeenCalledWith(
      '/api/v1/threads',
      { method: 'POST', body: JSON.stringify({ message: 'hello' }) },
      65_000,
    );
  });

  it('encodes a thread id when sending a message', async () => {
    mockFetchJson.mockResolvedValue({
      thread_id: 'thread/id',
      turn_id: 'turn-2',
      status: 'in_progress',
    });

    await sendMessage('thread/id', 'follow up');

    expect(mockFetchJson).toHaveBeenCalledWith(
      '/api/v1/threads/thread%2Fid/messages',
      { method: 'POST', body: JSON.stringify({ message: 'follow up' }) },
      65_000,
    );
  });

  it('preserves API errors', async () => {
    const error = new ApiError('failed', 503);
    mockFetchJson.mockRejectedValue(error);

    await expect(getThreads()).rejects.toBe(error);
  });
});

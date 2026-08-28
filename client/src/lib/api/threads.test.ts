import { ApiError, fetchJson } from './client';
import { getThread, getThreads } from './threads';

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
    expect(mockFetchJson).toHaveBeenCalledWith('/api/v1/threads?limit=50&archived=false');
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

  it('preserves API errors', async () => {
    const error = new ApiError('failed', 503);
    mockFetchJson.mockRejectedValue(error);

    await expect(getThreads()).rejects.toBe(error);
  });
});

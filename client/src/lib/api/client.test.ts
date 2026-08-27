import { ApiError, fetchJson } from './client';

const mockFetch = jest.fn();

globalThis.fetch = mockFetch as typeof fetch;

describe('fetchJson', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('returns a JSON response', async () => {
    mockFetch.mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    await expect(fetchJson<{ ok: boolean }>('/health')).resolves.toEqual({ ok: true });
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/health',
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
  });

  it('rejects malformed JSON', async () => {
    mockFetch.mockResolvedValue(new Response('not-json', { status: 200 }));

    await expect(fetchJson('/health')).rejects.toMatchObject({
      message: '서버 응답을 JSON으로 해석할 수 없습니다.',
      status: 200,
    });
  });

  it('includes the status and payload in HTTP errors', async () => {
    mockFetch.mockResolvedValue(
      new Response(JSON.stringify({ detail: 'failed' }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    await expect(fetchJson('/health')).rejects.toMatchObject({
      message: '요청에 실패했습니다. (500)',
      status: 500,
      payload: { detail: 'failed' },
    });
  });

  it('turns an aborted request into a timeout error', async () => {
    mockFetch.mockImplementation(
      (_url: string, init: RequestInit) =>
        new Promise((_resolve, reject) => {
          init.signal?.addEventListener('abort', () => {
            const error = new Error('aborted');
            error.name = 'AbortError';
            reject(error);
          });
        }),
    );

    await expect(fetchJson('/slow', {}, 1)).rejects.toEqual(
      new ApiError('요청 시간이 초과되었습니다.'),
    );
  });
});

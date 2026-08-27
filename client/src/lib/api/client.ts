import { env } from '@/config/env';

const DEFAULT_TIMEOUT_MS = 10_000;

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number | null = null,
    readonly payload: unknown = null,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function fetchJson<T>(
  path: string,
  init: RequestInit = {},
  timeoutMs = DEFAULT_TIMEOUT_MS,
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  const headers = new Headers(init.headers);

  headers.set('Accept', 'application/json');
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  try {
    const response = await fetch(`${env.apiUrl}/${path.replace(/^\/+/, '')}`, {
      ...init,
      headers,
      signal: controller.signal,
    });
    const body = await response.text();
    let payload: unknown = null;

    if (body) {
      try {
        payload = JSON.parse(body);
      } catch {
        throw new ApiError('서버 응답을 JSON으로 해석할 수 없습니다.', response.status);
      }
    }

    if (!response.ok) {
      throw new ApiError(`요청에 실패했습니다. (${response.status})`, response.status, payload);
    }

    return payload as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof Error && error.name === 'AbortError') {
      throw new ApiError('요청 시간이 초과되었습니다.');
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

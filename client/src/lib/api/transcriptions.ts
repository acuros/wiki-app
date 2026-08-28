import { fetch } from 'expo/fetch';
import { File } from 'expo-file-system';

import { env } from '@/config/env';

const MAX_AUDIO_BYTES = 5 * 1024 * 1024;
const TRANSCRIPTION_TIMEOUT_MS = 300_000;

export type TranscriptionErrorReason =
  | 'missing_key'
  | 'invalid_audio'
  | 'too_large'
  | 'busy'
  | 'unauthorized'
  | 'unavailable'
  | 'timeout'
  | 'invalid_response';

export class TranscriptionError extends Error {
  constructor(readonly reason: TranscriptionErrorReason) {
    super(reason);
    this.name = 'TranscriptionError';
  }
}

type TranscriptionResponse = {
  text: string;
};

function errorForStatus(status: number) {
  if (status === 400) return new TranscriptionError('invalid_audio');
  if (status === 401 || status === 403) return new TranscriptionError('unauthorized');
  if (status === 413) return new TranscriptionError('too_large');
  if (status === 429) return new TranscriptionError('busy');
  if (status >= 500) return new TranscriptionError('unavailable');
  return new TranscriptionError('invalid_response');
}

export async function transcribeRecording(uri: string): Promise<string> {
  if (!env.transcriptionApiKey) {
    throw new TranscriptionError('missing_key');
  }

  const file = new File(uri);
  if (file.size === 0) {
    throw new TranscriptionError('invalid_audio');
  }
  if (file.size > MAX_AUDIO_BYTES) {
    throw new TranscriptionError('too_large');
  }

  const body = new FormData();
  body.append('file', file, file.name || 'recording.m4a');
  body.append('model', 'whisper-1');
  body.append('response_format', 'json');

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), TRANSCRIPTION_TIMEOUT_MS);
  try {
    const response = await fetch(env.transcriptionApiUrl, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        Authorization: `Bearer ${env.transcriptionApiKey}`,
      },
      body,
      signal: controller.signal,
    });
    if (!response.ok) {
      throw errorForStatus(response.status);
    }

    let payload: TranscriptionResponse;
    try {
      payload = (await response.json()) as TranscriptionResponse;
    } catch {
      throw new TranscriptionError('invalid_response');
    }
    if (typeof payload.text !== 'string') {
      throw new TranscriptionError('invalid_response');
    }
    return payload.text;
  } catch (error) {
    if (error instanceof TranscriptionError) {
      throw error;
    }
    if (error instanceof Error && error.name === 'AbortError') {
      throw new TranscriptionError('timeout');
    }
    throw new TranscriptionError('unavailable');
  } finally {
    clearTimeout(timeout);
    try {
      file.delete();
    } catch {
      // Cache cleanup failure must not replace the transcription result.
    }
  }
}

import { fetch } from 'expo/fetch';
import { File } from 'expo-file-system';

import { TranscriptionError, transcribeRecording } from './transcriptions';

jest.mock('expo/fetch', () => ({ fetch: jest.fn() }));
jest.mock('expo-file-system', () => ({ File: jest.fn() }));

const mockFetch = fetch as jest.MockedFunction<typeof fetch>;
const MockFile = File as jest.MockedClass<typeof File>;
const mockDelete = jest.fn();

function file(size = 100) {
  const recording = new Blob(['audio'], { type: 'audio/mp4' });
  Object.defineProperties(recording, {
    delete: { value: mockDelete },
    name: { value: 'recording.m4a' },
    size: { value: size },
    uri: { value: 'file:///recording.m4a' },
  });
  return recording as unknown as File;
}

function response(body: string, status: number) {
  return new Response(body, { status }) as unknown as Awaited<ReturnType<typeof fetch>>;
}

describe('transcribeRecording', () => {
  beforeEach(() => {
    mockFetch.mockReset();
    MockFile.mockReset();
    mockDelete.mockReset();
    MockFile.mockImplementation(() => file());
  });

  it('uploads the recording directly with the bearer key and OpenAI fields', async () => {
    mockFetch.mockResolvedValue(response(JSON.stringify({ text: '받아쓴 문장' }), 200));

    await expect(transcribeRecording('file:///recording.m4a')).resolves.toBe('받아쓴 문장');

    expect(MockFile).toHaveBeenCalledWith('file:///recording.m4a');
    expect(mockFetch).toHaveBeenCalledWith(
      'https://transcription.joshua.kim/v1/audio/transcriptions',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({ Authorization: 'Bearer test-transcription-key' }),
        body: expect.any(FormData),
      }),
    );
    const body = mockFetch.mock.calls[0][1]?.body as FormData;
    expect([...body.entries()].map(([name]) => name)).toEqual(['file', 'model', 'response_format']);
    expect(body.get('model')).toBe('whisper-1');
    expect(body.get('response_format')).toBe('json');
    expect(mockDelete).toHaveBeenCalledTimes(1);
  });

  it('rejects recordings larger than five megabytes before upload', async () => {
    MockFile.mockImplementation(() => file(5 * 1024 * 1024 + 1));

    await expect(transcribeRecording('file:///large.m4a')).rejects.toEqual(
      new TranscriptionError('too_large'),
    );

    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('classifies a busy service and still deletes the cached recording', async () => {
    mockFetch.mockResolvedValue(response('', 429));

    await expect(transcribeRecording('file:///recording.m4a')).rejects.toEqual(
      new TranscriptionError('busy'),
    );

    expect(mockDelete).toHaveBeenCalledTimes(1);
  });

  it('rejects a response without text', async () => {
    mockFetch.mockResolvedValue(response(JSON.stringify({ result: 'missing' }), 200));

    await expect(transcribeRecording('file:///recording.m4a')).rejects.toEqual(
      new TranscriptionError('invalid_response'),
    );
  });
});

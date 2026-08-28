import { fetchJson } from './client';

export type ThreadSummary = {
  id: string;
  title: string | null;
  preview: string;
  source: string;
  cwd: string;
  project_id: string | null;
  created_at: string;
  updated_at: string;
  recency_at: string;
  status: string;
  active_flags: string[];
};

export type TextContent = {
  type: 'text';
  text: string;
};

export type ReferenceContent = {
  type: 'reference';
  reference_type: string;
  target: string;
  name: string | null;
};

export type ThreadContent = TextContent | ReferenceContent;

export type UserMessageEntry = {
  id: string;
  type: 'user_message';
  content: ThreadContent[];
};

export type AssistantMessageEntry = {
  id: string;
  type: 'assistant_message';
  phase: string;
  content: ThreadContent[];
};

export type PlanEntry = {
  id: string;
  type: 'plan';
  content: ThreadContent[];
};

export type ThreadEntry = UserMessageEntry | AssistantMessageEntry | PlanEntry;

export type ThreadTurn = {
  id: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  entries: ThreadEntry[];
  omitted_item_count: number;
  omitted_item_types: string[];
};

export type ThreadListResponse = {
  threads: ThreadSummary[];
  next_cursor: string | null;
};

export type ThreadDetail = ThreadSummary & {
  turns: ThreadTurn[];
};

type GetThreadsOptions = {
  cursor?: string;
  limit?: number;
  archived?: boolean;
};

export function getThreads({
  cursor,
  limit = 50,
  archived = false,
}: GetThreadsOptions = {}): Promise<ThreadListResponse> {
  const cursorQuery = cursor ? `&cursor=${encodeURIComponent(cursor)}` : '';
  return fetchJson<ThreadListResponse>(
    `/api/v1/threads?limit=${limit}&archived=${archived}${cursorQuery}`,
  );
}

export function getThread(threadId: string): Promise<ThreadDetail> {
  return fetchJson<ThreadDetail>(`/api/v1/threads/${encodeURIComponent(threadId)}`);
}

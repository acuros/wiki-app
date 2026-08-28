import { useLocalSearchParams } from 'expo-router';

import { ThreadConversation } from '@/components/thread-conversation';

export default function ThreadDetailScreen() {
  const params = useLocalSearchParams<{ threadId?: string | string[] }>();
  const threadId = Array.isArray(params.threadId) ? params.threadId[0] : params.threadId;

  return <ThreadConversation threadId={threadId || ''} />;
}

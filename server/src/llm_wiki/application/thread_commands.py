from llm_wiki.application.ports import ThreadSource
from llm_wiki.domain.errors import InvalidMessage, InvalidThreadQuery
from llm_wiki.domain.models import ThreadId, TurnSubmission


class ThreadCommandService:
    def __init__(self, source: ThreadSource) -> None:
        self._source = source

    async def create_thread(self, message: str) -> TurnSubmission:
        self._validate_message(message)
        return await self._source.create(message)

    async def send_message(self, thread_id: ThreadId, message: str) -> TurnSubmission:
        if not thread_id:
            raise InvalidThreadQuery("thread id must not be empty")
        self._validate_message(message)
        return await self._source.send(thread_id, message)

    @staticmethod
    def _validate_message(message: str) -> None:
        if not message.strip():
            raise InvalidMessage("message must not be blank")

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

    async def update_settings(
        self, thread_id: ThreadId, *, model: str | None = None, effort: str | None = None
    ) -> None:
        if not thread_id:
            raise InvalidThreadQuery("thread id must not be empty")
        if model is not None and model not in {"gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"}:
            raise InvalidThreadQuery("unsupported model")
        if effort is not None and effort not in {"none", "low", "medium", "high", "xhigh"}:
            raise InvalidThreadQuery("unsupported reasoning effort")
        if model is None and effort is None:
            raise InvalidThreadQuery("at least one setting is required")
        await self._source.update_settings(thread_id, model=model, effort=effort)

    @staticmethod
    def _validate_message(message: str) -> None:
        if not message.strip():
            raise InvalidMessage("message must not be blank")

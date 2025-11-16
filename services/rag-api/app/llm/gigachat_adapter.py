from __future__ import annotations

from typing import Any, List, Optional, Sequence

from gigachat import GigaChat as GigaSDK
from gigachat.models import Chat as GigaChatPayload, Messages as GigaMessage, MessagesRole

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.tools import BaseTool


class GigaChatLC(BaseChatModel):
    """
    Адаптер GigaChat -> LangChain v1 BaseChatModel.

    Под капотом: официальный SDK gigachat.
    Снаружи: интерфейс как у ChatOpenAI, включая bind_tools().
    """

    credentials: str
    scope: str = "GIGACHAT_API_PERS"
    model: str = "GigaChat-2"
    verify_ssl_certs: bool = False

    class Config:
        arbitrary_types_allowed = True

    @property
    def _llm_type(self) -> str:
        return "gigachat"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> ChatResult:
        # LangChain -> GigaChat формат сообщений
        giga_messages: list[GigaMessage] = []

        for m in messages:
            if isinstance(m, HumanMessage):
                role = MessagesRole.USER
            elif isinstance(m, SystemMessage):
                role = MessagesRole.SYSTEM
            else:
                role = MessagesRole.ASSISTANT

            giga_messages.append(
                GigaMessage(
                    role=role,
                    content=m.content,
                )
            )

        payload = GigaChatPayload(messages=giga_messages)

        # простой вариант – отдельный контекст на каждый вызов
        with GigaSDK(
            credentials=self.credentials,
            scope=self.scope,
            model=self.model,
            verify_ssl_certs=self.verify_ssl_certs,
        ) as giga:
            response = giga.chat(payload)

        content = response.choices[0].message.content

        # уважаем stop, если вдруг кто-то его всё же передаст
        if stop:
            for s in stop:
                if s in content:
                    content = content.split(s)[0]

        ai_message = AIMessage(content=content)
        return ChatResult(generations=[ChatGeneration(message=ai_message)])

    # 🔧 КРИТИЧНО: реализуем bind_tools, чтобы LangGraph/agents не падали
    def bind_tools(
        self,
        tools: Sequence[BaseTool] | Sequence[Any],
        **kwargs: Any,
    ) -> "GigaChatLC":
        """
        LangChain v1 ожидает у ChatModel наличие bind_tools().

        В нашем ReAct-агенте инструменты вызываются не через
        нативный tool-calling LLM, а через внешний агент.
        Поэтому здесь можно сделать no-op: просто вернуть self.

        При желании ты позже можешь:
        - сохранить tools в self._tools;
        - модифицировать system prompt, чтобы явно перечислять инструменты.
        """
        return self

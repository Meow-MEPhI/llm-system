from logging import critical

from langchain_gigachat.chat_models import GigaChat
from langchain_core.messages import SystemMessage, HumanMessage


class NormalAgent:
    """Агент для нормализации научной статьи."""

    def __init__(self, auth_key: str):
        self.auth_key = auth_key
        self.model = GigaChat(credentials=auth_key, verify_ssl_certs=False)

    def run(self, state: dict) -> dict:

        article_text = state.get("article_text", "")
        critique = state.get("critique_normal", "")
        prompt = open('./agent_system/prompt_normal.txt', 'r', encoding='utf-8').read()
        revision_count = state.get("revision_count_nor", 0)

        if critique:
            prompt += f"\n\n⚠️ ВНИМАНИЕ! Предыдущая попытка была отклонена:\n{critique}\n\nУчти эти замечания и исправь ошибки!"

        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=article_text)
        ]

        result = self.model.invoke(messages).content

        return {
            "rubric_result_normal": result,
            "critique_normal": "",
            "revision_count_nor": revision_count + 1,
            "status": ["completed"]
        }

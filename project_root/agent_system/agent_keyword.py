
from langchain_gigachat.chat_models import GigaChat
from langchain_core.messages import SystemMessage, HumanMessage


class KeywordAgent:
    """Агент для создания рубрикации научной статьи."""

    def __init__(self, auth_key: str):
        self.auth_key = auth_key
        self.model = GigaChat(credentials=auth_key, verify_ssl_certs=False)

    def run(self, state: dict) -> dict:

        article_text = state.get("article_text", "")
        prompt = open('./agent_system/prompt_keyword.txt', 'r', encoding='utf-8').read()
        critique = state.get("critique_key", "")
        revision_count = state.get("revision_count_key", 0)


        if critique:
            prompt += f"\n\n⚠️ ВНИМАНИЕ! Предыдущая попытка была отклонена:\n{critique}\n\nУчти эти замечания и исправь ошибки!"

        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=article_text)
        ]

        result = self.model.invoke(messages).content

        return {
            "rubric_result_keyword": result,
            "critique_key": "",
            "revision_count_key": revision_count + 1,
            "status": ["completed"]
        }

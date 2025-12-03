
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

        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=article_text[:10000])  # Ограничиваем длину для GigaChat
        ]

        result = self.model.invoke(messages).content


        return {
            "rubric_result_keyword": result,
            "status": ["completed"]
        }


from langchain_gigachat.chat_models import GigaChat
from langchain_core.messages import SystemMessage, HumanMessage


class KritikAgent:
    """Агент для проверки корректности отевта."""

    def __init__(self, auth_key: str):
        self.auth_key = auth_key
        self.model = GigaChat(credentials=auth_key, verify_ssl_certs=False)

    def run(self, state: dict) -> dict:

        article_text1 = state.get("rubric_result_rubricator", "")

        prompt = open('./agent_system/prompt_kritik.txt', 'r', encoding='utf-8').read()

        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=article_text1[:10000])  # Ограничиваем длину для GigaChat
        ]

        result = self.model.invoke(messages).content


        return {
            "rubric_result_kritik": result,
            "status": ["completed"]
        }

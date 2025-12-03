from langchain_gigachat.chat_models import GigaChat
from langchain_core.messages import SystemMessage, HumanMessage


class RubricatorAgent:
    """Агент для создания рубрикации научной статьи."""

    def __init__(self, auth_key: str):
        self.auth_key = auth_key
        self.model = GigaChat(credentials=auth_key, verify_ssl_certs=False)

    def run(self, state: dict) -> dict:

        article_text = state.get("article_text", "")
        prompt = f"Ты — редактор-верстальщик и библиограф; задача: построить рубрикацию научной статьи как систему взаимосвязанных и соподчинённых заголовков, где заголовки старших уровней логически включают младшие, а одноуровневые заголовки равнозначны и не пересекаются; правила: 1) один признак деления на каждом уровне (не смешивай основания деления внутри одного уровня); 2) полнота: сумма подразделов покрывает содержание родительского раздела, «пустых» или дублирующих пунктов нет; 3) одноуровневые разделы не пересекаются и не включают друг друга; 4)заголовки краткие, терминологичные, без лишних слов; Ответ выдай в формате JSON!!!"
        critique = state.get("critique", "")  # Получаем критику
        revision_count = state.get("revision_count", 0)


        # Если есть критика, добавляем её в промпт
        if critique:
            prompt += f"\n\n⚠️ ВНИМАНИЕ! Предыдущая попытка была отклонена:\n{critique}\n\nУчти эти замечания и исправь ошибки!"

        messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=article_text)
        ]


        result = self.model.invoke(messages).content


        return {
            "rubric_result_rubricator": result,
            "critique": "",
            "revision_count": revision_count + 1,
            "status": ["completed"]
        }

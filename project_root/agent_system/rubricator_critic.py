from langchain_gigachat.chat_models import GigaChat
from langchain_core.messages import SystemMessage, HumanMessage


class CriticAgent:
    """Агент-критик для проверки качества рубрикации."""

    def __init__(self, auth_key: str):
        self.auth_key = auth_key
        self.model = GigaChat(credentials=auth_key, verify_ssl_certs=False)

    def run(self, state: dict) -> dict:
        article_text = state.get("article_text", "")[:5000]  # Ограничиваем длину
        rubric_result = state.get("rubric_result_rubricator", "")

        # Промпт критика
        critique_prompt = """Ты — строгий научный редактор и эксперт по библиографии. 
Твоя задача: проверить, правильно ли была определена рубрика для научной статьи.

КРИТЕРИИ ПРОВЕРКИ:
1. Рубрика должна точно отражать научную область статьи
2. Рубрика должна соответствовать стандартам ГОСТ для библиографии
3. Если в статье несколько тем, нужна основная (доминирующая) рубрика
4. Рубрика НЕ должна быть слишком общей или слишком узкой

ИНСТРУКЦИЯ:
Если рубрика КОРРЕКТНА и соответствует всем критериям, верни ТОЛЬКО слово: APPROVED

Если рубрика НЕКОРРЕКТНА, верни строго в формате:
REJECT: <краткое объяснение, что не так и как исправить>

Пример плохого ответа:
REJECT: Указана общая рубрика "Наука", но статья явно про криптографию. Нужна рубрика "Информационная безопасность" или "Криптография".

ВХОДНЫЕ ДАННЫЕ:
Фрагмент статьи: {article}

Предложенная рубрика: {rubric}

Твой вердикт:"""

        messages = [
            SystemMessage(content=critique_prompt.format(
                article=article_text,
                rubric=rubric_result
            ))
        ]

        response = self.model.invoke(messages).content.strip()

        # Определяем, одобрено или отклонено
        if response.startswith("APPROVED"):
            return {
                "critique": "",
                "status": ["critic_approved"]
            }

        return {
            "critique": response,
            "status": ["critic_rejected"]
        }

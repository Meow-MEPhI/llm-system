import requests
from langchain_gigachat.chat_models import GigaChat
from langchain_core.messages import SystemMessage, HumanMessage


class BibliographerAgent:
    """Агент для извлечения текста научной статьи из загруженного файла."""

    def __init__(self, auth_key: str):
        self.auth_key = auth_key
        self.model = GigaChat(credentials=auth_key, verify_ssl_certs=False)

    def run(self, state: dict) -> dict:
        """
        Получает текст статьи, уже извлечённый из PDF/TXT на бэкенде.
        Не нужно парсить HTML или скачивать файлы - текст уже готов!
        """

        # Текст уже готов из server.py (extract_text_from_pdf или extract_text_from_txt)
        article_text = state.get("article_text", "")

        if not article_text:
            return {
                "article_text": "",
                "status": ["error_no_text"]
            }

        print(f"✅ Текст статьи получен ({len(article_text)} символов)")

        return {
            "article_text": article_text,
            "status": ["text_extracted"]
        }

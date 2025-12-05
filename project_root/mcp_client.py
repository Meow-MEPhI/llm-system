"""HTTP клиент для MCP сервера."""

import requests

MCP_URL = "http://localhost:5002"

def save_article_via_mcp(article_text: str, rubric: str = "", keywords: str = "",
                         summary: str = "", normalized_text: str = ""):
    """
    Сохраняет статью через HTTP MCP сервер.

    Args:
        article_text: Полный текст статьи
        rubric: Рубрика
        keywords: Ключевые слова
        summary: Резюме
        normalized_text: Нормализованный текст

    Returns:
        article_id (int) или None при ошибке
    """
    try:
        response = requests.post(
            f"{MCP_URL}/save_article",
            json={
                "article_text": article_text,
                "rubric": rubric,
                "keywords": keywords,
                "summary": summary,
                "normalized_text": normalized_text
            },
            timeout=10
        )

        if response.status_code == 200:
            return response.json().get("article_id")
        else:
            print(f"⚠️ MCP ошибка: {response.text}")
            return None

    except requests.exceptions.ConnectionError:
        print("⚠️ MCP сервер недоступен! Запустите: python mcp_server.py")
        return None
    except Exception as e:
        print(f"⚠️ MCP ошибка: {e}")
        return None

def get_article_via_mcp(article_id: int):
    """Получить статью по ID через MCP."""
    try:
        response = requests.get(
            f"{MCP_URL}/get_article/{article_id}",
            timeout=5
        )

        if response.status_code == 200:
            return response.json().get("article")
        else:
            return None

    except Exception as e:
        print(f"⚠️ MCP ошибка: {e}")
        return None

def list_articles_via_mcp(limit: int = 10):
    """Получить список статей через MCP."""
    try:
        response = requests.get(
            f"{MCP_URL}/list_articles",
            params={"limit": limit},
            timeout=5
        )

        if response.status_code == 200:
            return response.json().get("articles", [])
        else:
            return []

    except Exception as e:
        print(f"⚠️ MCP ошибка: {e}")
        return []

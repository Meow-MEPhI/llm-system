import json
from datetime import datetime


class IndexerAgent:
    def __init__(self, auth_key: str = None):
        pass

    def run(self, state: dict) -> dict:
        print("📊 [Indexer] Собираю результаты...")

        data = {
            "article_text": state.get("article_text", ""),
            "rubric": state.get("rubric_result_rubricator", ""),
            "keywords": state.get("rubric_result_keyword", ""),
            "summary": state.get("rubric_result_summariser", ""),
            "normalized": state.get("rubric_result_normal", ""),
            "timestamp": datetime.now().isoformat()
        }

        print(f"✅ [Indexer] Готово")
        return {"indexed_data": json.dumps(data, ensure_ascii=False), "status": ["indexed"]}

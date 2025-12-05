"""HTTP MCP Server для работы с БД статей."""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)

DB_FILE = "articles.db"

# Инициализация БД
conn = sqlite3.connect(DB_FILE)
conn.execute('''CREATE TABLE IF NOT EXISTS articles
                (
                    id
                    INTEGER
                    PRIMARY
                    KEY
                    AUTOINCREMENT,
                    article_text
                    TEXT,
                    rubric
                    TEXT,
                    keywords
                    TEXT,
                    summary
                    TEXT,
                    normalized_text
                    TEXT,
                    created_at
                    TIMESTAMP
                    DEFAULT
                    CURRENT_TIMESTAMP
                )''')
conn.commit()
conn.close()
print("✅ БД инициализирована")


@app.route('/save_article', methods=['POST'])
def save_article():
    """Сохраняет статью в БД."""
    try:
        data = request.json

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute(
            """INSERT INTO articles
                   (article_text, rubric, keywords, summary, normalized_text)
               VALUES (?, ?, ?, ?, ?)""",
            (
                data.get("article_text", ""),
                data.get("rubric", ""),
                data.get("keywords", ""),
                data.get("summary", ""),
                data.get("normalized_text", "")
            )
        )

        conn.commit()
        article_id = cursor.lastrowid
        conn.close()

        return jsonify({"status": "success", "article_id": article_id}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/get_article/<int:article_id>', methods=['GET'])
def get_article(article_id):
    """Получить статью по ID."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM articles WHERE id = ?", (article_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return jsonify({
                "status": "success",
                "article": {
                    "id": row[0],
                    "article_text": row[1],
                    "rubric": row[2],
                    "keywords": row[3],
                    "summary": row[4],
                    "normalized_text": row[5],
                    "created_at": row[6]
                }
            }), 200
        else:
            return jsonify({"status": "error", "message": "Article not found"}), 404

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/list_articles', methods=['GET'])
def list_articles():
    """Получить список всех статей."""
    try:
        limit = request.args.get('limit', 10, type=int)

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, rubric, keywords, created_at FROM articles ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()

        articles = [
            {
                "id": row[0],
                "rubric": row[1],
                "keywords": row[2],
                "created_at": row[3]
            }
            for row in rows
        ]

        return jsonify({"status": "success", "articles": articles, "count": len(articles)}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    print("🚀 MCP HTTP Server запущен на http://localhost:5002")
    app.run(host="0.0.0.0", port=5002, debug=False)

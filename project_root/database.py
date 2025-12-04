import sqlite3
import json

# from pygments.lexers.robotframework import normalize

DB_FILE = "articles.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute('''CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        article_text TEXT,
        rubric TEXT,
        keywords TEXT,
        summary TEXT,
        normalized TEXT,
        created_at TEXT
    )''')
    conn.commit()
    conn.close()

def save_article(rubric, keywords, summary, normalized, article_text=""):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO articles (article_text, rubric, keywords, summary, normalized, created_at) VALUES (?, ?, ?, ?, ?, datetime('now'))",
        (article_text, rubric, keywords, summary, normalized)
    )
    conn.commit()
    article_id = cursor.lastrowid
    conn.close()
    return article_id

def get_all_articles():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM articles ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "article_text": r[1],
            "rubric": r[2],
            "keywords": r[3],
            "summary": r[4],
            "normalized": r[5],
            "created_at": r[6]
        }
        for r in rows
    ]

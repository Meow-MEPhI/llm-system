import sqlite3
import json

conn = sqlite3.connect("articles.db")
cursor = conn.cursor()

cursor.execute("SELECT * FROM articles")
rows = cursor.fetchall()

print(f"Всего статей: {len(rows)}\n")

for row in rows:
    # print("=" * 80)
    # print(f"ID: {row[0]}")
    # print(f"Рубрика: {row[1]}")
    # print(f"Ключевые слова: {row[2]}")
    # print(f"Резюме: {row[3][:200]}...")  # Первые 200 символов
    # print(f"Создано: {row[4]}")
    # print()
    print(f"{row[5]}")

conn.close()

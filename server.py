from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import PyPDF2
import sys
import traceback

# Добавляем путь к вашей агентной системе
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agent_system'))

from project_root.agent_system.graph_orchestrator import create_multi_agent_graph

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Ваш ключ GigaChat (в боевом приложении - из переменных окружения!)
GIGACHAT_AUTH_KEY = "YOUR_GIGACHAT_AUTH_KEY_HERE"


def extract_text_from_pdf(pdf_path: str) -> str:
    """Извлекает текст из PDF файла."""
    try:
        with open(pdf_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text
    except Exception as e:
        raise Exception(f"Ошибка чтения PDF: {str(e)}")


def extract_text_from_txt(txt_path: str) -> str:
    """Извлекает текст из TXT файла."""
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        raise Exception(f"Ошибка чтения TXT: {str(e)}")


@app.route('/process_article', methods=['POST'])
def process_article():
    """
    Основной эндпоинт для обработки статей.
    Принимает: PDF или TXT файл
    Возвращает: Результаты работы всех агентов
    """
    try:
        # ========== ЭТАП 1: Получение и сохранение файла ==========
        if 'pdf' not in request.files:
            return jsonify({
                "status": "error",
                "message": "Файл не найден. Используйте поле 'pdf'"
            }), 400

        file = request.files['pdf']
        if file.filename == '':
            return jsonify({
                "status": "error",
                "message": "Имя файла пусто"
            }), 400

        # Сохраняем файл
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)

        # ========== ЭТАП 2: Извлечение текста из файла ==========
        print(f"📄 Обработка файла: {file.filename}")

        if file.filename.lower().endswith('.pdf'):
            article_text = extract_text_from_pdf(filepath)
            file_type = "PDF"
        elif file.filename.lower().endswith('.txt'):
            article_text = extract_text_from_txt(filepath)
            file_type = "TXT"
        else:
            return jsonify({
                "status": "error",
                "message": "Поддерживаются только PDF и TXT файлы"
            }), 400

        if not article_text or len(article_text.strip()) == 0:
            return jsonify({
                "status": "error",
                "message": "Не удалось извлечь текст из файла"
            }), 400

        print(f"✅ Текст успешно извлечён ({len(article_text)} символов)")

        # ========== ЭТАП 3: Инициализация графа агентов ==========
        print("🤖 Инициализация агентной системы...")

        try:
            graph = create_multi_agent_graph(auth_key=GIGACHAT_AUTH_KEY)
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Ошибка инициализации агентов: {str(e)}"
            }), 500

        # ========== ЭТАП 4: Подготовка начального состояния ==========
        initial_state = {
            "article_url": "",
            "article_text": article_text[:50000],  # Ограничиваем длину для GigaChat
            "rubric_result_rubricator": "",
            "rubric_result_keyword": "",
            "rubric_result_normal": "",
            "rubric_result_summariser": "",
            "rubric_result_kritik": "",
            "critique": "",
            "revision_count": 0,
            "status": ["started", "text_extracted"]
        }

        # ========== ЭТАП 5: Запуск графа обработки ==========
        print("⚙️  Запуск агентной системы...")

        try:
            final_state = graph.invoke(initial_state)
            print("✅ Обработка завершена успешно!")
        except Exception as e:
            print(f"❌ Ошибка при обработке: {str(e)}")
            traceback.print_exc()
            return jsonify({
                "status": "error",
                "message": f"Ошибка обработки графа: {str(e)}"
            }), 500

        # ========== ЭТАП 6: Формирование результатов ==========
        result = {
            "status": "success",
            "filename": file.filename,
            "file_type": file_type,
            "processing_time": "~1-3 минуты",
            "results": {
                "rubrics": final_state.get("rubric_result_rubricator", ""),
                "keywords": final_state.get("rubric_result_keyword", ""),
                "normalization": final_state.get("rubric_result_normal", ""),
                "summary": final_state.get("rubric_result_summariser", ""),
                "critique": final_state.get("rubric_result_kritik", "")
            },
            "metadata": {
                "text_length": len(article_text),
                "revision_count": final_state.get("revision_count", 0),
                "status": final_state.get("status", [])
            }
        }

        return jsonify(result), 200

    except Exception as e:
        print(f"❌ Ошибка сервера: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": f"Внутренняя ошибка сервера: {str(e)}"
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Проверка здоровья сервера."""
    return jsonify({
        "status": "ok",
        "service": "Article Processing API",
        "version": "1.0"
    }), 200


if __name__ == '__main__':
    print("🚀 Запуск API сервера на http://localhost:5000")
    print("📝 GigaChat Auth Key:", "Set" if GIGACHAT_AUTH_KEY != "YOUR_GIGACHAT_AUTH_KEY_HERE" else "NOT SET - ОШИБКА!")
    app.run(host="0.0.0.0", port=5000, debug=True)

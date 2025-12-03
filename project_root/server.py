"""
Flask API Server для обработки научных статей
Связывает React Frontend с Python Backend (LangGraph Agent System)
"""

import os
from dotenv import load_dotenv

# ЗАГРУЗКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ - САМОЕ НАЧАЛО!
load_dotenv()

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import PyPDF2
import tempfile
import sys
import traceback
from datetime import datetime

# Добавляем путь к агентной системе
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agent_system'))

try:
    from agent_system.graph_orchestrator import create_multi_agent_graph
except ImportError as e:
    print(f"⚠️  Ошибка импорта: {e}")
    print("Убедитесь, что папка agent_system/ существует и содержит graph_orchestrator.py")

app = Flask(__name__)
CORS(app)

# ========== КОНФИГУРАЦИЯ ==========
UPLOAD_FOLDER = 'uploads'
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 МБ
ALLOWED_EXTENSIONS = {'pdf', 'txt'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# GigaChat Authorization Key - ПОЛУЧАЕМ ИЗ .env или используем значение по умолчанию
GIGACHAT_AUTH_KEY = os.getenv('GIGACHAT_AUTH_KEY', 'ENTER_KEY')

if not GIGACHAT_AUTH_KEY or GIGACHAT_AUTH_KEY == 'YOUR_GIGACHAT_AUTH_KEY_HERE':
    print("⚠️  ВНИМАНИЕ: Используется значение GIGACHAT_AUTH_KEY по умолчанию!")
    GIGACHAT_AUTH_KEY = 'ENTER_KEY'
else:
    print("✅ GigaChat Auth Key: успешно загружен из .env")


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def allowed_file(filename: str) -> bool:
    """Проверка расширения файла."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Извлекает текст из PDF файла.

    Args:
        pdf_path: Путь к PDF файлу

    Returns:
        Извлечённый текст

    Raises:
        Exception: Если ошибка при чтении PDF
    """
    try:
        print(f"📖 Извлечение текста из PDF: {pdf_path}")
        with open(pdf_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            text = ""
            total_pages = len(pdf_reader.pages)

            for page_num, page in enumerate(pdf_reader.pages, 1):
                try:
                    page_text = page.extract_text()
                    text += page_text + "\n"
                    print(f"   ✓ Страница {page_num}/{total_pages}")
                except Exception as e:
                    print(f"   ⚠️  Ошибка на странице {page_num}: {str(e)}")
                    continue

        print(f"✅ PDF успешно обработан ({len(text)} символов)")
        return text
    except Exception as e:
        raise Exception(f"Ошибка чтения PDF: {str(e)}")


def extract_text_from_txt(txt_path: str) -> str:
    """
    Извлекает текст из TXT файла.

    Args:
        txt_path: Путь к TXT файлу

    Returns:
        Содержимое файла

    Raises:
        Exception: Если ошибка при чтении TXT
    """
    try:
        print(f"📝 Извлечение текста из TXT: {txt_path}")
        with open(txt_path, 'r', encoding='utf-8') as f:
            text = f.read()
        print(f"✅ TXT успешно обработан ({len(text)} символов)")
        return text
    except Exception as e:
        raise Exception(f"Ошибка чтения TXT: {str(e)}")


def sanitize_text(text: str, max_length: int = 50000) -> str:
    """
    Очищает и ограничивает длину текста.

    Args:
        text: Исходный текст
        max_length: Максимальная длина

    Returns:
        Обработанный текст
    """
    # Удаляем специальные символы
    text = text.replace('\x00', '')
    text = text.replace('\ufffd', '')

    # Ограничиваем длину
    if len(text) > max_length:
        print(f"⚠️  Текст обрезан с {len(text)} до {max_length} символов")
        text = text[:max_length]

    return text.strip()


# ========== ОСНОВНЫЕ ЭНДПОИНТЫ ==========

@app.route('/health', methods=['GET'])
def health_check():
    """
    Проверка здоровья сервера.

    Returns:
        JSON с информацией о сервере
    """
    return jsonify({
        "status": "ok",
        "service": "Article Processing API",
        "version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "gigachat_configured": GIGACHAT_AUTH_KEY == 'ENTER_KEY'
    }), 200


@app.route('/process_article', methods=['POST'])
def process_article():
    """
    Основной эндпоинт для обработки статей.

    Принимает:
        - PDF или TXT файл в поле 'pdf'

    Возвращает:
        - JSON с результатами работы всех агентов
    """
    try:
        print("\n" + "=" * 80)
        print("🚀 НОВАЯ СЕССИЯ ОБРАБОТКИ СТАТЬИ")
        print("=" * 80)

        # ========== ЭТАП 1: ПРОВЕРКА И СОХРАНЕНИЕ ФАЙЛА ==========
        print("\n[1/6] Проверка файла...")

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

        if not allowed_file(file.filename):
            return jsonify({
                "status": "error",
                "message": "Поддерживаются только PDF и TXT файлы"
            }), 400

        # Проверяем размер файла
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if file_size > MAX_FILE_SIZE:
            return jsonify({
                "status": "error",
                "message": f"Файл слишком большой. Максимум: {MAX_FILE_SIZE / 1024 / 1024} МБ"
            }), 400

        # Сохраняем файл
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        print(f"✅ Файл сохранён: {file.filename} ({file_size / 1024:.2f} KB)")

        # ========== ЭТАП 2: ИЗВЛЕЧЕНИЕ ТЕКСТА ==========
        print("\n[2/6] Извлечение текста из файла...")

        file_type = "PDF" if file.filename.lower().endswith('.pdf') else "TXT"

        try:
            if file_type == "PDF":
                article_text = extract_text_from_pdf(filepath)
            else:
                article_text = extract_text_from_txt(filepath)
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Ошибка извлечения текста: {str(e)}"
            }), 400

        if not article_text or len(article_text.strip()) == 0:
            return jsonify({
                "status": "error",
                "message": "Не удалось извлечь текст из файла"
            }), 400

        # Очищаем текст
        article_text = sanitize_text(article_text)
        print(f"✅ Текст готов к обработке ({len(article_text)} символов)")

        # ========== ЭТАП 3: ИНИЦИАЛИЗАЦИЯ ГРАФА ==========
        print("\n[3/6] Инициализация агентной системы...")

        if not GIGACHAT_AUTH_KEY or GIGACHAT_AUTH_KEY == 'YOUR_GIGACHAT_AUTH_KEY_HERE':
            return jsonify({
                "status": "error",
                "message": "GigaChat Auth Key не установлен. Установите переменную окружения GIGACHAT_AUTH_KEY"
            }), 500

        try:
            graph = create_multi_agent_graph(auth_key=GIGACHAT_AUTH_KEY)
            print("✅ Граф агентов инициализирован")
        except Exception as e:
            print(f"❌ Ошибка инициализации: {str(e)}")
            return jsonify({
                "status": "error",
                "message": f"Ошибка инициализации агентов: {str(e)}"
            }), 500

        # ========== ЭТАП 4: ПОДГОТОВКА НАЧАЛЬНОГО СОСТОЯНИЯ ==========
        print("\n[4/6] Подготовка начального состояния...")

        initial_state = {
            "article_url": "",
            "article_text": article_text,
            "rubric_result_rubricator": "",
            "rubric_result_keyword": "",
            "rubric_result_normal": "",
            "rubric_result_summariser": "",
            "rubric_result_kritik": "",
            "critique": "",
            "revision_count": 0,
            "status": ["started", "text_extracted"]
        }

        print("✅ Начальное состояние готово")

        # ========== ЭТАП 5: ЗАПУСК ГРАФА ==========
        print("\n[5/6] Запуск обработки агентной системой...")
        print("-" * 80)

        try:
            final_state = graph.invoke(initial_state)
            print("-" * 80)
            print("✅ Обработка агентной системой завершена!")
        except Exception as e:
            print(f"❌ Ошибка при обработке: {str(e)}")
            traceback.print_exc()
            return jsonify({
                "status": "error",
                "message": f"Ошибка обработки графа: {str(e)}"
            }), 500

        # ========== ЭТАП 6: ФОРМИРОВАНИЕ РЕЗУЛЬТАТОВ ==========
        print("\n[6/6] Формирование результатов...")

        result = {
            "status": "success",
            "filename": file.filename,
            "file_type": file_type,
            "processing_time": "~1-3 минуты",
            "timestamp": datetime.now().isoformat(),
            "results": {
                "rubrics": final_state.get("rubric_result_rubricator", "").strip(),
                "keywords": final_state.get("rubric_result_keyword", "").strip(),
                "normalization": final_state.get("rubric_result_normal", "").strip(),
                "summary": final_state.get("rubric_result_summariser", "").strip(),
                "critique": final_state.get("rubric_result_kritik", "").strip()
            },
            "metadata": {
                "text_length": len(article_text),
                "revision_count": final_state.get("revision_count", 0),
                "status": final_state.get("status", []),
                "file_size_kb": file_size / 1024
            }
        }

        print("✅ Результаты сформированы")
        print("\n" + "=" * 80)
        print("✅ СЕССИЯ ЗАВЕРШЕНА УСПЕШНО")
        print("=" * 80 + "\n")

        return jsonify(result), 200

    except Exception as e:
        print(f"❌ Критическая ошибка: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": f"Внутренняя ошибка сервера: {str(e)}"
        }), 500


@app.route('/status', methods=['GET'])
def status():
    """Получить статус сервера и конфигурацию."""
    return jsonify({
        "server_status": "running",
        "uploads_folder": UPLOAD_FOLDER,
        "upload_count": len(os.listdir(UPLOAD_FOLDER)),
        "gigachat_available": GIGACHAT_AUTH_KEY == 'ENTER_KEY',
        "timestamp": datetime.now().isoformat()
    }), 200


# ========== ERROR HANDLERS ==========

@app.errorhandler(413)
def request_entity_too_large(error):
    """Обработка ошибки слишком большого файла."""
    return jsonify({
        "status": "error",
        "message": "Файл слишком большой. Максимум: 50 МБ"
    }), 413


@app.errorhandler(405)
def method_not_allowed(error):
    """Обработка неправильного метода."""
    return jsonify({
        "status": "error",
        "message": "Метод не разрешён"
    }), 405


@app.errorhandler(404)
def not_found(error):
    """Обработка несуществующего маршрута."""
    return jsonify({
        "status": "error",
        "message": "Маршрут не найден"
    }), 404


# ========== ЗАПУСК ПРИЛОЖЕНИЯ ==========

if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("🚀 ЗАПУСК API СЕРВЕРА")
    print("=" * 80)
    print(f"📍 Адрес: http://localhost:5001")
    print(
        f"📝 GigaChat Auth Key: {'✅ Установлен' if GIGACHAT_AUTH_KEY == 'ENTER_KEY' else '⚠️  ИСПОЛЬЗУЕТСЯ ЗНАЧЕНИЕ ПО УМОЛЧАНИЮ'}")
    print(f"📂 Папка загрузок: {UPLOAD_FOLDER}")
    print("=" * 80 + "\n")

    app.run(
        host="0.0.0.0",
        port=5001,
        debug=True,
        use_reloader=False
    )

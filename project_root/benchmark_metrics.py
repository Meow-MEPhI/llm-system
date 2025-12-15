"""
Скрипт для бенчмарка LLM-as-a-Judge системы.
Читает статьи из папки test_articles/, обрабатывает их и собирает метрики.
"""

import os
import sys
import time
import json
from datetime import datetime
from typing import List, Dict
import statistics
from dotenv import load_dotenv
import glob

# Добавляем путь к модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agent_system'))

from agent_system.graph_orchestrator import create_multi_agent_graph

# Загрузка переменных окружения
load_dotenv()


# ==================== МЕТРИКИ ====================

class MetricsCollector:
    def __init__(self):
        self.runs: List[Dict] = []

    def add_run(self, run_data: Dict):
        """Добавляет результат запуска"""
        self.runs.append(run_data)

    def calculate_statistics(self) -> Dict:
        """Вычисляет статистику по всем запускам"""
        if not self.runs:
            return {}

        latencies = [r['latency'] for r in self.runs if 'latency' in r and r['status'] == 'success']
        tokens = [r['total_tokens'] for r in self.runs if 'total_tokens' in r and r['status'] == 'success']
        errors = [r for r in self.runs if r.get('status') == 'error']

        return {
            'total_runs': len(self.runs),
            'successful_runs': len(self.runs) - len(errors),
            'error_rate': len(errors) / len(self.runs) * 100 if self.runs else 0,
            'latency': {
                'mean': statistics.mean(latencies) if latencies else 0,
                'median': statistics.median(latencies) if latencies else 0,
                'p95': self._percentile(latencies, 0.95) if latencies else 0,
                'p99': self._percentile(latencies, 0.99) if latencies else 0,
                'min': min(latencies) if latencies else 0,
                'max': max(latencies) if latencies else 0,
            },
            'tokens': {
                'mean': statistics.mean(tokens) if tokens else 0,
                'median': statistics.median(tokens) if tokens else 0,
                'total': sum(tokens) if tokens else 0,
                'min': min(tokens) if tokens else 0,
                'max': max(tokens) if tokens else 0,
            },
            'errors': errors
        }

    @staticmethod
    def _percentile(data: List[float], percentile: float) -> float:
        """Вычисляет перцентиль"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile)
        return sorted_data[min(index, len(sorted_data) - 1)]

    def print_report(self):
        """Выводит красивый отчёт"""
        stats = self.calculate_statistics()

        print("\n" + "=" * 80)
        print("📊 ОТЧЁТ ПО МЕТРИКАМ LLM-AS-A-JUDGE")
        print("=" * 80)

        print(f"\n📈 Общая статистика:")
        print(f"  • Всего запусков: {stats['total_runs']}")
        print(f"  • Успешных: {stats['successful_runs']}")
        print(f"  • Процент ошибок: {stats['error_rate']:.2f}%")

        if stats['latency']['mean'] > 0:
            print(f"\n⏱️  Latency (задержка):")
            print(f"  • Среднее: {stats['latency']['mean']:.2f} сек")
            print(f"  • Медиана (P50): {stats['latency']['median']:.2f} сек")
            print(f"  • P95: {stats['latency']['p95']:.2f} сек")
            print(f"  • P99: {stats['latency']['p99']:.2f} сек")
            print(f"  • Min / Max: {stats['latency']['min']:.2f} / {stats['latency']['max']:.2f} сек")

        if stats['tokens']['total'] > 0:
            print(f"\n🪙 Токены:")
            print(f"  • Среднее на запуск: {stats['tokens']['mean']:.0f}")
            print(f"  • Медиана: {stats['tokens']['median']:.0f}")
            print(f"  • Всего потрачено: {stats['tokens']['total']:,}")
            print(f"  • Min / Max: {stats['tokens']['min']:.0f} / {stats['tokens']['max']:.0f}")

        if stats['errors']:
            print(f"\n❌ Ошибки ({len(stats['errors'])}):")
            for i, err in enumerate(stats['errors'][:5], 1):  # Первые 5
                print(f"  {i}. {err.get('title', 'Unknown')}: {err.get('error_message', 'Unknown error')[:80]}...")

        print("\n" + "=" * 80)

        # Сохраняем в JSON
        report_file = f"metrics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'statistics': stats,
                'runs': self.runs
            }, f, indent=2, ensure_ascii=False)

        print(f"💾 Полный отчёт сохранён в: {report_file}\n")


# ==================== ЗАГРУЗКА СТАТЕЙ ====================

def load_articles_from_folder(folder_path: str = 'test_articles') -> List[Dict[str, str]]:
    """Загружает все статьи из указанной папки"""
    if not os.path.exists(folder_path):
        print(f"❌ Папка '{folder_path}' не найдена!")
        print(f"💡 Сначала запустите: python generate_test_articles.py")
        return []

    articles = []
    txt_files = sorted(glob.glob(os.path.join(folder_path, '*.txt')))

    if not txt_files:
        print(f"❌ В папке '{folder_path}' нет .txt файлов!")
        return []

    for filepath in txt_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            filename = os.path.basename(filepath)
            title = content.split('\n')[0] if content else filename  # Первая строка как заголовок

            articles.append({
                'filename': filename,
                'title': title[:100],  # Обрезаем длинные заголовки
                'text': content
            })
        except Exception as e:
            print(f"⚠️  Ошибка чтения {filepath}: {e}")

    return articles


# ==================== ЗАПУСК БЕНЧМАРКА ====================

def run_benchmark(num_articles: int = None):
    """Запускает бенчмарк на статьях из папки"""

    print("\n" + "🚀 ЗАПУСК БЕНЧМАРКА LLM-AS-A-JUDGE" + "\n")
    print(f"Время старта: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Проверка AUTH KEY
    auth_key = os.getenv('GIGACHAT_AUTH_KEY')
    if not auth_key:
        print("❌ GIGACHAT_AUTH_KEY не найден в .env!")
        return

    # Загрузка статей
    print("\n📁 Загрузка статей из папки 'test_articles/'...")
    articles = load_articles_from_folder()

    if not articles:
        return

    # Ограничиваем количество, если указано
    if num_articles:
        articles = articles[:num_articles]

    print(f"✅ Загружено {len(articles)} статей\n")

    # Инициализация
    collector = MetricsCollector()

    try:
        # Создаём граф один раз
        print("🔧 Инициализация графа агентов...")
        graph = create_multi_agent_graph(auth_key=auth_key)
        print("✅ Граф создан успешно\n")
    except Exception as e:
        print(f"❌ Ошибка создания графа: {e}")
        return

    # Обработка статей
    for idx, article in enumerate(articles, 1):
        print(f"\n{'─' * 80}")
        print(f"📄 Статья {idx}/{len(articles)}: {article['filename']}")
        print(f"📝 {article['title'][:70]}...")
        print(f"{'─' * 80}")

        start_time = time.time()

        initial_state = {
            "article_text": article['text'],
            "rubric_result_rubricator": "",
            "rubric_result_keyword": "",
            "rubric_result_normal": "",
            "rubric_result_summariser": "",
            "critique": "",
            "critique_key": "",
            "critique_sum": "",
            "critique_nor": "",
            "revision_count": 0,
            "revision_count_key": 0,
            "revision_count_sum": 0,
            "revision_count_nor": 0,
            "status": ["started"]
        }

        try:
            # Запускаем граф
            final_state = graph.invoke(initial_state)

            latency = time.time() - start_time

            # Примерный подсчёт токенов (длина текста / 4)
            total_tokens = (
                                   len(article['text']) +
                                   len(final_state.get('rubric_result_rubricator', '')) +
                                   len(final_state.get('rubric_result_keyword', '')) +
                                   len(final_state.get('rubric_result_normal', '')) +
                                   len(final_state.get('rubric_result_summariser', ''))
                           ) // 4

            run_data = {
                'article_id': idx,
                'filename': article['filename'],
                'title': article['title'],
                'status': 'success',
                'latency': latency,
                'total_tokens': total_tokens,
                'revision_count': final_state.get('revision_count', 0),
                'results': {
                    'rubric': final_state.get('rubric_result_rubricator', '')[:100],
                    'keywords': final_state.get('rubric_result_keyword', '')[:100],
                    'summary': final_state.get('rubric_result_summariser', '')[:100],
                }
            }

            collector.add_run(run_data)

            print(f"✅ Успешно обработана за {latency:.2f}с (≈{total_tokens:,} токенов)")
            print(f"   🏷️  Рубрика: {run_data['results']['rubric'][:60]}...")

        except Exception as e:
            latency = time.time() - start_time
            error_msg = str(e)

            run_data = {
                'article_id': idx,
                'filename': article['filename'],
                'title': article['title'],
                'status': 'error',
                'latency': latency,
                'error_message': error_msg
            }

            collector.add_run(run_data)

            print(f"❌ Ошибка: {error_msg[:150]}")

        # Небольшая пауза между запросами
        if idx < len(articles):
            time.sleep(2)

    # Итоговый отчёт
    collector.print_report()


# ==================== MAIN ====================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Бенчмарк LLM-as-a-Judge системы')
    parser.add_argument('-n', '--num', type=int, default=None,
                        help='Количество статей для обработки (по умолчанию: все)')

    args = parser.parse_args()

    run_benchmark(num_articles=args.num)

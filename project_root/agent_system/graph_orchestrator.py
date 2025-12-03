# graph_orchestrator.py

from typing import TypedDict, Annotated, List, Literal
from langgraph.graph import StateGraph, START, END
import time
import operator
import os

# Исправленные импорты - относительные пути
# from .agent_bibliographer import BibliographerAgent
from .agent_rubricator import RubricatorAgent
from .agent_keyword import KeywordAgent
from .agent_summariser import SummariserAgent
from .agent_normal import NormalAgent
from .rubricator_critic import CriticAgent
from .keyword_critic import CriticKeywordAgent
from .summariser_critic import CriticSumAgent
from .normal_critic import CriticNormalAgent


def should_continue_or_revise(state: dict) -> Literal["continue", "revise", "max_retries"]:
    """Решает, продолжать дальше или вернуться на переделку."""

    # Проверяем счетчик попыток
    try:
        revision_count = state.get("revision_count", 0)
    except:
        pass

    try:
        revision_count = state.get("revision_count_key", 0)
    except:
        pass

    try:
        revision_count = state.get("revision_count_sum", 0)
    except:
        pass

    try:
        revision_count = state.get("revision_count_nor", 0)
    except:
        pass


    MAX_REVISIONS = 1

    if revision_count >= MAX_REVISIONS:
        return "max_retries"

    # Проверяем статус критика
    status_list = state.get("status", [])

    if "critic_rejected" in status_list:
        return "revise"
    elif "critic_approved" in status_list:
        return "continue"

    return "continue"


def saferun(func, state: dict):
    """Безопасное выполнение функции агента с повторами."""
    while True:
        try:
            time.sleep(1)
            return func(state)
        except Exception as e:
            print(f"⚠️  Ошибка в saferun: {e}")
            print(func)
            continue


# Определяем состояние графа
class GraphState(TypedDict):
    """Общее состояние для всех узлов графа."""
    article_text: str

    rubric_result_keyword: str
    rubric_result_rubricator: str
    rubric_result_normal: str
    rubric_result_summariser: str

    critique: str
    critique_key: str
    critique_sum: str
    critique_nor: str

    revision_count: int
    revision_count_key: int
    revision_count_sum: int
    revision_count_nor: int
    status: Annotated[List[str], operator.add]


def create_multi_agent_graph(auth_key: str):
    """Создаёт многоагентный граф обработки статей."""

    print("📍 Инициализация агентов...")

    # Инициализируем агентов с ключом GigaChat
    try:

        rubricator = RubricatorAgent(auth_key=auth_key)
        print("✅ RubricatorAgent инициализирован")

        keyword = KeywordAgent(auth_key=auth_key)
        print("✅ KeywordAgent инициализирован")

        normal = NormalAgent(auth_key=auth_key)
        print("✅ NormalAgent инициализирован")

        summariser = SummariserAgent(auth_key=auth_key)
        print("✅ SummariserAgent инициализирован")

        critic_r = CriticAgent(auth_key=auth_key)
        print("✅ CriticAgent инициализирован")

        critic_k = CriticKeywordAgent(auth_key=auth_key)
        print("✅ Critic2Agent инициализирован")

        critic_sum = CriticSumAgent(auth_key=auth_key)
        print("✅ CriticSumAgent инициализирован")

        critic_nor = CriticNormalAgent(auth_key=auth_key)
        print("✅ CriticNormalAgent инициализирован")

    except Exception as e:
        print(f"❌ Ошибка инициализации агентов: {e}")
        raise

    # Создаем граф состояний
    workflow = StateGraph(GraphState)

    # Добавляем узлы (агентов) в граф
    # workflow.add_node("bibliographer", lambda state: saferun(bibliographer.run, state))
    workflow.add_node("rubricator", lambda state: saferun(rubricator.run, state))
    workflow.add_node("critic_r", lambda state: saferun(critic_r.run, state))
    workflow.add_node("keyword", lambda state: saferun(keyword.run, state))
    workflow.add_node("critic_k", lambda state: saferun(critic_k.run, state))
    workflow.add_node("normal", lambda state: saferun(normal.run, state))
    workflow.add_node("critic_nor", lambda state: saferun(critic_nor.run, state))
    workflow.add_node("summariser", lambda state: saferun(summariser.run, state))
    workflow.add_node("critic_sum", lambda state: saferun(critic_sum.run, state))

    # Определяем последовательность выполнения
    # workflow.add_edge(START, "bibliographer")
    workflow.add_edge(START, "rubricator")
    workflow.add_edge("rubricator", "critic_r")
    workflow.add_conditional_edges(
        "critic_r",
        should_continue_or_revise,
        {
            "revise": "rubricator",  # Возврат на переделку
            "continue": END,  # Переход к следующему агенту
            "max_retries": END  # Если превышен лимит, идём дальше
        }
    )

    # Параллельные пути от библиографа
    workflow.add_edge(START, "keyword")
    workflow.add_edge("keyword", "critic_k")
    workflow.add_conditional_edges(
        "critic_k",
        should_continue_or_revise,
        {
            "revise": "keyword",  # Возврат на переделку
            "continue": END,  # Переход к следующему агенту
            "max_retries": END  # Если превышен лимит, идём дальше
        }
    )

    workflow.add_edge(START, "normal")
    workflow.add_edge("normal", "critic_nor")
    workflow.add_conditional_edges(
        "critic_nor",
        should_continue_or_revise,
        {
            "revise": "normal",  # Возврат на переделку
            "continue": END,  # Переход к следующему агенту
            "max_retries": END  # Если превышен лимит, идём дальше
        }
    )

    workflow.add_edge(START, "summariser")
    workflow.add_edge("summariser", "critic_sum")
    workflow.add_conditional_edges(
        "critic_sum",
        should_continue_or_revise,
        {
            "revise": "summariser",  # Возврат на переделку
            "continue": END,  # Переход к следующему агенту
            "max_retries": END  # Если превышен лимит, идём дальше
        }
    )



    # Компилируем граф
    print("🔧 Компиляция графа...")
    graph = workflow.compile()
    print("✅ Граф успешно скомпилирован")

    return graph


if __name__ == "__main__":
    AUTH_KEY = "YOUR_KEY"
    
    graph = create_multi_agent_graph(AUTH_KEY)

    initial_state = {
        "article_text": "",
        "rubric_result_rubricator": "",
        "rubric_result_keyword": "",
        "rubric_result_normal": "",
        "rubric_result_summariser": "",

        "critique": "",
        "critique_key": "",
        "critique_sum": "",
        "critique_normal": "",

        "revision_count": 0,
        "revision_count_key": 0,
        "revision_count_sum": 0,
        "revision_count_nor": 0,
        "status": ["started"]
    }

    # Выполняем граф
    final_state = graph.invoke(initial_state)

    # Сохранить структуру в файл
    try:
        png_data = graph.get_graph().draw_mermaid_png()
        with open("graph_visualization.png", "wb") as f:
            f.write(png_data)
        print("✅ Визуализация графа сохранена")
    except Exception as e:
        print(f"⚠️  Не удалось сохранить визуализацию: {e}")

    print("\n" + "=" * 80)
    print("РЕЗУЛЬТАТЫ ОБРАБОТКИ:")
    print("=" * 80)
    print(f"Рубрицирование:\n{final_state['rubric_result_rubricator']}\n")
    print(f"Количество ревизий: {final_state['revision_count']}")

    print(f"Саммари:\n{final_state['rubric_result_summariser']}\n")
    print(f"Количество ревизий: {final_state['revision_count_sum']}")

    print("=" * 80)
    print(f"нормализация:\n{final_state['rubric_result_normal']}\n")
    print(f"Количество ревизий: {final_state['revision_count_nor']}")

    print("=" * 80)
    print(f"Суммаризация:\n{final_state['rubric_result_keyword']}\n")
    print(f"Количество ревизий: {final_state['revision_count_key']}")


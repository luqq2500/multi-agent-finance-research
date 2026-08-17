from langchain_core.tools import tool
from tavily import TavilyClient

@tool
def finance_web_search(query: str):
    """
    search dedicated financial markets related research from web.
    """
    engine = TavilyClient()
    results = engine.search(
        query=query,
        include_answer="advanced",
        topic="finance",
        search_depth="advanced",
        max_results=10
    )
    return results

@tool
def general_web_search(query: str):
    """
    search general financial markets research related from web.
    """
    engine = TavilyClient()
    results = engine.search(
        query=query,
        include_answer="advanced",
        search_depth="advanced",
        max_results=10
    )
    return results
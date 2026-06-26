"""
Search Agent: Tavily-powered real-time web search with result summarization.
"""

import time
from typing import Any, Dict, List, Optional, Tuple

import structlog
from tavily import TavilyClient

from gateway.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class SearchAgent:
    def __init__(self):
        self.client = TavilyClient(api_key=settings.tavily_api_key)

    async def search(
        self,
        query: str,
        max_results: int = 5,
        search_depth: str = "advanced",
        include_domains: Optional[List[str]] = None,
    ) -> Tuple[List[Dict[str, Any]], float]:
        """
        Perform web search. Returns (results, latency_ms).
        Each result: {title, url, content, score}
        """
        t0 = time.monotonic()
        try:
            response = self.client.search(
                query=query,
                max_results=max_results,
                search_depth=search_depth,
                include_domains=include_domains or [],
                include_answer=True,
            )

            results = []
            for r in response.get("results", []):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", "")[:1000],  # cap per result
                    "score": r.get("score", 0.0),
                })

            # Also include Tavily's synthesized answer if present
            if response.get("answer"):
                results.insert(0, {
                    "title": "Synthesized Answer",
                    "url": "",
                    "content": response["answer"],
                    "score": 1.0,
                })

            latency = (time.monotonic() - t0) * 1000
            logger.info("search_complete", query=query[:50], results=len(results), latency_ms=round(latency, 1))
            return results, latency

        except Exception as e:
            latency = (time.monotonic() - t0) * 1000
            logger.error("search_failed", query=query[:50], error=str(e))
            return [], latency

    def format_results(self, results: List[Dict[str, Any]]) -> str:
        """Format search results into a prompt-ready block."""
        if not results:
            return "No web search results found."

        lines = ["## Web Search Results\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"**[{i}] {r['title']}**")
            if r["url"]:
                lines.append(f"Source: {r['url']}")
            lines.append(r["content"])
            lines.append("")
        return "\n".join(lines)


_search_agent: Optional[SearchAgent] = None


def get_search_agent() -> SearchAgent:
    global _search_agent
    if _search_agent is None:
        _search_agent = SearchAgent()
    return _search_agent

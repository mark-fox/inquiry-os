from __future__ import annotations

from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str


@dataclass(frozen=True)
class DuckDuckGoClient:
    timeout_s: float = 10.0

    async def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        # DuckDuckGo HTML endpoint (no JS)
        url = "https://duckduckgo.com/html/"
        params = {"q": query}

        async with httpx.AsyncClient(timeout=self.timeout_s, follow_redirects=True) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")

        results: list[SearchResult] = []
        for a in soup.select("a.result__a"):
            title = a.get_text(strip=True)
            href = a.get("href")
            if not href:
                continue
            results.append(SearchResult(title=title, url=href))
            if len(results) >= limit:
                break

        return results
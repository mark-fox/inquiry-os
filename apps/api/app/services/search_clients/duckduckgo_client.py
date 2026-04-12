from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlparse

import httpx
from bs4 import BeautifulSoup


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str


@dataclass(frozen=True)
class DuckDuckGoClient:
    timeout_s: float = 10.0

    def _clean_duckduckgo_href(self, href: str) -> str:
        """
        DuckDuckGo sometimes wraps outbound URLs like:
        /l/?uddg=https%3A%2F%2Fexample.com...
        This extracts the real destination URL.
        """
        if href.startswith("//"):
            return "https:" + href

        if href.startswith("/l/?"):
            parsed = urlparse(href)
            query = parse_qs(parsed.query)
            uddg = query.get("uddg")
            if uddg:
                return unquote(uddg[0])

        return href

    async def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        url = "https://html.duckduckgo.com/html/"
        params = {"q": query}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        }

        async with httpx.AsyncClient(
            timeout=self.timeout_s,
            follow_redirects=True,
            headers=headers,
        ) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")

        results: list[SearchResult] = []

        # Primary selector
        for a in soup.select("a.result__a"):
            title = a.get_text(" ", strip=True)
            href = a.get("href")
            if not href:
                continue

            cleaned_url = self._clean_duckduckgo_href(href)
            if not cleaned_url.startswith(("http://", "https://")):
                continue

            results.append(SearchResult(title=title, url=cleaned_url))
            if len(results) >= limit:
                return results

        # Fallback selector for alternate DDG HTML layouts
        for result in soup.select(".result"):
            a = result.select_one("a[href]")
            if a is None:
                continue

            title = a.get_text(" ", strip=True)
            href = a.get("href")
            if not href:
                continue

            cleaned_url = self._clean_duckduckgo_href(href)
            if not cleaned_url.startswith(("http://", "https://")):
                continue

            # Avoid duplicates
            if any(existing.url == cleaned_url for existing in results):
                continue

            results.append(SearchResult(title=title, url=cleaned_url))
            if len(results) >= limit:
                return results

        return results
from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from typing import Final
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


_MAX_BYTES: Final[int] = 1_000_000  # 1 MB
_USER_AGENT: Final[str] = "InquiryOS/0.1 (Research Reader)"


class UnsafeUrlError(Exception):
    pass


@dataclass(frozen=True)
class FetchedPage:
    url: str
    status_code: int
    html: str


def _is_private_or_local_ip(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
    )


def _validate_url(url: str) -> None:
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise UnsafeUrlError("Only http/https URLs are allowed.")

    if not parsed.netloc:
        raise UnsafeUrlError("URL must include a hostname.")

    host = parsed.hostname or ""
    if host in {"localhost"}:
        raise UnsafeUrlError("Localhost URLs are not allowed.")

    # If hostname is an IP, block private/local ranges
    if _is_private_or_local_ip(host):
        raise UnsafeUrlError("Private/local IP URLs are not allowed.")


async def _fetch_html_with_client(url: str, client: httpx.AsyncClient) -> FetchedPage:
    async with client.stream("GET", url) as resp:
        resp.raise_for_status()

        chunks: list[bytes] = []
        total = 0
        async for chunk in resp.aiter_bytes():
            if not chunk:
                continue
            chunks.append(chunk)
            total += len(chunk)
            if total > _MAX_BYTES:
                raise httpx.HTTPError("Response too large")

        content = b"".join(chunks)

    html = content.decode("utf-8", errors="replace")
    return FetchedPage(url=url, status_code=200, html=html)


async def fetch_html(
    url: str,
    timeout_s: float = 10.0,
    *,
    client: httpx.AsyncClient | None = None,
) -> FetchedPage:
    _validate_url(url)

    headers = {"User-Agent": _USER_AGENT}

    # If a client is provided, reuse it. Otherwise create a one-off client.
    if client is None:
        async with httpx.AsyncClient(
            timeout=timeout_s,
            follow_redirects=True,
            headers=headers,
        ) as local_client:
            return await _fetch_html_with_client(url, local_client)
    else:
        # Ensure headers exist even on a shared client (best-effort, don't mutate if already set)
        if "User-Agent" not in client.headers:
            client.headers.update(headers)
        return await _fetch_html_with_client(url, client)


def extract_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")

    # Remove noisy tags
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def basic_summary(text: str, max_chars: int = 800) -> str:
    if not text:
        return ""

    # Simple: take the first max_chars of cleaned text
    return text[:max_chars].strip()
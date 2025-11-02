"""HTTPクライアント共通処理モジュール."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

DEFAULT_HEADERS: Final[dict[str, str]] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    ),
}
REQUEST_TIMEOUT: Final[int] = 10


@dataclass(slots=True)
class NonSvPageError(RuntimeError):
    """ポケモンSV図鑑以外のページへ遷移した場合の例外."""

    final_url: str

    def __str__(self) -> str:
        return f"Redirected to non-SV catalogue page: {self.final_url}"


@dataclass(slots=True)
class RedirectedToZaError(NonSvPageError):
    """ポケモンZAページへリダイレクトされた場合の例外."""

    def __str__(self) -> str:
        return f"Redirected to ZA catalogue page: {self.final_url}"


def fetch_pokemon_soup(url: str) -> BeautifulSoup:
    """指定URLのHTMLを取得しBeautifulSoupオブジェクトを返す.

    CloudFlare対策としてUser-Agentを偽装し、HTMLのエンコーディングを自動検出する。

    Args:
        url: スクレイピング対象のページURL

    Returns:
        BeautifulSoupオブジェクト

    Raises:
        requests.HTTPError: HTTPリクエストが失敗した場合
        RedirectedToZaError: SV図鑑からZA図鑑へリダイレクトされた場合
        NonSvPageError: ポケモンSV図鑑以外のページに遷移した場合
    """
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    parsed = urlparse(response.url)
    if parsed.path.startswith("/za/"):
        raise RedirectedToZaError(response.url)
    if not parsed.path.startswith("/sv/"):
        raise NonSvPageError(response.url)
    # EUC-JP等のレガシーエンコーディングにも対応するためbytesから直接解析する
    encoding = response.encoding or ""
    if encoding.lower() == "iso-8859-1":
        encoding = ""
    bs_encoding = encoding or response.apparent_encoding
    return BeautifulSoup(response.content, "html.parser", from_encoding=bs_encoding)

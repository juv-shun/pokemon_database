"""HTTPクライアント共通処理モジュール."""

from __future__ import annotations

from typing import Final

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


def fetch_pokemon_soup(url: str) -> BeautifulSoup:
    """指定URLのHTMLを取得しBeautifulSoupオブジェクトを返す.

    CloudFlare対策としてUser-Agentを偽装し、HTMLのエンコーディングを自動検出する。

    Args:
        url: スクレイピング対象のページURL

    Returns:
        BeautifulSoupオブジェクト

    Raises:
        requests.HTTPError: HTTPリクエストが失敗した場合
    """
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    # EUC-JP等のレガシーエンコーディングにも対応するためbytesから直接解析する
    encoding = response.encoding or ""
    if encoding.lower() == "iso-8859-1":
        encoding = ""
    bs_encoding = encoding or response.apparent_encoding
    return BeautifulSoup(response.content, "html.parser", from_encoding=bs_encoding)

"""ポケモン特性情報のスクレイピングモジュール."""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup, Tag


def scrape_pokemon_abilities(soup: BeautifulSoup) -> list[dict[str, Any]]:
    """ポケモン図鑑ページから特性情報を抽出する.

    Args:
        soup: ポケモン図鑑ページのBeautifulSoupオブジェクト

    Returns:
        特性情報の辞書リスト
            - name_ja: 特性名
            - effect_text: 効果説明
            - is_hidden: 夢特性フラグ
    """
    ability_table = _find_ability_table(soup)
    if ability_table is None:
        return []

    abilities: list[dict[str, Any]] = []
    in_ability_section = False
    current_hidden = False

    for row in ability_table.find_all("tr"):
        header_cell = row.find("th")
        if header_cell:
            header_text = header_cell.get_text(strip=True)
            if "特性" in header_text:
                in_ability_section = True
                current_hidden = "隠れ" in header_text or "夢特性" in header_text
                continue

            if in_ability_section:
                # 特性以外のセクションに移行したら終了
                break

        if not in_ability_section:
            continue

        cells = row.find_all("td")
        if len(cells) != 2:
            continue

        raw_name = cells[0].get_text(strip=True)
        if not raw_name:
            continue

        is_hidden = current_hidden or raw_name.startswith("*")
        name = raw_name.lstrip("*")
        effect_text = cells[1].get_text(strip=True)

        abilities.append(
            {
                "name_ja": name,
                "effect_text": effect_text,
                "is_hidden": is_hidden,
            }
        )

    return abilities


def _find_ability_table(soup: BeautifulSoup) -> Tag | None:
    """特性情報を含むテーブル要素を検索する."""
    for table in soup.find_all("table"):
        for header in table.find_all("th"):
            header_text = header.get_text(strip=True)
            if "特性" in header_text:
                return table
    return None

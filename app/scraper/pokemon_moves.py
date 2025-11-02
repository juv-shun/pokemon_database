"""ポケモン技情報のスクレイピングモジュール."""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

_PRIORITY_PATTERN = re.compile(r"優先度[:：]?\s*([+-]?\d+)")
_DAMAGE_CLASS_MAP = {
    "物理": "physical",
    "特殊": "special",
    "変化": "status",
}


def scrape_pokemon_moves(soup: BeautifulSoup) -> list[dict[str, Any]]:
    """ポケモン図鑑ページから技情報を抽出する.

    Args:
        soup: ポケモン図鑑ページのBeautifulSoupオブジェクト

    Returns:
        技情報の辞書リスト
            - name_ja: 技名
            - type_name: タイプ名
            - damage_class: ダメージ区分 (physical/special/status)
            - power: 威力
            - accuracy: 命中率
            - pp: PP
            - priority: 優先度
            - effect_text: 効果説明
            - notes: 習得条件や備考
    """
    move_table = soup.find("table", id="move_list")
    if move_table is None:
        return []

    moves: list[dict[str, Any]] = []
    current_section = ""
    pending_move: dict[str, Any] | None = None

    for row in move_table.find_all("tr"):
        classes = row.get("class", [])
        if "move_head" in classes:
            current_section = _normalize_space(row.get("data-label") or row.get_text(strip=True))
            continue

        if "move_head2" in classes:
            continue

        if "move_main_row" in classes:
            pending_move = _parse_move_main_row(row, current_section)
            continue

        if "move_detail_row" in classes and pending_move is not None:
            move_entry = _compose_move_entry(row, pending_move)
            moves.append(move_entry)
            pending_move = None

    return moves


def _parse_move_main_row(row: Tag, current_section: str) -> dict[str, Any]:
    """技名や習得条件などメイン行の情報を抽出する."""
    condition_cell = row.find("td", class_="move_condition_cell")
    condition_text = _normalize_space(condition_cell.get_text(strip=True)) if condition_cell else ""
    condition_text = _normalize_condition(condition_text)

    name_cell = row.find("td", class_="move_name_cell")
    name_link = name_cell.find("a") if name_cell else None

    raw_name = ""
    if name_link is not None:
        raw_name = name_link.get_text(strip=True)
    elif name_cell is not None:
        raw_name = name_cell.get_text(strip=True)
    name_text = _normalize_space(raw_name)

    extra_info = ""
    if name_cell is not None:
        extra_info = " ".join(
            _normalize_space(span.get_text(strip=True))
            for span in name_cell.find_all("span", class_="small")
        )

    note_parts: list[str] = []
    if condition_text:
        note_parts.append(condition_text)
    elif current_section:
        note_parts.append(current_section)
    if extra_info:
        note_parts.append(extra_info)

    notes = " ".join(note_parts).strip() or None

    return {
        "name_ja": name_text,
        "notes": notes,
    }


def _compose_move_entry(detail_row: Tag, base_info: dict[str, Any]) -> dict[str, Any]:
    """メイン行と詳細行を組み合わせて最終的な技情報を構築する."""
    cells = detail_row.find_all("td")
    type_name = cells[0].get_text(strip=True) if len(cells) > 0 else ""
    damage_class_text = cells[1].get_text(strip=True) if len(cells) > 1 else ""
    power_text = cells[2].get_text(strip=True) if len(cells) > 2 else ""
    accuracy_text = cells[3].get_text(strip=True) if len(cells) > 3 else ""
    pp_text = cells[4].get_text(strip=True) if len(cells) > 4 else ""
    effect_text = cells[6].get_text(strip=True) if len(cells) > 6 else ""

    priority = _extract_priority(effect_text)

    return {
        "name_ja": base_info["name_ja"],
        "type_name": type_name or None,
        "damage_class": _DAMAGE_CLASS_MAP.get(damage_class_text, None),
        "power": _parse_optional_int(power_text),
        "accuracy": _parse_optional_int(accuracy_text),
        "pp": _parse_optional_int(pp_text),
        "priority": priority if priority is not None else 0,
        "effect_text": effect_text or None,
        "notes": base_info.get("notes"),
    }


def _parse_optional_int(value: str) -> int | None:
    """数値が取得できない場合Noneを返却する."""
    cleaned = value.replace("−", "-").replace("ー", "-").replace("―", "-").replace("—", "-").strip()
    if not cleaned or cleaned in {"-", "--"}:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def _extract_priority(effect_text: str) -> int | None:
    """効果テキストから優先度情報を抽出する."""
    match = _PRIORITY_PATTERN.search(effect_text)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None
    return None


def _normalize_space(value: str) -> str:
    """全角スペースを含む文字列の余分な空白を削除する."""
    return value.replace("\xa0", " ").strip()


def _normalize_condition(condition_text: str) -> str:
    """習得条件テキストの表記揺れを吸収する."""
    if condition_text.startswith("Lv."):
        return condition_text.replace("Lv.", "レベル", 1)
    if condition_text.startswith("Lv"):
        return condition_text.replace("Lv", "レベル", 1)
    return condition_text

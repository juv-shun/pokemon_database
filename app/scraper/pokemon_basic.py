"""ポケモン基本情報のスクレイピングモジュール."""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup


def scrape_pokemon_basic(soup: BeautifulSoup) -> dict[str, Any]:
    """ポケモン図鑑ページからポケモン基本情報を抽出する.

    Args:
        soup: ポケモン図鑑ページのBeautifulSoupオブジェクト

    Returns:
        pokemon テーブルの情報を含む辞書

    Raises:
        ValueError: 必要なデータが取得できなかった場合
    """

    # 基本情報テーブル（最初のテーブル）を取得
    tables = soup.find_all("table")
    if not tables:
        raise ValueError("テーブルが見つかりません")

    basic_info_table = tables[0]
    rows = basic_info_table.find_all("tr")

    # 初期化
    pokemon_data: dict[str, Any] = {
        "pokedex_no": None,
        "name_ja": None,
        "name_en": None,
        "form_label": None,
        "type_primary": None,
        "type_secondary": None,
        "height_dm": None,
        "weight_hg": None,
        "low_kick_power": None,
        "is_legendary": False,
        "is_mythical": False,
        "base_hp": None,
        "base_atk": None,
        "base_def": None,
        "base_spa": None,
        "base_spd": None,
        "base_spe": None,
        "remarks": None,
    }

    # ポケモン名の抽出
    h1 = soup.find("h1")
    if h1:
        h1_text = h1.get_text(strip=True)
        # "ボルトロス- ポケモン図鑑SV" から "ボルトロス" を抽出
        name_match = re.match(r"(.+?)-\s*ポケモン図鑑", h1_text)
        if name_match:
            pokemon_data["name_ja"] = name_match.group(1).strip()

    # 各行から情報を抽出
    for row in rows:
        cells = row.find_all(["th", "td"])
        if len(cells) >= 2:
            key = cells[0].get_text(strip=True)
            value = cells[1].get_text(strip=True)

            if key == "全国No." or key == "ぜんこくNo.":
                digits_match = re.search(r"(\d+)", value)
                if digits_match:
                    pokemon_data["pokedex_no"] = int(digits_match.group(1))
            elif key == "英語名":
                pokemon_data["name_en"] = value
            elif key == "高さ":
                # "1.5m" -> 15 (デシメートル)
                height_match = re.search(r"([\d.]+)m", value)
                if height_match:
                    pokemon_data["height_dm"] = int(float(height_match.group(1)) * 10)
            elif key == "重さ":
                # "61.0kgけたぐり威力80" から重さとけたぐり威力を抽出
                weight_match = re.search(r"([\d.]+)kg", value)
                if weight_match:
                    pokemon_data["weight_hg"] = int(float(weight_match.group(1)) * 10)
                kick_match = re.search(r"けたぐり威力(\d+)", value)
                if kick_match:
                    pokemon_data["low_kick_power"] = int(kick_match.group(1))
            elif key == "タイプ":
                # タイプ画像からalt属性を取得
                type_imgs = cells[1].find_all("img")
                if len(type_imgs) >= 1:
                    pokemon_data["type_primary"] = type_imgs[0].get("alt")
                if len(type_imgs) >= 2:
                    pokemon_data["type_secondary"] = type_imgs[1].get("alt")

    # 種族値テーブル（2番目のテーブル）から種族値を抽出
    if len(tables) > 1:
        stats_table = tables[1]
        stats_rows = stats_table.find_all("tr")

        # 種族値は見出しの後の連続した6行に含まれる
        # "◆ {ポケモン名}の種族値" の後の行から抽出
        in_base_stats_section = False

        for row in stats_rows:
            cells = row.find_all(["th", "td"])
            if not cells:
                continue

            first_cell_text = cells[0].get_text(strip=True)

            # 種族値セクションの開始を検出
            if "の種族値" in first_cell_text:
                in_base_stats_section = True
                continue

            # 種族値セクション以外（努力値など）に入ったら終了
            if in_base_stats_section and (
                "努力値" in first_cell_text or "実数値" in first_cell_text
            ):
                in_base_stats_section = False
                break

            # 種族値セクション内で値を抽出
            if in_base_stats_section and len(cells) >= 2:
                stat_name = first_cell_text
                stat_value_text = cells[1].get_text(strip=True)

                # "79(345位)" から "79" を抽出
                stat_match = re.match(r"(\d+)", stat_value_text)
                if stat_match:
                    stat_value = int(stat_match.group(1))

                    if stat_name == "HP":
                        pokemon_data["base_hp"] = stat_value
                    elif stat_name == "こうげき":
                        pokemon_data["base_atk"] = stat_value
                    elif stat_name == "ぼうぎょ":
                        pokemon_data["base_def"] = stat_value
                    elif stat_name == "とくこう":
                        pokemon_data["base_spa"] = stat_value
                    elif stat_name == "とくぼう":
                        pokemon_data["base_spd"] = stat_value
                    elif stat_name == "すばやさ":
                        pokemon_data["base_spe"] = stat_value

        # カテゴリー情報から伝説・幻フラグを判定
        for row in stats_rows:
            cells = row.find_all(["th", "td"])
            if len(cells) >= 2:
                if cells[0].get_text(strip=True) == "カテゴリー":
                    category = cells[1].get_text(strip=True)
                    if "伝説" in category:
                        pokemon_data["is_legendary"] = True
                    if "幻" in category:
                        pokemon_data["is_mythical"] = True

    # フォームラベルの抽出
    # 種族値テーブルのタイトルから抽出 "◆ ボルトロス(化身)の種族値"
    if len(tables) > 1:
        stats_table = tables[1]
        first_row = stats_table.find("tr")
        if first_row:
            title_cell = first_row.find(["th", "td"])
            if title_cell:
                title_text = title_cell.get_text(strip=True)
                # "◆ ボルトロス(化身)の種族値" から "(化身)" を抽出
                form_match = re.search(r"(\([^)]+\))", title_text)
                if form_match:
                    pokemon_data["form_label"] = form_match.group(1)

    return pokemon_data

"""スクレイピングのメイン実行モジュール."""

from __future__ import annotations

import argparse
from typing import Any

from app.scraper.http_client import fetch_pokemon_soup
from app.scraper.output import save_pokemon_json
from app.scraper.pokemon_abilities import scrape_pokemon_abilities
from app.scraper.pokemon_basic import scrape_pokemon_basic
from app.scraper.pokemon_moves import scrape_pokemon_moves


def scrape_and_save(url: str, output_dir: str = "data/pokemon") -> None:
    """指定されたURLからポケモンデータを取得してJSONに保存する.

    Args:
        url: ポケモン図鑑ページのURL
        output_dir: 出力ディレクトリ

    """
    print(f"スクレイピング開始: {url}")

    soup = fetch_pokemon_soup(url)

    # ポケモン基本情報を取得
    pokemon_data = scrape_pokemon_basic(soup)
    abilities = scrape_pokemon_abilities(soup)
    moves = scrape_pokemon_moves(soup)

    bundle: dict[str, Any] = {
        "pokemon": pokemon_data,
        "abilities": abilities,
        "moves": moves,
    }

    print("\n取得したデータ概要:")
    print("-" * 80)
    print(f"ポケモン名: {pokemon_data.get('name_ja')} (No.{pokemon_data.get('pokedex_no')})")
    print(f"特性件数: {len(abilities)}")
    print(f"技件数: {len(moves)}")
    print("-" * 80)

    # JSONファイルに保存
    output_path = save_pokemon_json(bundle, output_dir)

    print(f"\nJSONファイルを保存しました: {output_path}")


if __name__ == "__main__":
    default_url = "https://yakkun.com/sv/zukan/n642"

    parser = argparse.ArgumentParser(
        description="ポケモン図鑑ページからデータを取得してJSONに保存するスクレイパー.",
    )
    parser.add_argument(
        "target_url",
        nargs="?",
        default=default_url,
        help="スクレイピング対象のポケモン図鑑ページURL (省略時はボルトロス).",
    )

    parsed = parser.parse_args()

    scrape_and_save(parsed.target_url)

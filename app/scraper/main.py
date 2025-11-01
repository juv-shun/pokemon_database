"""スクレイピングのメイン実行モジュール."""

from app.scraper.output import save_pokemon_json
from app.scraper.pokemon_basic import scrape_pokemon_basic


def scrape_and_save(url: str, output_dir: str = "data/pokemon") -> None:
    """指定されたURLからポケモンデータを取得してJSONに保存する.

    Args:
        url: ポケモン図鑑ページのURL
        output_dir: 出力ディレクトリ

    """
    print(f"スクレイピング開始: {url}")

    # ポケモン基本情報を取得
    pokemon_data = scrape_pokemon_basic(url)

    print("\n取得したデータ:")
    print("-" * 80)
    for key, value in pokemon_data.items():
        print(f"{key}: {value}")
    print("-" * 80)

    # JSONファイルに保存
    output_path = save_pokemon_json(pokemon_data, output_dir)

    print(f"\nJSONファイルを保存しました: {output_path}")


if __name__ == "__main__":
    # ボルトロス(化身)のサンプル実行
    target_url = "https://yakkun.com/sv/zukan/n642"
    scrape_and_save(target_url)

"""スクレイピングのメイン実行モジュール."""

from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.scraper.http_client import NonSvPageError, fetch_pokemon_soup
from app.scraper.output import save_pokemon_json
from app.scraper.pokemon_abilities import scrape_pokemon_abilities
from app.scraper.pokemon_basic import scrape_pokemon_basic
from app.scraper.pokemon_moves import scrape_pokemon_moves
from app.scraper.progress import BatchProgress, load_progress, save_progress

DEFAULT_SLEEP_SECONDS = 1.0
POKEMON_URLS_PATH = Path("app/scraper/pokemon_urls.json")


@dataclass(slots=True)
class PokemonTarget:
    """スクレイピング対象ポケモンの情報を保持するデータクラス."""

    dex_no: int
    pokemon_name: str
    url: str


def scrape_and_save(url: str, output_dir: str = "data/pokemon") -> None:
    """指定されたURLからポケモンデータを取得してJSONに保存する.

    Args:
        url: ポケモン図鑑ページのURL
        output_dir: 出力ディレクトリ
    """
    print(f"スクレイピング開始: {url}")

    try:
        soup = fetch_pokemon_soup(url)
    except NonSvPageError as error:
        print("ポケモンSV図鑑以外のページへ遷移したため、スクレイピングを中止しました。")
        print(f"最終URL: {error.final_url}")
        return

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

    output_path = save_pokemon_json(bundle, output_dir)

    print(f"\nJSONファイルを保存しました: {output_path}")


def load_pokemon_targets(path: Path) -> list[PokemonTarget]:
    """ポケモンURLリストを読み込む.

    Args:
        path: JSONファイルのパス

    Returns:
        PokemonTargetのリスト
    """
    with path.open(encoding="utf-8") as fp:
        raw_items = json.load(fp)

    targets = [
        PokemonTarget(
            dex_no=int(item["dex_no"]),
            pokemon_name=str(item["pokemon_name"]),
            url=str(item["url"]),
        )
        for item in raw_items
    ]
    return targets


def run_batch(
    *,
    pokemon_targets: list[PokemonTarget],
    sleep_seconds: float = DEFAULT_SLEEP_SECONDS,
) -> None:
    """ポケモン一覧を順次スクレイピングし進捗を保存する.

    Args:
        pokemon_targets: スクレイピング対象リスト
        sleep_seconds: ポケモン処理間で待機する秒数
    """
    total = len(pokemon_targets)
    if total == 0:
        print("ポケモンURLリストが空です。")
        return

    progress: BatchProgress = load_progress(total)
    if progress.next_index >= total:
        print("全てのポケモンについてスクレイピング済みです。")
        return

    stop_requested = False

    def handle_sigint(signum: int, frame: object) -> None:
        nonlocal stop_requested
        if not stop_requested:
            print(
                "\n停止要求を受け付けました。現在のポケモン処理完了後に停止します。",
                flush=True,
            )
        stop_requested = True

    original_handler = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, handle_sigint)

    try:
        for index in range(progress.next_index, total):
            target = pokemon_targets[index]
            current_count = index + 1
            remaining = total - current_count
            print(
                f"\n[{current_count}/{total}] No.{target.dex_no} {target.pokemon_name} を処理中...",
            )
            try:
                scrape_and_save(target.url)
            except Exception as error:  # noqa: BLE001
                print(
                    f"エラーが発生しました (No.{target.dex_no} {target.pokemon_name}): {error}",
                    file=sys.stderr,
                )
                print(
                    "このポケモンの処理は完了しませんでした。次回実行時に再試行します。",
                    file=sys.stderr,
                )
                break

            progress.next_index = index + 1
            save_progress(
                progress,
                total=total,
                last_entry={
                    "dex_no": target.dex_no,
                    "pokemon_name": target.pokemon_name,
                    "url": target.url,
                },
            )

            if stop_requested:
                print("停止要求によりバッチ処理を終了します。")
                break

            if remaining > 0:
                try:
                    time.sleep(sleep_seconds)
                except InterruptedError:
                    stop_requested = True
                    print(
                        "\n停止要求を受け付けました。現在のポケモン処理完了後に停止します。",
                        flush=True,
                    )
    finally:
        signal.signal(signal.SIGINT, original_handler)

    completed = progress.completed_count
    print(f"\n進捗: {completed}/{total} 件完了。")
    if completed >= total:
        print("全てのポケモンのスクレイピングが完了しました。")
    elif stop_requested:
        print("途中停止しました。次回は進捗ファイルを利用して自動的に再開します。")


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
    parser.add_argument(
        "--batch",
        action="store_true",
        help="pokemon_urls.json の一覧を順次スクレイピングします。",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=DEFAULT_SLEEP_SECONDS,
        help="バッチ実行時のポケモン間待機秒数 (デフォルト: 1.0 秒)。",
    )

    parsed = parser.parse_args()

    if parsed.batch:
        targets = load_pokemon_targets(POKEMON_URLS_PATH)
        run_batch(pokemon_targets=targets, sleep_seconds=max(parsed.sleep, 0.0))
    else:
        scrape_and_save(parsed.target_url)

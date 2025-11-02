"""SQL生成ツールのメインエントリポイント.

data/pokemon配下のJSONファイルを読み込み、INSERT SQLを生成します。

Usage:
    python -m app.sql_generator.main
    または
    uv run python -m app.sql_generator.main
"""

import logging
from pathlib import Path

from .json_loader import PokemonDataLoader
from .sql_builder import SQLBuilder

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main() -> None:
    """メイン処理."""
    logger.info("=" * 60)
    logger.info("ポケモンデータベース INSERT SQL生成ツール")
    logger.info("=" * 60)

    # パス設定
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / "data" / "pokemon"
    output_file = project_root / "output" / "insert_data.sql"

    logger.info(f"JSONデータディレクトリ: {data_dir}")
    logger.info(f"SQL出力先: {output_file}")

    # 1. JSONファイル読み込み
    logger.info("\n[1/3] JSONファイル読み込み")
    loader = PokemonDataLoader(data_dir)
    pokemon_data_list = loader.load_all_json_files()

    # 2. データ収集と重複排除
    logger.info("\n[2/3] データ収集と重複排除")
    builder = SQLBuilder()
    builder.collect_data(pokemon_data_list)

    # 3. SQL生成と出力
    logger.info("\n[3/3] SQL生成と出力")
    sql = builder.generate_sql()

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as f:
        f.write(sql)

    logger.info(f"SQLファイルを生成しました: {output_file}")
    logger.info(f"ファイルサイズ: {output_file.stat().st_size:,} bytes")
    logger.info("\n" + "=" * 60)
    logger.info("処理完了")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

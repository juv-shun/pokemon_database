"""CSV生成ツールのメインエントリポイント.

data/pokemon配下のJSONファイルを読み込み、CSVファイルを生成します。

Usage:
    python -m app.csv_generator.main
    または
    uv run python -m app.csv_generator.main
"""

import logging
from pathlib import Path

from .csv_builder import CSVBuilder
from .json_loader import PokemonDataLoader

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main() -> None:
    """メイン処理."""
    logger.info("=" * 60)
    logger.info("ポケモンデータベース CSV生成ツール")
    logger.info("=" * 60)

    # パス設定
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / "data" / "pokemon"
    output_dir = project_root / "output"

    logger.info(f"JSONデータディレクトリ: {data_dir}")
    logger.info(f"CSV出力先ディレクトリ: {output_dir}")

    # 1. JSONファイル読み込み
    logger.info("\n[1/3] JSONファイル読み込み")
    loader = PokemonDataLoader(data_dir)
    pokemon_data_list = loader.load_all_json_files()

    # 2. データ収集と重複排除
    logger.info("\n[2/3] データ収集と重複排除")
    builder = CSVBuilder()
    builder.collect_data(pokemon_data_list)

    # 3. CSV生成と出力
    logger.info("\n[3/3] CSV生成と出力")
    generated_files = builder.generate_csvs(output_dir)

    logger.info("\n生成されたCSVファイル:")
    total_size = 0
    for table_name, file_path in generated_files.items():
        file_size = file_path.stat().st_size
        total_size += file_size
        logger.info(f"  - {table_name}: {file_path.name} ({file_size:,} bytes)")

    logger.info(f"\n合計ファイルサイズ: {total_size:,} bytes")
    logger.info("\n" + "=" * 60)
    logger.info("処理完了")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

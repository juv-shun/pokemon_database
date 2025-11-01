"""JSON出力機能モジュール."""

import json
from pathlib import Path
from typing import Any


def save_pokemon_json(pokemon_data: dict[str, Any], output_dir: str = "data/pokemon") -> Path:
    """ポケモンデータをJSONファイルに保存する.

    Args:
        pokemon_data: ポケモンデータの辞書
        output_dir: 出力ディレクトリ

    Returns:
        保存したファイルのパス

    Raises:
        ValueError: 必要なフィールドが欠けている場合
    """
    # 必須フィールドのチェック
    if pokemon_data.get("pokedex_no") is None:
        raise ValueError("pokedex_no が必須です")
    if pokemon_data.get("name_ja") is None:
        raise ValueError("name_ja が必須です")

    # 出力ディレクトリの作成
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # ファイル名の生成: {pokedex_no:04d}_{name_ja}.json
    pokedex_no = pokemon_data["pokedex_no"]
    name_ja = pokemon_data["name_ja"]
    filename = f"{pokedex_no:04d}_{name_ja}.json"
    file_path = output_path / filename

    # フェーズ1.1.1用の簡略化されたJSONフォーマット（pokemonキーのみ）
    output_data = {"pokemon": pokemon_data}

    # JSONファイルに書き込み
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    return file_path

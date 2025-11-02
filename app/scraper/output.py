"""JSON出力機能モジュール."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def save_pokemon_json(pokemon_bundle: dict[str, Any], output_dir: str = "data/pokemon") -> Path:
    """ポケモンデータをJSONファイルに保存する.

    Args:
        pokemon_bundle: JSON化するポケモン情報の辞書。`pokemon` キー必須。
        output_dir: 出力ディレクトリ

    Returns:
        保存したファイルのパス

    Raises:
        ValueError: 必須フィールドが欠けている場合
    """
    pokemon = pokemon_bundle.get("pokemon")
    if not isinstance(pokemon, dict):
        raise ValueError("pokemon キーにポケモン基本情報の辞書が必要です")

    pokedex_no = pokemon.get("pokedex_no")
    name_ja = pokemon.get("name_ja")

    if pokedex_no is None:
        raise ValueError("pokemon.pokedex_no が必須です")
    if name_ja is None:
        raise ValueError("pokemon.name_ja が必須です")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    filename = f"{int(pokedex_no):04d}_{name_ja}.json"
    file_path = output_path / filename

    with open(file_path, "w", encoding="utf-8") as fp:
        json.dump(pokemon_bundle, fp, ensure_ascii=False, indent=2)

    return file_path

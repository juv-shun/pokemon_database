"""JSONファイル読み込みモジュール.

data/pokemon配下のJSONファイルを読み込み、Pydanticモデルに変換します。
"""

import json
import logging
from pathlib import Path

from .models import Ability, Move, PokemonAbility, PokemonData, PokemonMove

logger = logging.getLogger(__name__)


class PokemonDataLoader:
    """ポケモンデータローダー."""

    def __init__(self, data_dir: Path) -> None:
        """初期化.

        Args:
            data_dir: JSONファイルが格納されているディレクトリパス
        """
        self.data_dir = data_dir

    def load_all_json_files(self) -> list[PokemonData]:
        """data/pokemon配下の全JSONファイルを読み込む.

        Returns:
            PokemonDataオブジェクトのリスト

        Raises:
            FileNotFoundError: data_dirが存在しない場合
        """
        if not self.data_dir.exists():
            msg = f"ディレクトリが存在しません: {self.data_dir}"
            raise FileNotFoundError(msg)

        json_files = sorted(self.data_dir.glob("*.json"))
        logger.info(f"{len(json_files)}個のJSONファイルを検出しました")

        pokemon_data_list: list[PokemonData] = []

        for json_file in json_files:
            try:
                pokemon_data = self._load_single_json(json_file)
                pokemon_data_list.append(pokemon_data)
            except Exception:
                logger.exception(f"JSONファイルの読み込みに失敗: {json_file}")
                raise

        logger.info(f"{len(pokemon_data_list)}件のポケモンデータを読み込みました")
        return pokemon_data_list

    def _load_single_json(self, json_path: Path) -> PokemonData:
        """単一のJSONファイルを読み込む.

        Args:
            json_path: JSONファイルのパス

        Returns:
            PokemonDataオブジェクト
        """
        logger.debug(f"読み込み中: {json_path.name}")

        with json_path.open(encoding="utf-8") as f:
            raw_data = json.load(f)

        # JSONの特性・技データにis_hidden/notesを追加
        abilities_with_pokemon = []
        for ability_data in raw_data.get("abilities", []):
            abilities_with_pokemon.append(
                {
                    "pokemon_name": raw_data["pokemon"]["name_ja"],
                    "ability_name": ability_data["name_ja"],
                    "is_hidden": ability_data.get("is_hidden", False),
                }
            )

        moves_with_pokemon = []
        for move_data in raw_data.get("moves", []):
            moves_with_pokemon.append(
                {
                    "pokemon_name": raw_data["pokemon"]["name_ja"],
                    "move_name": move_data["name_ja"],
                    "notes": move_data.get("notes"),
                }
            )

        # Pydanticモデルに変換
        pokemon_data = PokemonData(
            pokemon=raw_data["pokemon"],
            abilities=[
                Ability(
                    name_ja=ability["name_ja"],
                    effect_text=ability.get("effect_text"),
                )
                for ability in raw_data.get("abilities", [])
            ],
            moves=[
                Move(
                    name_ja=move["name_ja"],
                    type_name=move["type_name"],
                    damage_class=move["damage_class"],
                    power=move.get("power"),
                    accuracy=move.get("accuracy"),
                    pp=move.get("pp"),
                    priority=move.get("priority", 0),
                    effect_text=move.get("effect_text"),
                )
                for move in raw_data.get("moves", [])
            ],
        )

        # ポケモン-特性、ポケモン-技の関連情報を保持
        pokemon_data.pokemon_abilities = [PokemonAbility(**data) for data in abilities_with_pokemon]
        pokemon_data.pokemon_moves = [PokemonMove(**data) for data in moves_with_pokemon]

        return pokemon_data

"""CSV生成モジュール.

PokemonDataからCSVファイルを生成します。
"""

import csv
import logging
from collections.abc import Sequence
from pathlib import Path

from .models import Ability, Move, Pokemon, PokemonAbility, PokemonData

logger = logging.getLogger(__name__)


class CSVBuilder:
    """CSV生成クラス."""

    def __init__(self) -> None:
        """初期化."""
        self.abilities_dict: dict[str, Ability] = {}
        self.moves_dict: dict[str, Move] = {}
        self.pokemon_list: list[Pokemon] = []
        self.pokemon_abilities: list[PokemonAbility] = []
        self.pokemon_moves_dict: dict[tuple[str, str], None] = {}  # (pokemon_name, move_name)

        # 名前→IDマッピング（CSV生成時に使用）
        self.ability_name_to_id: dict[str, int] = {}
        self.move_name_to_id: dict[str, int] = {}
        self.pokemon_name_to_id: dict[str, int] = {}

    def collect_data(self, pokemon_data_list: Sequence[PokemonData]) -> None:
        """全ポケモンデータから特性・技を収集し、重複排除する.

        Args:
            pokemon_data_list: PokemonDataオブジェクトのリスト
        """
        logger.info("データ収集フェーズ開始")

        for pokemon_data in pokemon_data_list:
            # ポケモン基本情報
            self.pokemon_list.append(pokemon_data.pokemon)

            # 特性（name_jaでユニーク）
            for ability in pokemon_data.abilities:
                if ability.name_ja not in self.abilities_dict:
                    self.abilities_dict[ability.name_ja] = ability

            # 技（name_jaでユニーク）
            for move in pokemon_data.moves:
                if move.name_ja not in self.moves_dict:
                    self.moves_dict[move.name_ja] = move

            # ポケモン-特性関連
            self.pokemon_abilities.extend(pokemon_data.pokemon_abilities)

            # ポケモン-技関連（pokemon_name, move_nameの組み合わせでユニーク化）
            for pm in pokemon_data.pokemon_moves:
                key = (pm.pokemon_name, pm.move_name)
                self.pokemon_moves_dict[key] = None

        logger.info(f"ポケモン: {len(self.pokemon_list)}件")
        logger.info(f"ユニーク特性: {len(self.abilities_dict)}件")
        logger.info(f"ユニーク技: {len(self.moves_dict)}件")
        logger.info(f"ポケモン-特性関連: {len(self.pokemon_abilities)}件")
        logger.info(f"ポケモン-技関連（ユニーク）: {len(self.pokemon_moves_dict)}件")

    def generate_csvs(self, output_dir: Path) -> dict[str, Path]:
        """CSVファイルを生成する.

        Args:
            output_dir: 出力先ディレクトリ

        Returns:
            生成されたCSVファイルのパス辞書 (テーブル名 -> パス)
        """
        logger.info("CSV生成フェーズ開始")

        output_dir.mkdir(parents=True, exist_ok=True)
        generated_files = {}

        # IDマッピングを構築
        self._build_id_mappings()

        # 各テーブルのCSV生成（マスタテーブルが先）
        generated_files["abilities"] = self._generate_abilities_csv(output_dir / "abilities.csv")
        generated_files["moves"] = self._generate_moves_csv(output_dir / "moves.csv")
        generated_files["pokemon"] = self._generate_pokemon_csv(output_dir / "pokemon.csv")
        generated_files["pokemon_abilities"] = self._generate_pokemon_abilities_csv(
            output_dir / "pokemon_abilities.csv"
        )
        generated_files["pokemon_moves"] = self._generate_pokemon_moves_csv(
            output_dir / "pokemon_moves.csv"
        )

        logger.info(f"CSV生成完了: {len(generated_files)}ファイル")
        return generated_files

    def _build_id_mappings(self) -> None:
        """名前→IDマッピングを構築する."""
        # 特性のIDマッピング（アルファベット順でソートして連番を割り当て）
        for idx, name_ja in enumerate(sorted(self.abilities_dict.keys()), start=1):
            self.ability_name_to_id[name_ja] = idx

        # 技のIDマッピング
        for idx, name_ja in enumerate(sorted(self.moves_dict.keys()), start=1):
            self.move_name_to_id[name_ja] = idx

        # ポケモンのIDマッピング
        for idx, pokemon in enumerate(self.pokemon_list, start=1):
            self.pokemon_name_to_id[pokemon.name_ja] = idx

    def _generate_abilities_csv(self, output_path: Path) -> Path:
        """特性マスタのCSVを生成.

        Args:
            output_path: 出力ファイルパス

        Returns:
            生成されたファイルパス
        """
        logger.info(f"特性CSV生成中: {output_path}")

        with output_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)

            # ヘッダー
            writer.writerow(["id", "name_ja", "effect_text"])

            # データ（ソート順でID割り当て）
            for name_ja in sorted(self.abilities_dict.keys()):
                ability = self.abilities_dict[name_ja]
                ability_id = self.ability_name_to_id[name_ja]
                writer.writerow([ability_id, ability.name_ja, ability.effect_text or ""])

        logger.info(f"特性CSV生成完了: {len(self.abilities_dict)}件")
        return output_path

    def _generate_moves_csv(self, output_path: Path) -> Path:
        """技マスタのCSVを生成.

        Args:
            output_path: 出力ファイルパス

        Returns:
            生成されたファイルパス
        """
        logger.info(f"技CSV生成中: {output_path}")

        with output_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)

            # ヘッダー
            writer.writerow(
                [
                    "id",
                    "name_ja",
                    "type_name",
                    "damage_class",
                    "power",
                    "accuracy",
                    "pp",
                    "priority",
                    "effect_text",
                ]
            )

            # データ（ソート順でID割り当て）
            for name_ja in sorted(self.moves_dict.keys()):
                move = self.moves_dict[name_ja]
                move_id = self.move_name_to_id[name_ja]
                writer.writerow(
                    [
                        move_id,
                        move.name_ja,
                        move.type_name,
                        move.damage_class or "",
                        move.power if move.power is not None else "",
                        move.accuracy if move.accuracy is not None else "",
                        move.pp if move.pp is not None else "",
                        move.priority,
                        move.effect_text or "",
                    ]
                )

        logger.info(f"技CSV生成完了: {len(self.moves_dict)}件")
        return output_path

    def _generate_pokemon_csv(self, output_path: Path) -> Path:
        """ポケモンマスタのCSVを生成.

        Args:
            output_path: 出力ファイルパス

        Returns:
            生成されたファイルパス
        """
        logger.info(f"ポケモンCSV生成中: {output_path}")

        with output_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)

            # ヘッダー
            writer.writerow(
                [
                    "id",
                    "pokedex_no",
                    "name_ja",
                    "name_en",
                    "form_label",
                    "type_primary",
                    "type_secondary",
                    "height_dm",
                    "weight_hg",
                    "low_kick_power",
                    "is_legendary",
                    "is_mythical",
                    "base_hp",
                    "base_atk",
                    "base_def",
                    "base_spa",
                    "base_spd",
                    "base_spe",
                    "remarks",
                ]
            )

            # データ
            for pokemon in self.pokemon_list:
                pokemon_id = self.pokemon_name_to_id[pokemon.name_ja]
                writer.writerow(
                    [
                        pokemon_id,
                        pokemon.pokedex_no,
                        pokemon.name_ja,
                        pokemon.name_en or "",
                        pokemon.form_label or "",
                        pokemon.type_primary,
                        pokemon.type_secondary or "",
                        pokemon.height_dm if pokemon.height_dm is not None else "",
                        pokemon.weight_hg if pokemon.weight_hg is not None else "",
                        pokemon.low_kick_power if pokemon.low_kick_power is not None else "",
                        pokemon.is_legendary,
                        pokemon.is_mythical,
                        pokemon.base_hp,
                        pokemon.base_atk,
                        pokemon.base_def,
                        pokemon.base_spa,
                        pokemon.base_spd,
                        pokemon.base_spe,
                        pokemon.remarks or "",
                    ]
                )

        logger.info(f"ポケモンCSV生成完了: {len(self.pokemon_list)}件")
        return output_path

    def _generate_pokemon_abilities_csv(self, output_path: Path) -> Path:
        """ポケモン-特性関連のCSVを生成.

        Args:
            output_path: 出力ファイルパス

        Returns:
            生成されたファイルパス
        """
        logger.info(f"ポケモン-特性CSV生成中: {output_path}")

        with output_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)

            # ヘッダー
            writer.writerow(["pokemon_id", "ability_id", "is_hidden"])

            # データ（名前をIDに変換）
            for pa in self.pokemon_abilities:
                pokemon_id = self.pokemon_name_to_id[pa.pokemon_name]
                ability_id = self.ability_name_to_id[pa.ability_name]
                writer.writerow([pokemon_id, ability_id, pa.is_hidden])

        logger.info(f"ポケモン-特性CSV生成完了: {len(self.pokemon_abilities)}件")
        return output_path

    def _generate_pokemon_moves_csv(self, output_path: Path) -> Path:
        """ポケモン-技関連のCSVを生成.

        Args:
            output_path: 出力ファイルパス

        Returns:
            生成されたファイルパス
        """
        logger.info(f"ポケモン-技CSV生成中: {output_path}")

        with output_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)

            # ヘッダー
            writer.writerow(["pokemon_id", "move_id"])

            # データ（名前をIDに変換）
            for pokemon_name, move_name in self.pokemon_moves_dict.keys():
                pokemon_id = self.pokemon_name_to_id[pokemon_name]
                move_id = self.move_name_to_id[move_name]
                writer.writerow([pokemon_id, move_id])

        logger.info(f"ポケモン-技CSV生成完了: {len(self.pokemon_moves_dict)}件")
        return output_path

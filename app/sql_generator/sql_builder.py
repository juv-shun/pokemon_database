"""SQL生成モジュール.

PokemonDataからINSERT SQLを生成します。
"""

import logging
from collections.abc import Sequence

from .models import Ability, Move, Pokemon, PokemonAbility, PokemonData, PokemonMove

logger = logging.getLogger(__name__)


class SQLBuilder:
    """SQL生成クラス."""

    def __init__(self) -> None:
        """初期化."""
        self.abilities_dict: dict[str, Ability] = {}
        self.moves_dict: dict[str, Move] = {}
        self.pokemon_list: list[Pokemon] = []
        self.pokemon_abilities: list[PokemonAbility] = []
        self.pokemon_moves_dict: dict[tuple[str, str], list[str]] = {}  # (pokemon_name, move_name) -> [notes]

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
                self.pokemon_moves_dict[key] = None  # notesは保存しない

        logger.info(f"ポケモン: {len(self.pokemon_list)}件")
        logger.info(f"ユニーク特性: {len(self.abilities_dict)}件")
        logger.info(f"ユニーク技: {len(self.moves_dict)}件")
        logger.info(f"ポケモン-特性関連: {len(self.pokemon_abilities)}件")
        logger.info(f"ポケモン-技関連（ユニーク）: {len(self.pokemon_moves_dict)}件")

    def generate_sql(self) -> str:
        """INSERT SQLを生成する.

        Returns:
            生成されたSQL文字列
        """
        logger.info("SQL生成フェーズ開始")

        sql_parts = [
            "BEGIN;",
            "",
            "-- ========================================",
            "-- 特性マスタINSERT",
            "-- ========================================",
            self._generate_abilities_sql(),
            "",
            "-- ========================================",
            "-- 技マスタINSERT",
            "-- ========================================",
            self._generate_moves_sql(),
            "",
            "-- ========================================",
            "-- ポケモンマスタINSERT",
            "-- ========================================",
            self._generate_pokemon_sql(),
            "",
            "-- ========================================",
            "-- ポケモン-特性関連INSERT",
            "-- ========================================",
            self._generate_pokemon_abilities_sql(),
            "",
            "-- ========================================",
            "-- ポケモン-技関連INSERT",
            "-- ========================================",
            self._generate_pokemon_moves_sql(),
            "",
            "COMMIT;",
        ]

        return "\n".join(sql_parts)

    def _generate_abilities_sql(self) -> str:
        """特性マスタのINSERT SQLを生成."""
        if not self.abilities_dict:
            return "-- 特性データなし"

        sql = "INSERT INTO sv.abilities (name_ja, effect_text) VALUES\n"
        values = []

        for ability in self.abilities_dict.values():
            name_ja = self._escape_sql_string(ability.name_ja)
            effect_text = (
                self._escape_sql_string(ability.effect_text) if ability.effect_text else "NULL"
            )
            values.append(f"  ({name_ja}, {effect_text})")

        sql += ",\n".join(values)
        sql += "\nON CONFLICT (name_ja) DO NOTHING;"

        return sql

    def _generate_moves_sql(self) -> str:
        """技マスタのINSERT SQLを生成."""
        if not self.moves_dict:
            return "-- 技データなし"

        sql = "INSERT INTO sv.moves (name_ja, type_name, damage_class, power, accuracy, pp, priority, effect_text) VALUES\n"
        values = []

        for move in self.moves_dict.values():
            name_ja = self._escape_sql_string(move.name_ja)
            type_name = self._escape_sql_string(move.type_name)
            damage_class = (
                self._escape_sql_string(move.damage_class) if move.damage_class else "NULL"
            )
            power = str(move.power) if move.power is not None else "NULL"
            accuracy = str(move.accuracy) if move.accuracy is not None else "NULL"
            pp = str(move.pp) if move.pp is not None else "NULL"
            priority = str(move.priority)
            effect_text = self._escape_sql_string(move.effect_text) if move.effect_text else "NULL"

            values.append(
                f"  ({name_ja}, {type_name}, {damage_class}, {power}, {accuracy}, {pp}, {priority}, {effect_text})"
            )

        sql += ",\n".join(values)
        sql += "\nON CONFLICT (name_ja) DO NOTHING;"

        return sql

    def _generate_pokemon_sql(self) -> str:
        """ポケモンマスタのINSERT SQLを生成."""
        if not self.pokemon_list:
            return "-- ポケモンデータなし"

        sql = "INSERT INTO sv.pokemon (pokedex_no, name_ja, name_en, form_label, type_primary, type_secondary, height_dm, weight_hg, low_kick_power, is_legendary, is_mythical, base_hp, base_atk, base_def, base_spa, base_spd, base_spe, remarks) VALUES\n"
        values = []

        for pokemon in self.pokemon_list:
            pokedex_no = str(pokemon.pokedex_no)
            name_ja = self._escape_sql_string(pokemon.name_ja)
            name_en = self._escape_sql_string(pokemon.name_en) if pokemon.name_en else "NULL"
            form_label = (
                self._escape_sql_string(pokemon.form_label) if pokemon.form_label else "NULL"
            )
            type_primary = self._escape_sql_string(pokemon.type_primary)
            type_secondary = (
                self._escape_sql_string(pokemon.type_secondary)
                if pokemon.type_secondary
                else "NULL"
            )
            height_dm = str(pokemon.height_dm) if pokemon.height_dm is not None else "NULL"
            weight_hg = str(pokemon.weight_hg) if pokemon.weight_hg is not None else "NULL"
            low_kick_power = (
                str(pokemon.low_kick_power) if pokemon.low_kick_power is not None else "NULL"
            )
            is_legendary = "true" if pokemon.is_legendary else "false"
            is_mythical = "true" if pokemon.is_mythical else "false"
            base_hp = str(pokemon.base_hp)
            base_atk = str(pokemon.base_atk)
            base_def = str(pokemon.base_def)
            base_spa = str(pokemon.base_spa)
            base_spd = str(pokemon.base_spd)
            base_spe = str(pokemon.base_spe)
            remarks = self._escape_sql_string(pokemon.remarks) if pokemon.remarks else "NULL"

            values.append(
                f"  ({pokedex_no}, {name_ja}, {name_en}, {form_label}, {type_primary}, {type_secondary}, {height_dm}, {weight_hg}, {low_kick_power}, {is_legendary}, {is_mythical}, {base_hp}, {base_atk}, {base_def}, {base_spa}, {base_spd}, {base_spe}, {remarks})"
            )

        sql += ",\n".join(values)
        sql += ";"

        return sql

    def _generate_pokemon_abilities_sql(self) -> str:
        """ポケモン-特性関連のINSERT SQLを生成."""
        if not self.pokemon_abilities:
            return "-- ポケモン-特性関連データなし"

        selects = []

        for pa in self.pokemon_abilities:
            pokemon_name = self._escape_sql_string(pa.pokemon_name)
            ability_name = self._escape_sql_string(pa.ability_name)
            is_hidden = "true" if pa.is_hidden else "false"

            selects.append(
                f"SELECT (SELECT id FROM sv.pokemon WHERE name_ja = {pokemon_name}), "
                f"(SELECT id FROM sv.abilities WHERE name_ja = {ability_name}), "
                f"{is_hidden}"
            )

        # バッチサイズ1000でINSERT文を分割
        return self._batch_insert_statements(
            "sv.pokemon_abilities",
            "(pokemon_id, ability_id, is_hidden)",
            selects,
            batch_size=1000,
        )

    def _generate_pokemon_moves_sql(self) -> str:
        """ポケモン-技関連のINSERT SQLを生成."""
        if not self.pokemon_moves_dict:
            return "-- ポケモン-技関連データなし"

        selects = []

        for (pokemon_name, move_name) in self.pokemon_moves_dict.keys():
            pokemon_name_escaped = self._escape_sql_string(pokemon_name)
            move_name_escaped = self._escape_sql_string(move_name)

            selects.append(
                f"SELECT (SELECT id FROM sv.pokemon WHERE name_ja = {pokemon_name_escaped}), "
                f"(SELECT id FROM sv.moves WHERE name_ja = {move_name_escaped})"
            )

        # バッチサイズ1000でINSERT文を分割
        return self._batch_insert_statements(
            "sv.pokemon_moves",
            "(pokemon_id, move_id)",
            selects,
            batch_size=1000,
        )

    @staticmethod
    def _batch_insert_statements(
        table_name: str,
        columns: str,
        selects: list[str],
        batch_size: int = 1000,
    ) -> str:
        """大量のINSERT文をバッチに分割する.

        Args:
            table_name: テーブル名
            columns: カラム定義 (例: "(col1, col2, col3)")
            selects: SELECT文のリスト
            batch_size: バッチサイズ (デフォルト: 1000)

        Returns:
            バッチ分割されたINSERT SQL
        """
        if not selects:
            return f"-- {table_name}にデータなし"

        sql_parts = []
        for i in range(0, len(selects), batch_size):
            batch = selects[i : i + batch_size]
            batch_sql = f"INSERT INTO {table_name} {columns}\n"
            batch_sql += "\nUNION ALL\n".join(batch)
            batch_sql += ";"
            sql_parts.append(batch_sql)

        return "\n\n".join(sql_parts)

    @staticmethod
    def _escape_sql_string(value: str | None) -> str:
        """SQL文字列をエスケープする.

        Args:
            value: エスケープ対象の文字列

        Returns:
            エスケープされた文字列（シングルクォート含む）
        """
        if value is None:
            return "NULL"

        # シングルクォートを2つにエスケープ
        escaped = value.replace("'", "''")
        return f"'{escaped}'"

"""Data models for Pokemon database.

JSONデータとデータベーススキーマに対応するPydanticモデル定義。
"""

from typing import Optional

from pydantic import BaseModel, Field


class Pokemon(BaseModel):
    """ポケモン基本情報モデル (sv.pokemon テーブル対応)."""

    pokedex_no: int
    name_ja: str
    name_en: Optional[str] = None
    form_label: Optional[str] = None
    type_primary: str
    type_secondary: Optional[str] = None
    height_dm: Optional[int] = None
    weight_hg: Optional[int] = None
    low_kick_power: Optional[int] = None
    is_legendary: bool = False
    is_mythical: bool = False
    base_hp: int
    base_atk: int
    base_def: int
    base_spa: int
    base_spd: int
    base_spe: int
    remarks: Optional[str] = None


class Ability(BaseModel):
    """特性モデル (sv.abilities テーブル対応)."""

    name_ja: str
    effect_text: Optional[str] = None


class PokemonAbility(BaseModel):
    """ポケモン-特性関連モデル (sv.pokemon_abilities テーブル対応)."""

    pokemon_name: str
    ability_name: str
    is_hidden: bool = False


class Move(BaseModel):
    """技モデル (sv.moves テーブル対応)."""

    name_ja: str
    type_name: str
    damage_class: Optional[str] = None  # キョダイマックス技などでnullの場合あり
    power: Optional[int] = None
    accuracy: Optional[int] = None
    pp: Optional[int] = None
    priority: int = 0
    effect_text: Optional[str] = None


class PokemonMove(BaseModel):
    """ポケモン-技関連モデル (sv.pokemon_moves テーブル対応)."""

    pokemon_name: str
    move_name: str
    notes: Optional[str] = None


class PokemonData(BaseModel):
    """JSONファイル全体の構造を表すモデル."""

    pokemon: Pokemon
    abilities: list[Ability] = Field(default_factory=list)
    moves: list[Move] = Field(default_factory=list)
    pokemon_abilities: list[PokemonAbility] = Field(default_factory=list)
    pokemon_moves: list[PokemonMove] = Field(default_factory=list)

# CSV Generator 設計書

## 概要

`app.csv_generator` は、ポケモン Zukan（ポケ徹）からスクレイピングした JSON データを、Supabase 投入用の CSV ファイルに変換するツールです。

## 目的

- スクレイピングで収集したポケモンデータをデータベース投入可能な形式に変換
- 特性・技などのマスタデータの重複を排除
- 正規化されたリレーショナルデータベース構造に準拠した CSV 生成

## アーキテクチャ

### ディレクトリ構成

```
app/csv_generator/
├── __init__.py          # パッケージ初期化
├── main.py              # エントリーポイント
├── csv_builder.py       # CSV生成ロジック
├── models.py            # データモデル定義
└── json_loader.py       # JSONファイル読み込み
```

### データフロー

```
data/pokemon/*.json
    ↓ (JSONファイル読み込み)
json_loader.py
    ↓ (PokemonDataオブジェクト生成)
models.py
    ↓ (データ収集・重複排除)
csv_builder.py
    ↓ (CSV生成)
data/csv_files/*.csv
    ↓ (データ投入)
Supabase (svスキーマ)
```

## 主要コンポーネント

### 1. main.py

アプリケーションのエントリーポイント。コマンドライン引数を解析し、JSON 読み込みと CSV 生成を実行します。

```bash
# デフォルト設定で実行
uv run python -m app.csv_generator.main

# カスタムディレクトリを指定
uv run python -m app.csv_generator.main --input-dir ./custom_data --output-dir ./custom_output
```

### 2. json_loader.py

指定ディレクトリ内の全 JSON ファイルを読み込み、`PokemonData` オブジェクトに変換します。

### 3. models.py

データ構造の定義

**主要なデータモデル**:

```python
@dataclass
class Pokemon:
    """ポケモンマスタデータ"""
    pokedex_no: int          # 図鑑番号
    name_ja: str             # 日本語名
    name_en: str | None      # 英語名
    form_label: str | None   # フォームラベル（リージョンフォーム等）
    type_primary: str        # タイプ1
    type_secondary: str | None  # タイプ2
    height_dm: int | None    # 高さ（デシメートル）
    weight_hg: int | None    # 重さ（ヘクトグラム）
    low_kick_power: int | None  # けたぐり威力
    is_legendary: bool       # 伝説フラグ
    is_mythical: bool        # 幻フラグ
    base_hp: int            # 種族値HP
    base_atk: int           # 種族値攻撃
    base_def: int           # 種族値防御
    base_spa: int           # 種族値特攻
    base_spd: int           # 種族値特防
    base_spe: int           # 種族値素早さ
    remarks: str | None     # 備考

@dataclass
class Ability:
    """特性マスタデータ"""
    name_ja: str            # 日本語名
    effect_text: str | None # 効果テキスト

@dataclass
class Move:
    """技マスタデータ"""
    name_ja: str            # 日本語名
    type_name: str          # タイプ
    damage_class: str | None  # 分類（物理/特殊/変化）
    power: int | None       # 威力
    accuracy: int | None    # 命中率
    pp: int | None          # PP
    priority: int           # 優先度
    effect_text: str | None # 効果テキスト

@dataclass
class PokemonAbility:
    """ポケモン-特性関連データ"""
    pokemon_name: str       # ポケモン名
    ability_name: str       # 特性名
    is_hidden: bool         # 隠れ特性フラグ

@dataclass
class PokemonData:
    """JSONから読み込んだポケモンデータ全体"""
    pokemon: Pokemon
    abilities: list[Ability]
    moves: list[Move]
```

### 4. csv_builder.py

CSV 生成のコアロジック。以下の 3 フェーズで処理を実行します:

1. **データ収集**: 全ポケモンから特性・技を収集し、名前ベースで重複排除
2. **ID 割り当て**: 特性・技はアルファベット順、ポケモンは読み込み順で ID 採番
3. **CSV 生成**: マスタテーブル（abilities, moves, pokemon）と関連テーブル（pokemon_abilities, pokemon_moves）の CSV を生成

**生成される CSV ファイル**:

| ファイル名              | 内容              |
| ----------------------- | ----------------- |
| `abilities.csv`         | 特性マスタ        |
| `moves.csv`             | 技マスタ          |
| `pokemon.csv`           | ポケモンマスタ    |
| `pokemon_abilities.csv` | ポケモン-特性関連 |
| `pokemon_moves.csv`     | ポケモン-技関連   |

## 設計上の重要ポイント

### 1. ID 採番戦略

- **特性・技**: アルファベット順ソートで安定した ID

  - 理由: 同じデータセットからは常に同じ ID が生成される
  - メリット: CSV の差分管理が容易

- **ポケモン**: 読み込み順で ID 採番
  - 理由: ポケモンは図鑑番号とフォームの組み合わせで一意
  - メリット: シンプルな実装

### 2. 重複排除

- **特性・技**: 日本語名をキーとした辞書で重複排除
- **ポケモン-技の関連**: `(pokemon_name, move_name)` のタプルをキーとした辞書で重複排除

### 3. NULL 値の扱い

- Python 側では `None` で表現
- CSV 出力時は空文字列 `""` に変換
- PostgreSQL の COPY コマンドが空文字列を NULL として扱う

### 4. エンコーディング

- すべての CSV ファイルは **UTF-8** でエンコード
- PostgreSQL の COPY コマンドでも `ENCODING 'UTF8'` を明示

## データ投入

CSV 生成後、`scripts/import_to_supabase.sh` を使用して Supabase にデータを投入します。詳細は [本番環境投入手順](./本番環境投入手順.md) を参照してください。

```bash
# ローカル環境に投入
./scripts/import_to_supabase.sh

# 本番環境に投入
./scripts/import_to_supabase.sh --remote
```

# scraper 設計ドキュメント

## 目的

scraper は、ポケモン図鑑サイト（ポケモン徹底攻略）からデータを取得し、データベース構築用の JSON ファイルを生成することを目的としたスクレイピングツールである。ポケモンの基本情報・特性・習得技を網羅的に収集する。

## 全体構成

```
app/scraper/
├── main.py               # CLI エントリーポイント（単体／バッチ実行）
├── http_client.py        # HTTP 通信と Cloudflare 対策ヘッダー
├── pokemon_basic.py      # 基本情報スクレイパー
├── pokemon_abilities.py  # 特性スクレイパー
├── pokemon_moves.py      # 技スクレイパー
├── output.py             # JSON 保存ロジック
├── progress.py           # バッチ進捗管理
└── pokemon_urls.json     # フェーズ1.3で対象とするポケモンURL一覧
```

## 主な処理フロー

1. `main.py` が CLI 引数を解析し、単体スクレイピング (`target_url`) かバッチ実行 (`--batch`) を判定する。
2. `http_client.fetch_pokemon_soup()` がユーザーエージェントの偽装を行い、HTML を取得する。最終的な URL のパスが `/sv/` で始まらない場合（例: ZA や SM の図鑑ページ）は `NonSvPageError` を送出して処理を中断し、データ整合性を保つ。
3. `pokemon_basic.py`, `pokemon_abilities.py`, `pokemon_moves.py` が BeautifulSoup を用いて各情報を抽出する。
4. `output.save_pokemon_json()` が `data/pokemon/` 配下に `{図鑑番号}_{名称}.json` の形式で保存する（多言語出力は UTF-8／非 ASCII のまま保持）。

## バッチ実行の設計

- `pokemon_urls.json` に定義されたポケモンを直列で処理する。
- 各ポケモン処理の間に既定で 1 秒 (`DEFAULT_SLEEP_SECONDS`) のスリープを挟む。`--sleep` オプションで調整可能。
- SIGINT（Ctrl+C）を受け取ると、「現在処理中のポケモンまで完了 → 停止」の挙動となる。
- 進捗は `data/progress/pokemon_scrape_progress.json` に保存され、次回の `--batch` 実行時に未処理のインデックスから再開する。
  - 保存内容: `next_index`（次に処理するインデックス）、`completed_count`、`last_processed`（直近のポケモン情報）、`last_updated_utc` 等。
  - 進捗ファイルは `.gitignore` に含め、リポジトリ外部へのコミットを防いでいる。

## エラー制御と再実行

- HTTP エラーは `requests.HTTPError` をそのまま送出し、ログに表示した上で処理を終了する。
- スクレイプ中の例外（構造変化など）が発生した場合はバッチ処理を中断し、進捗ファイルは直前までを保持。問題を修正後に同じバッチコマンドを再実行することで再試行できる。
- SV 以外のページへリダイレクトされた場合は `NonSvPageError` で処理をスキップし、バッチの次のポケモンへ進む（進捗はインクリメントされる）。ZA 専用ページや未登場ポケモンのデータ混入を防ぐ目的でこの設計としている。

## 実行例

### 単体スクレイピング

```bash
uv run python -m app.scraper.main https://yakkun.com/sv/zukan/n25
```

### バッチスクレイピング

```bash
uv run python -m app.scraper.main --batch
```

オプション例:

- `--sleep 0.5` : ポケモン間のスリープを 0.5 秒に短縮
- `--sleep 2.0` : 2 秒の待機を挟む

## JSON ファイルフォーマット

以下の構造で JSON ファイルを生成する。

```json
{
  "pokemon": {
    "pokedex_no": 1,
    "name_ja": "フシギダネ",
    "name_en": "Bulbasaur",
    "form_label": null,
    "type_primary": "くさ",
    "type_secondary": "どく",
    "height_dm": 7,
    "weight_hg": 69,
    "low_kick_power": 40,
    "is_legendary": false,
    "is_mythical": false,
    "base_hp": 45,
    "base_atk": 49,
    "base_def": 49,
    "base_spa": 65,
    "base_spd": 65,
    "base_spe": 45,
    "remarks": null
  },
  "abilities": [
    {
      "name_ja": "しんりょく",
      "effect_text": "HPが1/3以下のとき、くさタイプの技の威力が1.5倍になる",
      "is_hidden": false
    },
    {
      "name_ja": "ようりょくそ",
      "effect_text": "天気が「ひざしがつよい」のとき、すばやさが2倍になる",
      "is_hidden": true
    }
  ],
  "moves": [
    {
      "name_ja": "たいあたり",
      "type_name": "ノーマル",
      "damage_class": "physical",
      "power": 40,
      "accuracy": 100,
      "pp": 35,
      "priority": 0,
      "effect_text": "通常攻撃",
      "notes": "レベル1"
    },
    {
      "name_ja": "やどりぎのタネ",
      "type_name": "くさ",
      "damage_class": "status",
      "power": null,
      "accuracy": 90,
      "pp": 10,
      "priority": 0,
      "effect_text": "毎ターン最大HPの1/8のダメージを与え、その分自分のHPを回復する",
      "notes": "レベル7"
    }
  ]
}
```

### フォーマットの特徴

1. **トップレベル構造**

   - `pokemon`: ポケモン本体の情報（1 オブジェクト）
   - `abilities`: 特性のリスト（配列）
   - `moves`: 覚える技のリスト（配列）

2. **`pokemon` オブジェクト**

   - DB 設計書の `sv.pokemon` テーブルのカラムと 1 対 1 で対応
   - `id` は含めない（DB 挿入時に自動採番）
   - NULL 許容フィールドは `null` を明示的に設定

3. **`abilities` 配列**

   - 各特性の情報と、そのポケモンにとって夢特性かどうか（`is_hidden`）を含む
   - `abilities` テーブルと `pokemon_abilities` テーブルの情報を統合
   - `id` や `pokemon_id`, `ability_id` などのリレーションキーは含めない

4. **`moves` 配列**
   - 各技の情報と、習得方法のメモ（`notes`）を含む
   - `moves` テーブルと `pokemon_moves` テーブルの情報を統合
   - `id` や `pokemon_id`, `move_id` などのリレーションキーは含めない

## 出力ファイルの命名規則

```text
data/pokemon/{pokedex_no:04d}_{name_ja}.json
```

例：

- `data/pokemon/0001_フシギダネ.json`
- `data/pokemon/0025_ピカチュウ.json`
- `data/pokemon/0025_ピカチュウ(相棒).json` （フォーム違い）

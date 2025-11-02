# app/scraper 設計ドキュメント

## 目的

app/scraper は、ポケモン図鑑サイト（ポケモン徹底攻略）からデータを取得し、データベース構築用の JSON ファイルを生成することを目的としたスクレイピングツールである。ポケモンの基本情報・特性・習得技を網羅的に収集し、フェーズ 1.3 時点では `docs/スクレイピングツール開発計画.md` の要件フェーズ 1.1〜1.3 を満たしている。

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

## 今後の課題

- ZA や過去作ページの正規データを別途扱う必要がある場合の拡張（SV 以外の情報ソース管理）。
- HTML 構造変化への耐性向上（BeautifulSoup セレクタの冗長化 / テストフィクスチャ整備）。
- 例外発生時のリトライ戦略やログ蓄積方法の検討。
- JSON スキーマ定義とバリデーション（例: pydantic）による型安全性の向上。

上記のように、app/scraper は SV 図鑑ページを信頼できるソースとして扱い、リダイレクトチェックと進捗管理によって安定した大量スクレイピングを実現している。

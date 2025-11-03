## 概要

このリポジトリは、ポケモンデータベースを構築し、MCP サーバーや Claude Skills など各種ツールをすべてまとめたモノレポリポジトリである。

## データベース

- Supabase のデータベースを採用
- データベースの詳細設計を把握したい場合、docs/DB 設計書.md を参照
- スキーマ変更が発生する場合は、supabase/migrations ディレクトリで migration 管理すること。
- Supabase MCP を使ってデータベースのスキーマ変更をしてはならない。

## アプリケーション

### データベース作成用ツール

#### scraper

- インターネット上の「ポケモン徹底攻略」よりスクレイピングして、JSON ファイルを生成するツール
- 詳細を把握する必要がある場合、app/scraper/README.md を参照。

#### csv_generator

- scraper が生成した JSON ファイルから RDB 投入用の CSV を生成するツール
- 詳細を把握する必要がある場合、app/csv_generator/README.md を参照

#### RDB 投入スクリプト

- csv_generator が生成した CSV ファイルを RDB に投入するシェルスクリプト
- scripts/import_to_supabase.sh で実行可能。
- 詳細を把握する必要がある場合、docs/本番環境データ投入手順書.md を参照

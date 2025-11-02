#!/bin/bash

# ========================================
# ポケモンデータベースSupabase投入スクリプト
# ========================================
#
# CSVファイルをSupabaseのsvスキーマに投入します。
#
# 使用方法:
#   ローカル環境: ./scripts/import_to_supabase.sh
#   本番環境:     ./scripts/import_to_supabase.sh --remote
#
# 前提条件:
#   - Supabase CLIがインストールされていること
#   - ローカル: supabase startでローカル環境が起動していること
#   - 本番: .envファイルにSupabase接続情報が設定されていること
#   - output/配下にCSVファイルが生成されていること
#   - psqlコマンドが利用可能であること
# ========================================

set -e  # エラー時に即座に終了

# カラー出力用
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# プロジェクトルートディレクトリ
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CSV_DIR="$PROJECT_ROOT/output"

# 環境変数（デフォルトはローカル）
ENVIRONMENT="local"

# コマンドライン引数の解析
while [[ $# -gt 0 ]]; do
    case $1 in
        --remote|--production)
            ENVIRONMENT="remote"
            shift
            ;;
        --local)
            ENVIRONMENT="local"
            shift
            ;;
        *)
            echo "不明なオプション: $1"
            echo "使用方法: $0 [--local|--remote]"
            exit 1
            ;;
    esac
done

# PostgreSQL接続情報
if [ "$ENVIRONMENT" = "local" ]; then
    # ローカル環境（Supabase CLI）
    DB_HOST="127.0.0.1"
    DB_PORT="54322"
    DB_NAME="postgres"
    DB_USER="postgres"
    DB_PASSWORD="postgres"
else
    # 本番環境（.envから読み込み）
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        echo -e "${RED}[ERROR]${NC} .envファイルが見つかりません"
        exit 1
    fi

    # .envファイルから環境変数を読み込み
    source "$PROJECT_ROOT/.env"

    # Supabase接続情報の確認
    if [ -z "$SUPABASE_PROJECT_REF" ] || [ -z "$SUPABASE_DB_PASSWORD" ]; then
        echo -e "${RED}[ERROR]${NC} .envファイルに必要な接続情報が設定されていません"
        echo "必要な変数: SUPABASE_PROJECT_REF, SUPABASE_DB_PASSWORD"
        exit 1
    fi

    # Session Pooler接続情報
    DB_HOST="${SUPABASE_DB_HOST:-aws-1-ap-northeast-1.pooler.supabase.com}"
    DB_PORT="${SUPABASE_DB_PORT:-5432}"
    DB_NAME="postgres"  # Supabaseでは常にpostgres
    DB_USER="postgres.${SUPABASE_PROJECT_REF}"
    DB_PASSWORD="$SUPABASE_DB_PASSWORD"
fi

# ログ関数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ========================================
# 前提条件チェック
# ========================================
check_prerequisites() {
    log_info "前提条件をチェック中..."

    # Supabase CLIの確認
    if ! command -v supabase &> /dev/null; then
        log_error "Supabase CLIがインストールされていません"
        log_info "インストール: brew install supabase/tap/supabase"
        exit 1
    fi

    # psqlコマンドの確認
    if ! command -v psql &> /dev/null; then
        log_error "psqlコマンドが見つかりません"
        log_info "PostgreSQLクライアントをインストールしてください: brew install postgresql"
        exit 1
    fi

    # CSVディレクトリの確認
    if [ ! -d "$CSV_DIR" ]; then
        log_error "CSVディレクトリが見つかりません: $CSV_DIR"
        log_info "先にCSV生成ツールを実行してください: uv run python -m app.csv_generator.main"
        exit 1
    fi

    # CSVファイルの確認
    local required_files=("abilities.csv" "moves.csv" "pokemon.csv" "pokemon_abilities.csv" "pokemon_moves.csv")
    for file in "${required_files[@]}"; do
        if [ ! -f "$CSV_DIR/$file" ]; then
            log_error "必要なCSVファイルが見つかりません: $file"
            exit 1
        fi
    done

    log_success "前提条件チェック完了"
}

# ========================================
# PostgreSQL接続ヘルパー関数
# ========================================
execute_sql() {
    local sql="$1"
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$sql" -q
}

execute_sql_with_output() {
    local sql="$1"
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "$sql"
}

# ========================================
# Supabaseプロジェクトの状態確認
# ========================================
check_supabase_status() {
    if [ "$ENVIRONMENT" = "local" ]; then
        log_info "ローカルSupabaseプロジェクトの状態を確認中..."

        cd "$PROJECT_ROOT"

        if ! supabase status &> /dev/null; then
            log_error "Supabaseプロジェクトが起動していません"
            log_info "起動コマンド: supabase start"
            exit 1
        fi

        log_success "ローカルSupabaseプロジェクトが起動しています"
    else
        log_info "本番Supabase環境への接続を確認中..."

        # 接続テスト
        if ! PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" &> /dev/null; then
            log_error "本番Supabase環境に接続できません"
            log_info "接続情報を確認してください"
            exit 1
        fi

        log_success "本番Supabase環境に接続しました"
    fi
}

# ========================================
# テーブルのクリア
# ========================================
clear_tables() {
    if [ "$ENVIRONMENT" = "remote" ]; then
        log_warn "⚠️  本番環境のデータをクリアしようとしています ⚠️"
        log_warn "本当に実行しますか? 'yes' と入力してください: "
        read -r response

        if [ "$response" != "yes" ]; then
            log_info "データクリアをキャンセルしました"
            return
        fi
    else
        log_warn "既存データをクリアしますか? (y/N): "
        read -r response

        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            log_info "データクリアをスキップしました"
            return
        fi
    fi

    log_info "テーブルをクリア中..."

    # 関連テーブルから削除（外部キー制約対応）
    execute_sql "TRUNCATE TABLE sv.pokemon_moves CASCADE;" 2>/dev/null || true
    execute_sql "TRUNCATE TABLE sv.pokemon_abilities CASCADE;" 2>/dev/null || true
    execute_sql "TRUNCATE TABLE sv.pokemon CASCADE;" 2>/dev/null || true
    execute_sql "TRUNCATE TABLE sv.moves CASCADE;" 2>/dev/null || true
    execute_sql "TRUNCATE TABLE sv.abilities CASCADE;" 2>/dev/null || true

    log_success "テーブルクリア完了"
}

# ========================================
# CSVファイルのインポート
# ========================================
import_csv() {
    local table_name=$1
    local csv_file=$2

    log_info "インポート中: $table_name ← $csv_file"

    # psqlコマンドを使用してCOPYコマンドを実行
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
        COPY sv.$table_name FROM STDIN WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
    " < "$CSV_DIR/$csv_file" -q

    # インポート件数を取得
    local count=$(execute_sql_with_output "SELECT COUNT(*) FROM sv.$table_name;" | tr -d ' ')

    log_success "インポート完了: $table_name ($count 件)"
}

# ========================================
# データ整合性チェック
# ========================================
verify_data() {
    log_info "データ整合性チェック中..."

    # 各テーブルの件数を確認
    log_info "テーブルレコード数:"

    local abilities_count=$(execute_sql_with_output "SELECT COUNT(*) FROM sv.abilities;" | tr -d ' ')
    echo "  - abilities: $abilities_count 件"

    local moves_count=$(execute_sql_with_output "SELECT COUNT(*) FROM sv.moves;" | tr -d ' ')
    echo "  - moves: $moves_count 件"

    local pokemon_count=$(execute_sql_with_output "SELECT COUNT(*) FROM sv.pokemon;" | tr -d ' ')
    echo "  - pokemon: $pokemon_count 件"

    local pokemon_abilities_count=$(execute_sql_with_output "SELECT COUNT(*) FROM sv.pokemon_abilities;" | tr -d ' ')
    echo "  - pokemon_abilities: $pokemon_abilities_count 件"

    local pokemon_moves_count=$(execute_sql_with_output "SELECT COUNT(*) FROM sv.pokemon_moves;" | tr -d ' ')
    echo "  - pokemon_moves: $pokemon_moves_count 件"

    # 外部キー制約違反チェック
    log_info "外部キー制約チェック中..."

    # pokemon_abilitiesの整合性チェック
    local invalid_pa=$(execute_sql_with_output "
        SELECT COUNT(*)
        FROM sv.pokemon_abilities pa
        LEFT JOIN sv.pokemon p ON pa.pokemon_id = p.id
        LEFT JOIN sv.abilities a ON pa.ability_id = a.id
        WHERE p.id IS NULL OR a.id IS NULL;
    " | tr -d ' ')

    if [ "$invalid_pa" -gt 0 ]; then
        log_error "pokemon_abilitiesに無効な参照が $invalid_pa 件見つかりました"
    else
        log_success "pokemon_abilities: 整合性OK"
    fi

    # pokemon_movesの整合性チェック
    local invalid_pm=$(execute_sql_with_output "
        SELECT COUNT(*)
        FROM sv.pokemon_moves pm
        LEFT JOIN sv.pokemon p ON pm.pokemon_id = p.id
        LEFT JOIN sv.moves m ON pm.move_id = m.id
        WHERE p.id IS NULL OR m.id IS NULL;
    " | tr -d ' ')

    if [ "$invalid_pm" -gt 0 ]; then
        log_error "pokemon_movesに無効な参照が $invalid_pm 件見つかりました"
    else
        log_success "pokemon_moves: 整合性OK"
    fi

    log_success "データ整合性チェック完了"
}

# ========================================
# メイン処理
# ========================================
main() {
    echo ""
    echo "========================================"
    echo "  ポケモンデータベース Supabase投入"
    if [ "$ENVIRONMENT" = "remote" ]; then
        echo "  環境: 本番 (Remote)"
    else
        echo "  環境: ローカル (Local)"
    fi
    echo "========================================"
    echo ""

    check_prerequisites
    check_supabase_status

    # 本番環境の場合は最終確認
    if [ "$ENVIRONMENT" = "remote" ]; then
        echo ""
        log_warn "========================================="
        log_warn "⚠️  本番環境にデータを投入します ⚠️"
        log_warn "========================================="
        log_warn "投入先: $DB_HOST"
        log_warn ""
        log_warn "続行しますか? 'yes' と入力してください: "
        read -r final_confirm

        if [ "$final_confirm" != "yes" ]; then
            log_info "処理をキャンセルしました"
            exit 0
        fi
        echo ""
    fi

    clear_tables

    echo ""
    log_info "CSVファイルをインポート中..."
    echo ""

    # マスタテーブルから順番にインポート
    import_csv "abilities" "abilities.csv"
    import_csv "moves" "moves.csv"
    import_csv "pokemon" "pokemon.csv"
    import_csv "pokemon_abilities" "pokemon_abilities.csv"
    import_csv "pokemon_moves" "pokemon_moves.csv"

    echo ""
    verify_data

    echo ""
    echo "========================================"
    log_success "インポート処理が正常に完了しました"
    if [ "$ENVIRONMENT" = "remote" ]; then
        log_success "本番環境へのデータ投入が完了しました"
    fi
    echo "========================================"
    echo ""
}

# スクリプト実行
main

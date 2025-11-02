"""バッチ進捗管理ユーティリティ."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_PROGRESS_PATH = Path("data/progress/pokemon_scrape_progress.json")


@dataclass(slots=True)
class BatchProgress:
    """ポケモン図鑑スクレイピングの進捗を表すデータクラス."""

    next_index: int = 0

    @property
    def completed_count(self) -> int:
        """完了済みの件数を返す."""
        return self.next_index


def load_progress(total: int, progress_path: Path = DEFAULT_PROGRESS_PATH) -> BatchProgress:
    """進捗ファイルを読み込み、バリデーションした進捗情報を返す.

    Args:
        total: 対象ポケモンの総数
        progress_path: 進捗ファイルのパス

    Returns:
        BatchProgress: 正常化された進捗情報
    """
    if not progress_path.exists():
        return BatchProgress()

    try:
        raw = json.loads(progress_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return BatchProgress()

    next_index = raw.get("next_index", 0)
    if not isinstance(next_index, int):
        next_index = 0

    next_index = max(0, min(next_index, total))
    return BatchProgress(next_index=next_index)


def save_progress(
    progress: BatchProgress,
    *,
    total: int,
    last_entry: dict[str, Any],
    progress_path: Path = DEFAULT_PROGRESS_PATH,
) -> None:
    """進捗情報をファイルに保存する.

    Args:
        progress: 保存対象の進捗オブジェクト
        total: 対象ポケモンの総数
        last_entry: 直近に処理したポケモンの情報
        progress_path: 進捗ファイルのパス
    """
    payload = {
        "next_index": progress.next_index,
        "completed_count": min(progress.completed_count, total),
        "total_entries": total,
        "remaining_count": max(total - progress.completed_count, 0),
        "last_processed": last_entry,
        "last_updated_utc": datetime.now(tz=timezone.utc).isoformat(),
    }

    progress_path.parent.mkdir(parents=True, exist_ok=True)
    progress_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

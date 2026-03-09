"""テスト実行ログ取得・保存 (Issue #19)

CANoe の測定ログ（BLF/CSV形式）の取得・保存と、
ログデータの構造化を提供する。
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LogEntry:
    """ログエントリ"""

    timestamp: float  # タイムスタンプ (秒)
    channel: int  # チャンネル番号
    message_name: str  # メッセージ名
    signal_name: str  # 信号名
    value: float  # 値
    direction: str = "Rx"  # "Tx" or "Rx"


@dataclass
class TestLog:
    """テスト実行ログ"""

    test_case_id: str
    start_time: str = ""
    end_time: str = ""
    entries: list[LogEntry] = field(default_factory=list)
    log_file_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        """辞書に変換"""
        return {
            "test_case_id": self.test_case_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "entries": [asdict(e) for e in self.entries],
            "log_file_path": self.log_file_path,
        }


class LogManager:
    """ログマネージャ

    テスト実行ログの管理、保存、読み込みを行う。
    """

    DEFAULT_LOG_DIR = "logs"
    LOG_NAME_FORMAT = "{test_case_id}_{timestamp}"

    def __init__(self, log_dir: Path | None = None) -> None:
        self._log_dir = log_dir or Path(self.DEFAULT_LOG_DIR)
        self._logs: dict[str, TestLog] = {}

    @property
    def log_dir(self) -> Path:
        """ログ保存ディレクトリ"""
        return self._log_dir

    def ensure_log_dir(self) -> None:
        """ログディレクトリを作成"""
        self._log_dir.mkdir(parents=True, exist_ok=True)

    def start_log(self, test_case_id: str) -> TestLog:
        """テスト実行ログを開始"""
        log = TestLog(
            test_case_id=test_case_id,
            start_time=datetime.now().isoformat(),
        )
        self._logs[test_case_id] = log
        return log

    def add_entry(self, test_case_id: str, entry: LogEntry) -> None:
        """ログエントリを追加"""
        if test_case_id not in self._logs:
            raise KeyError(f"ログが開始されていません: {test_case_id}")
        self._logs[test_case_id].entries.append(entry)

    def end_log(self, test_case_id: str) -> TestLog:
        """テスト実行ログを終了"""
        if test_case_id not in self._logs:
            raise KeyError(f"ログが開始されていません: {test_case_id}")
        log = self._logs[test_case_id]
        log.end_time = datetime.now().isoformat()
        return log

    def save_log_csv(self, test_case_id: str) -> Path:
        """ログを CSV 形式で保存

        Returns:
            保存先ファイルパス
        """
        if test_case_id not in self._logs:
            raise KeyError(f"ログが見つかりません: {test_case_id}")

        self.ensure_log_dir()
        log = self._logs[test_case_id]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{test_case_id}_{timestamp}.csv"
        file_path = self._log_dir / filename

        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "channel", "message_name", "signal_name",
                             "value", "direction"])
            for entry in log.entries:
                writer.writerow([
                    entry.timestamp, entry.channel, entry.message_name,
                    entry.signal_name, entry.value, entry.direction,
                ])

        log.log_file_path = str(file_path)
        logger.info("ログを保存しました: %s", file_path)
        return file_path

    def save_log_json(self, test_case_id: str) -> Path:
        """ログを JSON 形式で保存"""
        if test_case_id not in self._logs:
            raise KeyError(f"ログが見つかりません: {test_case_id}")

        self.ensure_log_dir()
        log = self._logs[test_case_id]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{test_case_id}_{timestamp}.json"
        file_path = self._log_dir / filename

        file_path.write_text(
            json.dumps(log.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        log.log_file_path = str(file_path)
        logger.info("ログを保存しました: %s", file_path)
        return file_path

    def load_log_csv(self, file_path: Path) -> TestLog:
        """CSV ログファイルを読み込み"""
        entries: list[LogEntry] = []
        with open(file_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                entries.append(LogEntry(
                    timestamp=float(row["timestamp"]),
                    channel=int(row["channel"]),
                    message_name=row["message_name"],
                    signal_name=row["signal_name"],
                    value=float(row["value"]),
                    direction=row.get("direction", "Rx"),
                ))

        test_case_id = file_path.stem.split("_")[0]
        log = TestLog(
            test_case_id=test_case_id,
            entries=entries,
            log_file_path=str(file_path),
        )
        return log

    def load_log_json(self, file_path: Path) -> TestLog:
        """JSON ログファイルを読み込み"""
        data = json.loads(file_path.read_text(encoding="utf-8"))
        entries = [LogEntry(**e) for e in data.get("entries", [])]
        return TestLog(
            test_case_id=data["test_case_id"],
            start_time=data.get("start_time", ""),
            end_time=data.get("end_time", ""),
            entries=entries,
            log_file_path=str(file_path),
        )

    def get_log(self, test_case_id: str) -> TestLog | None:
        """テストケースIDでログを取得"""
        return self._logs.get(test_case_id)

    def get_all_logs(self) -> list[TestLog]:
        """全ログを取得"""
        return list(self._logs.values())

"""テスト実行ログ テスト (Issue #19)"""

from pathlib import Path

import pytest

from src.engine.log_manager import LogEntry, LogManager, TestLog


class TestLogEntry:
    def test_create_entry(self) -> None:
        entry = LogEntry(
            timestamp=1.0, channel=1, message_name="EngineData",
            signal_name="EngineSpeed", value=3000.0,
        )
        assert entry.timestamp == 1.0
        assert entry.direction == "Rx"


class TestTestLog:
    def test_to_dict(self) -> None:
        log = TestLog(test_case_id="TC-001")
        log.entries.append(LogEntry(1.0, 1, "Msg", "Sig", 100.0))
        d = log.to_dict()
        assert d["test_case_id"] == "TC-001"
        assert len(d["entries"]) == 1


class TestLogManager:
    def test_start_log(self) -> None:
        mgr = LogManager()
        log = mgr.start_log("TC-001")
        assert log.test_case_id == "TC-001"
        assert log.start_time != ""

    def test_add_entry(self) -> None:
        mgr = LogManager()
        mgr.start_log("TC-001")
        entry = LogEntry(1.0, 1, "Msg", "Sig", 100.0)
        mgr.add_entry("TC-001", entry)
        log = mgr.get_log("TC-001")
        assert log is not None
        assert len(log.entries) == 1

    def test_add_entry_not_started_raises(self) -> None:
        mgr = LogManager()
        with pytest.raises(KeyError):
            mgr.add_entry("TC-999", LogEntry(0, 0, "", "", 0))

    def test_end_log(self) -> None:
        mgr = LogManager()
        mgr.start_log("TC-001")
        log = mgr.end_log("TC-001")
        assert log.end_time != ""

    def test_save_load_csv(self, tmp_path: Path) -> None:
        mgr = LogManager(log_dir=tmp_path)
        mgr.start_log("TC-001")
        mgr.add_entry("TC-001", LogEntry(1.0, 1, "Msg", "Sig", 100.0))
        mgr.add_entry("TC-001", LogEntry(2.0, 1, "Msg", "Sig", 200.0))

        csv_path = mgr.save_log_csv("TC-001")
        assert csv_path.exists()

        loaded = mgr.load_log_csv(csv_path)
        assert len(loaded.entries) == 2
        assert loaded.entries[0].value == 100.0

    def test_save_load_json(self, tmp_path: Path) -> None:
        mgr = LogManager(log_dir=tmp_path)
        mgr.start_log("TC-001")
        mgr.add_entry("TC-001", LogEntry(1.0, 1, "Msg", "Sig", 100.0))
        mgr.end_log("TC-001")

        json_path = mgr.save_log_json("TC-001")
        assert json_path.exists()

        loaded = mgr.load_log_json(json_path)
        assert loaded.test_case_id == "TC-001"
        assert len(loaded.entries) == 1

    def test_get_all_logs(self) -> None:
        mgr = LogManager()
        mgr.start_log("TC-001")
        mgr.start_log("TC-002")
        assert len(mgr.get_all_logs()) == 2

    def test_save_not_started_raises(self) -> None:
        mgr = LogManager()
        with pytest.raises(KeyError):
            mgr.save_log_csv("TC-999")

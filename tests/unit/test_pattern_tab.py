"""テストパターン作成タブのテスト

テストパターン入力フォーム、信号選択、一括変換連携のテスト。
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.gui.pattern_tab import PatternTab
from src.models.signal_model import Protocol, SignalInfo, SignalRepository
from src.models.test_pattern import TestPattern, TestPatternRepository


@pytest.fixture
def repository():
    repo = SignalRepository()
    repo.add_signals([
        SignalInfo("EngineSpeed", "EngineData", 256, "unsigned",
                   0, 8000, "rpm", "ECU1 -> ECU2", "test.dbc", Protocol.CAN),
        SignalInfo("Speed", "VehicleSpeed", 512, "unsigned",
                   0, 250, "km/h", "ECU2 -> ECU1", "test.dbc", Protocol.CAN),
    ])
    return repo


@pytest.fixture
def pattern_repo():
    return TestPatternRepository()


@pytest.fixture
def mock_parent():
    parent = MagicMock()
    return parent


class TestPatternTab:
    """テストパターン作成タブのテスト"""

    def test_creation(self, mock_parent, repository, pattern_repo):
        tab = PatternTab(mock_parent, repository, pattern_repo)
        assert tab.pattern_repository is pattern_repo
        assert tab.signal_repository is repository

    def test_add_pattern(self, mock_parent, repository, pattern_repo):
        tab = PatternTab(mock_parent, repository, pattern_repo)
        pattern = tab.create_pattern(
            test_case_name="エンジン回転数確認",
            target_signal="EngineSpeed",
            operation="エンジン回転数を3000rpmに設定",
            expected_value="3000",
            precondition="エンジン稼働中",
            wait_time_ms=100,
            remarks="テスト用",
        )
        assert pattern.test_case_id == "TC-001"
        assert pattern.test_case_name == "エンジン回転数確認"
        assert pattern_repo.count == 1

    def test_add_multiple_patterns(self, mock_parent, repository, pattern_repo):
        tab = PatternTab(mock_parent, repository, pattern_repo)
        tab.create_pattern("テスト1", "EngineSpeed", "操作1", "期待1")
        tab.create_pattern("テスト2", "Speed", "操作2", "期待2")
        assert pattern_repo.count == 2
        patterns = pattern_repo.get_all()
        assert patterns[0].test_case_id == "TC-001"
        assert patterns[1].test_case_id == "TC-002"

    def test_delete_pattern(self, mock_parent, repository, pattern_repo):
        tab = PatternTab(mock_parent, repository, pattern_repo)
        tab.create_pattern("テスト1", "EngineSpeed", "操作1", "期待1")
        assert pattern_repo.count == 1
        tab.delete_pattern("TC-001")
        assert pattern_repo.count == 0

    def test_delete_nonexistent_raises(self, mock_parent, repository, pattern_repo):
        tab = PatternTab(mock_parent, repository, pattern_repo)
        with pytest.raises(KeyError):
            tab.delete_pattern("TC-999")

    def test_get_all_patterns(self, mock_parent, repository, pattern_repo):
        tab = PatternTab(mock_parent, repository, pattern_repo)
        tab.create_pattern("テスト1", "EngineSpeed", "操作1", "期待1")
        tab.create_pattern("テスト2", "Speed", "操作2", "期待2")
        all_patterns = tab.get_all_patterns()
        assert len(all_patterns) == 2

    def test_save_load_patterns(self, mock_parent, repository, pattern_repo, tmp_path):
        tab = PatternTab(mock_parent, repository, pattern_repo)
        tab.create_pattern("テスト1", "EngineSpeed", "操作1", "期待1")
        tab.create_pattern("テスト2", "Speed", "操作2", "期待2")

        json_path = tmp_path / "patterns.json"
        tab.save_patterns(json_path)
        assert json_path.exists()

        # 新しいリポジトリに読込
        new_repo = TestPatternRepository()
        new_tab = PatternTab(mock_parent, repository, new_repo)
        new_tab.load_patterns(json_path)
        assert new_repo.count == 2

    def test_pattern_to_row(self, mock_parent, repository, pattern_repo):
        tab = PatternTab(mock_parent, repository, pattern_repo)
        pattern = tab.create_pattern("テスト1", "EngineSpeed", "操作1", "期待1", wait_time_ms=100)
        row = tab.pattern_to_row(pattern)
        assert row[0] == "TC-001"
        assert row[1] == "テスト1"
        assert row[2] == "EngineSpeed"

    def test_update_pattern(self, mock_parent, repository, pattern_repo):
        tab = PatternTab(mock_parent, repository, pattern_repo)
        tab.create_pattern("テスト1", "EngineSpeed", "操作1", "期待1")
        updated = TestPattern(
            test_case_name="更新テスト",
            target_signal="Speed",
            operation="操作更新",
            expected_value="期待更新",
        )
        result = tab.update_pattern("TC-001", updated)
        assert result.test_case_name == "更新テスト"
        assert result.test_case_id == "TC-001"

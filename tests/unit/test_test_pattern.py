"""テストパターンデータモデル テスト (Issue #13)"""

from pathlib import Path

import pytest

from src.models.test_pattern import TestPattern, TestPatternRepository


class TestTestPattern:
    def test_create_pattern(self) -> None:
        p = TestPattern(test_case_name="エンジン回転数テスト")
        assert p.test_case_name == "エンジン回転数テスト"
        assert p.test_case_id == ""

    def test_to_dict(self) -> None:
        p = TestPattern(test_case_name="テスト1", operation="信号送信")
        d = p.to_dict()
        assert d["test_case_name"] == "テスト1"
        assert d["operation"] == "信号送信"

    def test_from_dict(self) -> None:
        data = {"test_case_name": "テスト2", "wait_time_ms": 500}
        p = TestPattern.from_dict(data)
        assert p.test_case_name == "テスト2"
        assert p.wait_time_ms == 500


class TestTestPatternRepository:
    def test_add_auto_assigns_id(self) -> None:
        repo = TestPatternRepository()
        p = repo.add(TestPattern(test_case_name="テスト1"))
        assert p.test_case_id == "TC-001"

    def test_add_sequential_ids(self) -> None:
        repo = TestPatternRepository()
        repo.add(TestPattern(test_case_name="テスト1"))
        p2 = repo.add(TestPattern(test_case_name="テスト2"))
        assert p2.test_case_id == "TC-002"

    def test_count(self) -> None:
        repo = TestPatternRepository()
        assert repo.count == 0
        repo.add(TestPattern(test_case_name="テスト1"))
        assert repo.count == 1

    def test_get_all(self) -> None:
        repo = TestPatternRepository()
        repo.add(TestPattern(test_case_name="テスト1"))
        repo.add(TestPattern(test_case_name="テスト2"))
        assert len(repo.get_all()) == 2

    def test_get_by_id(self) -> None:
        repo = TestPatternRepository()
        repo.add(TestPattern(test_case_name="テスト1"))
        p = repo.get("TC-001")
        assert p.test_case_name == "テスト1"

    def test_get_nonexistent_raises(self) -> None:
        repo = TestPatternRepository()
        with pytest.raises(KeyError):
            repo.get("TC-999")

    def test_update(self) -> None:
        repo = TestPatternRepository()
        repo.add(TestPattern(test_case_name="テスト1"))
        updated = TestPattern(test_case_name="更新済み")
        result = repo.update("TC-001", updated)
        assert result.test_case_name == "更新済み"
        assert result.test_case_id == "TC-001"

    def test_update_nonexistent_raises(self) -> None:
        repo = TestPatternRepository()
        with pytest.raises(KeyError):
            repo.update("TC-999", TestPattern())

    def test_delete(self) -> None:
        repo = TestPatternRepository()
        repo.add(TestPattern(test_case_name="テスト1"))
        repo.delete("TC-001")
        assert repo.count == 0

    def test_delete_nonexistent_raises(self) -> None:
        repo = TestPatternRepository()
        with pytest.raises(KeyError):
            repo.delete("TC-999")

    def test_save_and_load_json(self, tmp_path: Path) -> None:
        repo = TestPatternRepository()
        repo.add(TestPattern(test_case_name="テスト1", operation="信号送信"))
        repo.add(TestPattern(test_case_name="テスト2", wait_time_ms=1000))

        json_file = tmp_path / "patterns.json"
        repo.save_to_json(json_file)

        # 新しいリポジトリに読み込み
        repo2 = TestPatternRepository()
        repo2.load_from_json(json_file)

        assert repo2.count == 2
        assert repo2.get("TC-001").test_case_name == "テスト1"
        assert repo2.get("TC-002").wait_time_ms == 1000

    def test_load_preserves_next_id(self, tmp_path: Path) -> None:
        repo = TestPatternRepository()
        repo.add(TestPattern(test_case_name="テスト1"))
        repo.add(TestPattern(test_case_name="テスト2"))

        json_file = tmp_path / "patterns.json"
        repo.save_to_json(json_file)

        repo2 = TestPatternRepository()
        repo2.load_from_json(json_file)
        p3 = repo2.add(TestPattern(test_case_name="テスト3"))
        assert p3.test_case_id == "TC-003"

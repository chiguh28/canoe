"""ログ解析・判定ロジック テスト (Issue #20)"""

from src.engine.judgment import (
    ChangeDirection,
    JudgmentCriteria,
    JudgmentDetail,
    JudgmentEngine,
    JudgmentResult,
    JudgmentType,
)
from src.engine.log_manager import LogEntry, TestLog


def _make_log(entries: list[LogEntry]) -> TestLog:
    return TestLog(test_case_id="TC-001", entries=entries)


class TestJudgmentExact:
    def test_exact_match_ok(self) -> None:
        engine = JudgmentEngine()
        log = _make_log([LogEntry(1.0, 1, "Msg", "Sig", 100.0)])
        criteria = JudgmentCriteria(
            judgment_type=JudgmentType.EXACT,
            signal_name="Sig",
            expected_value=100.0,
        )
        result = engine.judge("TC-001", log, criteria)
        assert result.result == JudgmentResult.OK

    def test_exact_match_ng(self) -> None:
        engine = JudgmentEngine()
        log = _make_log([LogEntry(1.0, 1, "Msg", "Sig", 105.0)])
        criteria = JudgmentCriteria(
            judgment_type=JudgmentType.EXACT,
            signal_name="Sig",
            expected_value=100.0,
        )
        result = engine.judge("TC-001", log, criteria)
        assert result.result == JudgmentResult.NG

    def test_exact_with_tolerance_ok(self) -> None:
        engine = JudgmentEngine()
        log = _make_log([LogEntry(1.0, 1, "Msg", "Sig", 101.0)])
        criteria = JudgmentCriteria(
            judgment_type=JudgmentType.EXACT,
            signal_name="Sig",
            expected_value=100.0,
            tolerance=2.0,
        )
        result = engine.judge("TC-001", log, criteria)
        assert result.result == JudgmentResult.OK

    def test_exact_no_entries_error(self) -> None:
        engine = JudgmentEngine()
        log = _make_log([])
        criteria = JudgmentCriteria(
            judgment_type=JudgmentType.EXACT,
            signal_name="Sig",
            expected_value=100.0,
        )
        result = engine.judge("TC-001", log, criteria)
        assert result.result == JudgmentResult.ERROR

    def test_exact_no_expected_error(self) -> None:
        engine = JudgmentEngine()
        log = _make_log([LogEntry(1.0, 1, "Msg", "Sig", 100.0)])
        criteria = JudgmentCriteria(
            judgment_type=JudgmentType.EXACT,
            signal_name="Sig",
        )
        result = engine.judge("TC-001", log, criteria)
        assert result.result == JudgmentResult.ERROR


class TestJudgmentRange:
    def test_range_ok(self) -> None:
        engine = JudgmentEngine()
        log = _make_log([LogEntry(1.0, 1, "Msg", "Sig", 50.0)])
        criteria = JudgmentCriteria(
            judgment_type=JudgmentType.RANGE,
            signal_name="Sig",
            range_min=0.0,
            range_max=100.0,
        )
        result = engine.judge("TC-001", log, criteria)
        assert result.result == JudgmentResult.OK

    def test_range_ng_too_high(self) -> None:
        engine = JudgmentEngine()
        log = _make_log([LogEntry(1.0, 1, "Msg", "Sig", 150.0)])
        criteria = JudgmentCriteria(
            judgment_type=JudgmentType.RANGE,
            signal_name="Sig",
            range_min=0.0,
            range_max=100.0,
        )
        result = engine.judge("TC-001", log, criteria)
        assert result.result == JudgmentResult.NG

    def test_range_boundary_ok(self) -> None:
        engine = JudgmentEngine()
        log = _make_log([LogEntry(1.0, 1, "Msg", "Sig", 100.0)])
        criteria = JudgmentCriteria(
            judgment_type=JudgmentType.RANGE,
            signal_name="Sig",
            range_min=0.0,
            range_max=100.0,
        )
        result = engine.judge("TC-001", log, criteria)
        assert result.result == JudgmentResult.OK


class TestJudgmentChange:
    def test_increase_ok(self) -> None:
        engine = JudgmentEngine()
        log = _make_log([
            LogEntry(1.0, 1, "Msg", "Sig", 100.0),
            LogEntry(2.0, 1, "Msg", "Sig", 200.0),
        ])
        criteria = JudgmentCriteria(
            judgment_type=JudgmentType.CHANGE,
            signal_name="Sig",
            change_direction=ChangeDirection.INCREASE,
        )
        result = engine.judge("TC-001", log, criteria)
        assert result.result == JudgmentResult.OK

    def test_decrease_ok(self) -> None:
        engine = JudgmentEngine()
        log = _make_log([
            LogEntry(1.0, 1, "Msg", "Sig", 200.0),
            LogEntry(2.0, 1, "Msg", "Sig", 100.0),
        ])
        criteria = JudgmentCriteria(
            judgment_type=JudgmentType.CHANGE,
            signal_name="Sig",
            change_direction=ChangeDirection.DECREASE,
        )
        result = engine.judge("TC-001", log, criteria)
        assert result.result == JudgmentResult.OK

    def test_no_change_ok(self) -> None:
        engine = JudgmentEngine()
        log = _make_log([
            LogEntry(1.0, 1, "Msg", "Sig", 100.0),
            LogEntry(2.0, 1, "Msg", "Sig", 100.0),
        ])
        criteria = JudgmentCriteria(
            judgment_type=JudgmentType.CHANGE,
            signal_name="Sig",
            change_direction=ChangeDirection.NO_CHANGE,
        )
        result = engine.judge("TC-001", log, criteria)
        assert result.result == JudgmentResult.OK

    def test_change_insufficient_entries(self) -> None:
        engine = JudgmentEngine()
        log = _make_log([LogEntry(1.0, 1, "Msg", "Sig", 100.0)])
        criteria = JudgmentCriteria(
            judgment_type=JudgmentType.CHANGE,
            signal_name="Sig",
            change_direction=ChangeDirection.INCREASE,
        )
        result = engine.judge("TC-001", log, criteria)
        assert result.result == JudgmentResult.ERROR


class TestJudgmentTimeout:
    def test_timeout_ok(self) -> None:
        engine = JudgmentEngine()
        log = _make_log([
            LogEntry(1.0, 1, "Msg", "Sig", 100.0),
            LogEntry(1.1, 1, "Msg", "Sig", 200.0),
        ])
        criteria = JudgmentCriteria(
            judgment_type=JudgmentType.TIMEOUT,
            signal_name="Sig",
            timeout_ms=200.0,
        )
        result = engine.judge("TC-001", log, criteria)
        assert result.result == JudgmentResult.OK

    def test_timeout_ng(self) -> None:
        engine = JudgmentEngine()
        log = _make_log([
            LogEntry(1.0, 1, "Msg", "Sig", 100.0),
            LogEntry(2.0, 1, "Msg", "Sig", 200.0),
        ])
        criteria = JudgmentCriteria(
            judgment_type=JudgmentType.TIMEOUT,
            signal_name="Sig",
            timeout_ms=500.0,
        )
        result = engine.judge("TC-001", log, criteria)
        assert result.result == JudgmentResult.NG

    def test_timeout_no_signal_ng(self) -> None:
        engine = JudgmentEngine()
        log = _make_log([])
        criteria = JudgmentCriteria(
            judgment_type=JudgmentType.TIMEOUT,
            signal_name="Sig",
            timeout_ms=1000.0,
        )
        result = engine.judge("TC-001", log, criteria)
        assert result.result == JudgmentResult.NG


class TestJudgmentCompound:
    def test_compound_and_all_ok(self) -> None:
        engine = JudgmentEngine()
        log = _make_log([
            LogEntry(1.0, 1, "Msg", "Sig1", 100.0),
            LogEntry(1.0, 1, "Msg", "Sig2", 50.0),
        ])
        criteria = JudgmentCriteria(
            judgment_type=JudgmentType.COMPOUND,
            signal_name="compound",
            compound_operator="AND",
            sub_criteria=[
                JudgmentCriteria(JudgmentType.EXACT, "Sig1", expected_value=100.0),
                JudgmentCriteria(JudgmentType.RANGE, "Sig2", range_min=0.0, range_max=100.0),
            ],
        )
        result = engine.judge("TC-001", log, criteria)
        assert result.result == JudgmentResult.OK

    def test_compound_and_one_ng(self) -> None:
        engine = JudgmentEngine()
        log = _make_log([
            LogEntry(1.0, 1, "Msg", "Sig1", 999.0),
            LogEntry(1.0, 1, "Msg", "Sig2", 50.0),
        ])
        criteria = JudgmentCriteria(
            judgment_type=JudgmentType.COMPOUND,
            signal_name="compound",
            compound_operator="AND",
            sub_criteria=[
                JudgmentCriteria(JudgmentType.EXACT, "Sig1", expected_value=100.0),
                JudgmentCriteria(JudgmentType.RANGE, "Sig2", range_min=0.0, range_max=100.0),
            ],
        )
        result = engine.judge("TC-001", log, criteria)
        assert result.result == JudgmentResult.NG

    def test_compound_or_one_ok(self) -> None:
        engine = JudgmentEngine()
        log = _make_log([
            LogEntry(1.0, 1, "Msg", "Sig1", 999.0),
            LogEntry(1.0, 1, "Msg", "Sig2", 50.0),
        ])
        criteria = JudgmentCriteria(
            judgment_type=JudgmentType.COMPOUND,
            signal_name="compound",
            compound_operator="OR",
            sub_criteria=[
                JudgmentCriteria(JudgmentType.EXACT, "Sig1", expected_value=100.0),
                JudgmentCriteria(JudgmentType.RANGE, "Sig2", range_min=0.0, range_max=100.0),
            ],
        )
        result = engine.judge("TC-001", log, criteria)
        assert result.result == JudgmentResult.OK

    def test_compound_empty_sub_criteria_error(self) -> None:
        engine = JudgmentEngine()
        log = _make_log([])
        criteria = JudgmentCriteria(
            judgment_type=JudgmentType.COMPOUND,
            signal_name="compound",
        )
        result = engine.judge("TC-001", log, criteria)
        assert result.result == JudgmentResult.ERROR


class TestJudgmentDetail:
    def test_to_dict(self) -> None:
        detail = JudgmentDetail(
            test_case_id="TC-001",
            result=JudgmentResult.OK,
            judgment_type=JudgmentType.EXACT,
            signal_name="Sig",
        )
        d = detail.to_dict()
        assert d["result"] == "OK"
        assert d["judgment_type"] == "exact"

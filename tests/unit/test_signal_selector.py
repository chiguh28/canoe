"""信号選択UI テスト (Issue #12)"""

from unittest.mock import MagicMock

from src.gui.signal_selector import SignalSelector
from src.models.signal_model import Protocol, SignalInfo, SignalRepository


def _make_signal(name: str = "TestSig", message: str = "TestMsg") -> SignalInfo:
    return SignalInfo(
        signal_name=name,
        message_name=message,
        message_id=0x100,
        data_type="unsigned",
        min_value=0.0,
        max_value=255.0,
        unit="rpm",
        node_info="ECU1 -> ECU2",
        source_file="test.dbc",
        protocol=Protocol.CAN,
    )


class TestSignalSelectorCreation:
    def test_creates_with_repo(self) -> None:
        parent = MagicMock()
        repo = SignalRepository()
        selector = SignalSelector(parent, repo)
        assert selector.repository is repo

    def test_has_search_entry(self) -> None:
        selector = SignalSelector(MagicMock(), SignalRepository())
        assert hasattr(selector, "search_entry")

    def test_has_combo(self) -> None:
        selector = SignalSelector(MagicMock(), SignalRepository())
        assert hasattr(selector, "signal_combo")

    def test_has_detail_labels(self) -> None:
        selector = SignalSelector(MagicMock(), SignalRepository())
        assert "signal_name" in selector.detail_labels


class TestSignalSelectorSearch:
    def test_get_signal_names(self) -> None:
        repo = SignalRepository()
        repo.add_signals([_make_signal("EngSpeed"), _make_signal("VehSpeed")])
        selector = SignalSelector(MagicMock(), repo)
        names = selector.get_signal_names()
        assert len(names) == 2
        assert "TestMsg.EngSpeed" in names

    def test_filter_signals(self) -> None:
        repo = SignalRepository()
        repo.add_signals(
            [
                _make_signal("EngineSpeed"),
                _make_signal("BrakeStatus"),
            ]
        )
        selector = SignalSelector(MagicMock(), repo)
        results = selector.filter_signals("engine")
        assert len(results) == 1
        assert "EngineSpeed" in results[0]

    def test_filter_empty_returns_all(self) -> None:
        repo = SignalRepository()
        repo.add_signals([_make_signal("A"), _make_signal("B")])
        selector = SignalSelector(MagicMock(), repo)
        assert len(selector.filter_signals("")) == 2


class TestSignalSelectorSelection:
    def test_initial_selection_empty(self) -> None:
        selector = SignalSelector(MagicMock(), SignalRepository())
        assert selector.get_selected_signals() == []

    def test_find_signal_by_display_name(self) -> None:
        repo = SignalRepository()
        sig = _make_signal("EngSpeed")
        repo.add_signals([sig])
        selector = SignalSelector(MagicMock(), repo)
        found = selector._find_signal_by_display_name("TestMsg.EngSpeed")
        assert found is not None
        assert found.signal_name == "EngSpeed"

    def test_find_nonexistent_signal(self) -> None:
        selector = SignalSelector(MagicMock(), SignalRepository())
        assert selector._find_signal_by_display_name("NotExist") is None

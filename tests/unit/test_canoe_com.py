"""CANoe COM API テスト (Issue #16)"""

from unittest.mock import MagicMock, patch

import pytest

from src.engine.canoe_com import (
    CANoeCOMWrapper,
    CANoeError,
    CANoeState,
)


class TestCANoeCOMWrapperState:
    def test_initial_state_disconnected(self) -> None:
        wrapper = CANoeCOMWrapper()
        assert wrapper.state == CANoeState.DISCONNECTED

    def test_config_path_initially_empty(self) -> None:
        wrapper = CANoeCOMWrapper()
        assert wrapper.config_path == ""


class TestCANoeCOMWrapperConnect:
    def test_connect_without_win32com_raises(self) -> None:
        wrapper = CANoeCOMWrapper()
        with patch.dict("sys.modules", {"win32com": None, "win32com.client": None}):
            with pytest.raises(CANoeError, match="win32com"):
                wrapper.connect()

    def test_connect_success_with_mock(self) -> None:
        wrapper = CANoeCOMWrapper()
        mock_client = MagicMock()
        mock_app = MagicMock()
        mock_client.Dispatch.return_value = mock_app

        with patch.dict("sys.modules", {"win32com": MagicMock(), "win32com.client": mock_client}):
            wrapper.connect()

        assert wrapper.state == CANoeState.CONNECTED

    def test_disconnect(self) -> None:
        wrapper = CANoeCOMWrapper()
        wrapper._state = CANoeState.CONNECTED
        wrapper._app = MagicMock()
        wrapper._measurement = MagicMock()

        wrapper.disconnect()

        assert wrapper.state == CANoeState.DISCONNECTED
        assert wrapper._app is None


class TestCANoeCOMWrapperConfig:
    def test_load_config_not_connected_raises(self) -> None:
        wrapper = CANoeCOMWrapper()
        with pytest.raises(CANoeError, match="接続されていません"):
            wrapper.load_config("test.cfg")

    def test_load_config_success(self) -> None:
        wrapper = CANoeCOMWrapper()
        wrapper._state = CANoeState.CONNECTED
        wrapper._app = MagicMock()

        wrapper.load_config("test.cfg")

        wrapper._app.Open.assert_called_once_with("test.cfg")
        assert wrapper.config_path == "test.cfg"


class TestCANoeCOMWrapperMeasurement:
    def test_start_measurement_not_connected_raises(self) -> None:
        wrapper = CANoeCOMWrapper()
        with pytest.raises(CANoeError, match="接続されていません"):
            wrapper.start_measurement()

    def test_start_measurement_success(self) -> None:
        wrapper = CANoeCOMWrapper()
        wrapper._state = CANoeState.CONNECTED
        wrapper._measurement = MagicMock()

        wrapper.start_measurement()

        assert wrapper.state == CANoeState.MEASURING
        wrapper._measurement.Start.assert_called_once()

    def test_stop_measurement_success(self) -> None:
        wrapper = CANoeCOMWrapper()
        wrapper._state = CANoeState.MEASURING
        wrapper._measurement = MagicMock()

        wrapper.stop_measurement()

        assert wrapper.state == CANoeState.CONNECTED
        wrapper._measurement.Stop.assert_called_once()


class TestCANoeCOMWrapperSignals:
    def test_set_signal_not_measuring_raises(self) -> None:
        wrapper = CANoeCOMWrapper()
        wrapper._state = CANoeState.CONNECTED
        with pytest.raises(CANoeError, match="測定中ではありません"):
            wrapper.set_signal_value(1, "Msg", "Sig", 100.0)

    def test_get_signal_not_measuring_raises(self) -> None:
        wrapper = CANoeCOMWrapper()
        wrapper._state = CANoeState.CONNECTED
        with pytest.raises(CANoeError, match="測定中ではありません"):
            wrapper.get_signal_value(1, "Msg", "Sig")

    def test_set_signal_value_success(self) -> None:
        wrapper = CANoeCOMWrapper()
        wrapper._state = CANoeState.MEASURING
        mock_app = MagicMock()
        wrapper._app = mock_app

        wrapper.set_signal_value(1, "EngineData", "EngineSpeed", 3000.0)

        mock_app.Bus.GetSignal.assert_called_once_with(1, "EngineData", "EngineSpeed")

    def test_get_signal_value_success(self) -> None:
        wrapper = CANoeCOMWrapper()
        wrapper._state = CANoeState.MEASURING
        mock_app = MagicMock()
        mock_sig = MagicMock()
        mock_sig.Value = 3000.0
        mock_app.Bus.GetSignal.return_value = mock_sig
        wrapper._app = mock_app

        value = wrapper.get_signal_value(1, "EngineData", "EngineSpeed")
        assert value == 3000.0

"""CANoe COM API ラッパー (Issue #16)

pywin32 (win32com.client) を使用して CANoe との連携基盤を提供する。
Windows 環境でのみ動作し、Linux ではモック可能な設計。
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CANoeState(Enum):
    """CANoe の接続状態"""

    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    MEASURING = "measuring"


class CANoeError(Exception):
    """CANoe COM API エラー"""


class CANoeNotFoundError(CANoeError):
    """CANoe が起動していない場合のエラー"""


class CANoeCOMWrapper:
    """CANoe COM API ラッパークラス

    CANoe アプリケーションとの接続・操作を抽象化する。
    テスト時にはモック化して使用する。
    """

    def __init__(self) -> None:
        self._app: Any = None
        self._measurement: Any = None
        self._state: CANoeState = CANoeState.DISCONNECTED
        self._config_path: str = ""

    @property
    def state(self) -> CANoeState:
        """現在の接続状態"""
        return self._state

    @property
    def config_path(self) -> str:
        """ロード中の構成ファイルパス"""
        return self._config_path

    def connect(self) -> None:
        """CANoe アプリケーションに接続

        Raises:
            CANoeNotFoundError: CANoe が起動していない場合
            CANoeError: COM 接続に失敗した場合
        """
        try:
            import win32com.client  # noqa: F811

            self._app = win32com.client.Dispatch("CANoe.Application")
            self._measurement = self._app.Measurement
            self._state = CANoeState.CONNECTED
            logger.info("CANoe に接続しました")
        except ImportError as e:
            raise CANoeError(
                "win32com が利用できません。Windows 環境で pywin32 をインストールしてください。"
            ) from e
        except Exception as e:
            error_msg = str(e)
            if "Class not registered" in error_msg or "Could not connect" in error_msg:
                raise CANoeNotFoundError(
                    "CANoe が起動していません。CANoe を起動してから再試行してください。"
                ) from e
            raise CANoeError(f"CANoe への接続に失敗しました: {e}") from e

    def disconnect(self) -> None:
        """CANoe から切断"""
        if self._state == CANoeState.MEASURING:
            self.stop_measurement()
        self._app = None
        self._measurement = None
        self._state = CANoeState.DISCONNECTED
        logger.info("CANoe から切断しました")

    def load_config(self, config_path: str) -> None:
        """構成ファイル (.cfg) をロード

        Args:
            config_path: .cfg ファイルのパス

        Raises:
            CANoeError: 接続されていない場合、またはロードに失敗した場合
        """
        if self._state == CANoeState.DISCONNECTED:
            raise CANoeError("CANoe に接続されていません")

        try:
            self._app.Open(config_path)
            self._config_path = config_path
            logger.info("構成ファイルをロードしました: %s", config_path)
        except Exception as e:
            raise CANoeError(f"構成ファイルのロードに失敗しました: {e}") from e

    def start_measurement(self) -> None:
        """測定を開始

        Raises:
            CANoeError: 接続されていない場合
        """
        if self._state == CANoeState.DISCONNECTED:
            raise CANoeError("CANoe に接続されていません")

        try:
            self._measurement.Start()
            self._state = CANoeState.MEASURING
            logger.info("測定を開始しました")
        except Exception as e:
            raise CANoeError(f"測定の開始に失敗しました: {e}") from e

    def stop_measurement(self) -> None:
        """測定を停止

        Raises:
            CANoeError: 接続されていない場合
        """
        if self._state == CANoeState.DISCONNECTED:
            raise CANoeError("CANoe に接続されていません")

        try:
            self._measurement.Stop()
            self._state = CANoeState.CONNECTED
            logger.info("測定を停止しました")
        except Exception as e:
            raise CANoeError(f"測定の停止に失敗しました: {e}") from e

    def set_signal_value(self, channel: int, message: str, signal: str, value: float) -> None:
        """信号値を送信

        Args:
            channel: チャンネル番号
            message: メッセージ名
            signal: 信号名
            value: 設定する値

        Raises:
            CANoeError: 測定中でない場合
        """
        if self._state != CANoeState.MEASURING:
            raise CANoeError("測定中ではありません。先に測定を開始してください。")

        try:
            bus = self._app.Bus
            sig = bus.GetSignal(channel, message, signal)
            sig.Value = value
            logger.debug("信号値を設定: ch=%d, %s.%s = %f", channel, message, signal, value)
        except Exception as e:
            raise CANoeError(f"信号値の設定に失敗しました: {e}") from e

    def get_signal_value(self, channel: int, message: str, signal: str) -> float:
        """信号値を受信

        Args:
            channel: チャンネル番号
            message: メッセージ名
            signal: 信号名

        Returns:
            現在の信号値

        Raises:
            CANoeError: 測定中でない場合
        """
        if self._state != CANoeState.MEASURING:
            raise CANoeError("測定中ではありません。先に測定を開始してください。")

        try:
            bus = self._app.Bus
            sig = bus.GetSignal(channel, message, signal)
            return float(sig.Value)
        except Exception as e:
            raise CANoeError(f"信号値の取得に失敗しました: {e}") from e

"""DBC Parser Module

cantools ライブラリを使用して .dbc ファイルをパースし、
SignalInfo オブジェクトのリストに変換する。
"""

from pathlib import Path

import cantools
from cantools.database.can.database import Database as CANDatabase
from cantools.database.can.message import Message as CANMessage
from cantools.database.can.signal import Signal as CANSignal

from src.models.signal_model import Protocol, SignalInfo


class DBCParseError(Exception):
    """DBC パースエラー"""

    pass


class DBCParser:
    """DBC ファイルパーサー"""

    def parse(self, dbc_path: Path) -> list[SignalInfo]:
        """DBC ファイルをパースして SignalInfo のリストを返す

        Args:
            dbc_path: .dbc ファイルのパス

        Returns:
            SignalInfo オブジェクトのリスト

        Raises:
            DBCParseError: ファイルが存在しない、またはパースに失敗した場合
        """
        # ファイル存在確認
        if not dbc_path.exists():
            raise DBCParseError(f"DBC file not found: {dbc_path}")

        # ファイルが空でないか確認
        if dbc_path.stat().st_size == 0:
            raise DBCParseError(f"DBC file is empty: {dbc_path}")

        try:
            # cantools でパース
            db = cantools.database.load_file(str(dbc_path))
            # DBC ファイルは CAN データベースであることを確認
            if not isinstance(db, CANDatabase):
                raise DBCParseError(f"Not a valid CAN database: {dbc_path}")
        except DBCParseError:
            raise
        except Exception as e:
            raise DBCParseError(f"Failed to parse DBC file: {dbc_path}. Error: {e}") from e

        # SignalInfo リストに変換
        signals: list[SignalInfo] = []
        for message in db.messages:
            signals.extend(self._convert_message_signals(message, dbc_path))

        return signals

    def _convert_message_signals(self, message: CANMessage, source_file: Path) -> list[SignalInfo]:
        """メッセージ内の全信号を SignalInfo に変換

        Args:
            message: cantools の Message オブジェクト
            source_file: 元の .dbc ファイルパス

        Returns:
            SignalInfo オブジェクトのリスト
        """
        signals: list[SignalInfo] = []

        for signal in message.signals:
            signal_info = self._convert_signal(signal, message, source_file)
            signals.append(signal_info)

        return signals

    def _convert_signal(
        self, signal: CANSignal, message: CANMessage, source_file: Path
    ) -> SignalInfo:
        """cantools の Signal オブジェクトを SignalInfo に変換

        Args:
            signal: cantools の Signal オブジェクト
            message: 親メッセージ
            source_file: 元の .dbc ファイルパス

        Returns:
            SignalInfo オブジェクト
        """
        # データ型（signed/unsigned）
        data_type = "signed" if signal.is_signed else "unsigned"

        # 物理値の範囲（cantools が既に物理値を返している）
        min_value = float(signal.minimum) if signal.minimum is not None else 0.0
        max_value = float(signal.maximum) if signal.maximum is not None else 0.0

        # ノード情報（送信元 -> 受信先1, 受信先2）
        node_info = self._format_node_info(message, signal)

        return SignalInfo(
            signal_name=signal.name,
            message_name=message.name,
            message_id=message.frame_id,
            data_type=data_type,
            min_value=min_value,
            max_value=max_value,
            unit=signal.unit or "",
            node_info=node_info,
            source_file=str(source_file),
            protocol=Protocol.CAN,
        )

    def _format_node_info(self, message: CANMessage, signal: CANSignal) -> str:
        """ノード情報をフォーマット

        Args:
            message: cantools の Message オブジェクト
            signal: cantools の Signal オブジェクト

        Returns:
            "送信元 -> 受信先1, 受信先2" 形式の文字列
        """
        sender = message.senders[0] if message.senders else "Unknown"

        # 受信先リスト
        receivers = signal.receivers if signal.receivers else []
        receiver_str = ", ".join(receivers) if receivers else ""

        return f"{sender} -> {receiver_str}"

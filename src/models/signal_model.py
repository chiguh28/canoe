"""信号情報データモデル

Phase 1 設計書 3.1 に準拠。
DBC (CAN) と LDF (LIN) の異なるフォーマットから取得した
信号情報を統一的に扱うためのデータモデルを提供する。
"""

from dataclasses import dataclass, field
from enum import Enum


class Protocol(Enum):
    """通信プロトコル種別"""

    CAN = "CAN"
    LIN = "LIN"


@dataclass(frozen=True)
class SignalInfo:
    """DBC/LDF 共通の正規化信号情報モデル

    要件定義書 3.1.1 に準拠。
    DBC (CAN) と LDF (LIN) の異なるフォーマットから取得した
    信号情報を統一的に扱うためのデータクラス。
    """

    signal_name: str  # 信号名
    message_name: str  # メッセージ名（LDF: フレーム名）
    message_id: int  # メッセージID（LDF: フレームID）
    data_type: str  # データ型（"unsigned", "signed", "float" 等）
    min_value: float  # 最小値（物理値）
    max_value: float  # 最大値（物理値）
    unit: str  # 物理単位（"rpm", "km/h", "" 等）
    node_info: str  # 送受信ノード情報（"ECU1 -> ECU2" 形式）
    source_file: str  # 元ファイルパス
    protocol: Protocol  # CAN or LIN

    @property
    def display_name(self) -> str:
        """GUI表示用の名称（メッセージ名.信号名）"""
        return f"{self.message_name}.{self.signal_name}"

    def matches_query(self, query: str) -> bool:
        """検索クエリに一致するか判定"""
        q = query.lower()
        return q in self.signal_name.lower() or q in self.message_name.lower()


@dataclass(frozen=True)
class MessageInfo:
    """メッセージ/フレーム情報"""

    name: str  # メッセージ名
    message_id: int  # メッセージID
    sender_node: str  # 送信ノード
    signals: tuple[SignalInfo, ...] = field(default_factory=tuple)
    source_file: str = ""
    protocol: Protocol = Protocol.CAN


class SignalRepository:
    """信号情報のインメモリリポジトリ

    セッション中に読み込んだ全信号情報を保持し、
    検索・フィルタ機能を提供する。
    （要件定義書 3.1.1「データ保持」に準拠）
    """

    def __init__(self) -> None:
        self._signals: list[SignalInfo] = []

    def add_signals(self, signals: list[SignalInfo]) -> None:
        """信号情報を追加"""
        self._signals.extend(signals)

    def clear(self) -> None:
        """全信号情報をクリア"""
        self._signals.clear()

    def get_all(self) -> list[SignalInfo]:
        """全信号情報を取得"""
        return list(self._signals)

    def search(self, query: str) -> list[SignalInfo]:
        """信号名・メッセージ名で検索"""
        if not query:
            return self.get_all()
        return [s for s in self._signals if s.matches_query(query)]

    def filter_by_protocol(self, protocol: Protocol) -> list[SignalInfo]:
        """プロトコル（CAN/LIN）でフィルタ"""
        return [s for s in self._signals if s.protocol == protocol]

    def get_by_message(self, message_name: str) -> list[SignalInfo]:
        """メッセージ名で信号を取得"""
        return [s for s in self._signals if s.message_name == message_name]

    @property
    def count(self) -> int:
        """登録信号数"""
        return len(self._signals)

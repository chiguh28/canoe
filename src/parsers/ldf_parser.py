"""LDF Parser Module

ldfparser ライブラリを使用して .ldf ファイルをパースし、
SignalInfo オブジェクトのリストに変換する。
"""

from pathlib import Path

import ldfparser  # type: ignore[import-untyped]

from src.models.signal_model import Protocol, SignalInfo


class LDFParseError(Exception):
    """LDF パースエラー"""

    pass


class LDFParser:
    """LDF ファイルパーサー"""

    def parse(self, ldf_path: Path | str) -> list[SignalInfo]:
        """LDF ファイルをパースして SignalInfo のリストを返す

        Args:
            ldf_path: .ldf ファイルのパス (Path または str)

        Returns:
            SignalInfo オブジェクトのリスト

        Raises:
            LDFParseError: ファイルが存在しない、またはパースに失敗した場合
        """
        # Path に変換
        if isinstance(ldf_path, str):
            ldf_path = Path(ldf_path)

        # ファイル存在確認
        if not ldf_path.exists():
            raise LDFParseError(f"File not found: {ldf_path}")

        # ファイルが空でないか確認
        if ldf_path.stat().st_size == 0:
            raise LDFParseError(f"LDF file is empty: {ldf_path}")

        try:
            # ldfparser でパース
            ldf = ldfparser.parse_ldf(str(ldf_path))
        except Exception as e:
            raise LDFParseError(f"Failed to parse LDF file: {ldf_path}. Error: {e}") from e

        # SignalInfo リストに変換
        signals: list[SignalInfo] = []

        # 全フレームを走査
        for frame in ldf.get_unconditional_frames():
            signals.extend(self._convert_frame_signals(frame, ldf, ldf_path))

        return signals

    def _convert_frame_signals(
        self,
        frame: ldfparser.LinUnconditionalFrame,
        ldf: ldfparser.LDF,
        source_file: Path,
    ) -> list[SignalInfo]:
        """フレーム内の全信号を SignalInfo に変換

        Args:
            frame: ldfparser の LinUnconditionalFrame オブジェクト
            ldf: LDF 全体のデータ
            source_file: 元の .ldf ファイルパス

        Returns:
            SignalInfo オブジェクトのリスト
        """
        signals: list[SignalInfo] = []

        # signal_map は [(offset, LinSignal), ...] のリスト
        for _offset, lin_signal in frame.signal_map:
            signal_info = self._convert_signal(lin_signal, frame, ldf, source_file)
            signals.append(signal_info)

        return signals

    def _convert_signal(
        self,
        signal: ldfparser.LinSignal,
        frame: ldfparser.LinUnconditionalFrame,
        ldf: ldfparser.LDF,
        source_file: Path,
    ) -> SignalInfo:
        """ldfparser の LinSignal オブジェクトを SignalInfo に変換

        Args:
            signal: ldfparser の LinSignal オブジェクト
            frame: 親フレーム
            ldf: LDF 全体のデータ
            source_file: 元の .ldf ファイルパス

        Returns:
            SignalInfo オブジェクト
        """
        # データ型判定（LINでは基本的に unsigned/signed）
        data_type = "unsigned"  # デフォルト

        # 物理値の範囲とユニットを取得
        min_value, max_value, unit = self._get_signal_physical_info(signal, ldf)

        # ノード情報（publisher -> subscribers）
        node_info = self._format_node_info(signal)

        return SignalInfo(
            signal_name=signal.name,
            message_name=frame.name,
            message_id=frame.frame_id,
            data_type=data_type,
            min_value=min_value,
            max_value=max_value,
            unit=unit,
            node_info=node_info,
            source_file=str(source_file),
            protocol=Protocol.LIN,
        )

    def _get_signal_physical_info(
        self, signal: ldfparser.LinSignal, ldf: ldfparser.LDF
    ) -> tuple[float, float, str]:
        """信号の物理値情報（min, max, unit）を取得

        Args:
            signal: ldfparser の LinSignal オブジェクト
            ldf: LDF 全体のデータ

        Returns:
            (min_value, max_value, unit) のタプル
        """
        min_value = 0.0
        max_value = 0.0
        unit = ""

        # エンコーディング情報を取得
        if signal.encoding_type:
            converters = signal.encoding_type.get_converters()
            if converters:
                # 最初の converter (通常は PhysicalValue) を使用
                converter = converters[0]
                if hasattr(converter, "phy_min"):
                    min_value = float(converter.phy_min)
                if hasattr(converter, "phy_max"):
                    max_value = float(converter.phy_max)
                if hasattr(converter, "unit"):
                    unit = converter.unit or ""

        return min_value, max_value, unit

    def _format_node_info(self, signal: ldfparser.LinSignal) -> str:
        """ノード情報をフォーマット

        Args:
            signal: ldfparser の LinSignal オブジェクト

        Returns:
            "publisher -> subscriber1, subscriber2" 形式の文字列
        """
        publisher = signal.publisher if hasattr(signal, "publisher") else "Unknown"

        # subscribers リスト（LinSlave オブジェクトから名前を抽出）
        subscriber_names = []
        if hasattr(signal, "subscribers") and signal.subscribers:
            for sub in signal.subscribers:
                if hasattr(sub, "name"):
                    subscriber_names.append(sub.name)
                else:
                    subscriber_names.append(str(sub))

        subscriber_str = ", ".join(subscriber_names) if subscriber_names else ""

        return f"{publisher} -> {subscriber_str}"

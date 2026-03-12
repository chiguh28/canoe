"""信号選択UI (Issue #12)

テストパターン作成画面における信号選択コンボボックスと
絞り込み検索機能を提供する。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src.models.signal_model import SignalInfo, SignalRepository


class SignalSelector:
    """信号選択コンポーネント

    コンボボックスによる信号選択と絞り込み検索、
    選択した信号の詳細情報表示を提供する。
    """

    def __init__(
        self,
        parent: tk.Widget | ttk.Frame,
        repository: SignalRepository,
    ) -> None:
        self.parent = parent
        self.repository = repository
        self._selected_signals: list[SignalInfo] = []
        self._on_selection_callback: object = None

        self._create_widgets()

    def _create_widgets(self) -> None:
        """ウィジェット生成"""
        # メインフレーム
        main_frame = ttk.LabelFrame(self.parent, text="信号選択")
        main_frame.pack(fill=tk.X, padx=5, pady=5)

        # 検索フレーム
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(search_frame, text="信号検索:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_var.trace_add("write", self._on_search_changed)

        # コンボボックス
        combo_frame = ttk.Frame(main_frame)
        combo_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(combo_frame, text="信号:").pack(side=tk.LEFT)
        self.signal_combo = ttk.Combobox(combo_frame, state="readonly", width=40)
        self.signal_combo.pack(side=tk.LEFT, padx=5)
        self.signal_combo.bind("<<ComboboxSelected>>", self._on_combo_selected)

        # 追加ボタン
        self.add_button = ttk.Button(combo_frame, text="追加", command=self._on_add_signal)
        self.add_button.pack(side=tk.LEFT, padx=5)

        # 詳細情報パネル
        self.detail_frame = ttk.LabelFrame(self.parent, text="信号詳細")
        self.detail_frame.pack(fill=tk.X, padx=5, pady=5)

        self.detail_labels: dict[str, ttk.Label] = {}
        detail_fields = [
            ("signal_name", "信号名"),
            ("message_name", "メッセージ名"),
            ("data_type", "データ型"),
            ("min_max", "値範囲"),
            ("unit", "単位"),
            ("protocol", "プロトコル"),
        ]
        for key, label_text in detail_fields:
            row = ttk.Frame(self.detail_frame)
            row.pack(fill=tk.X, padx=5, pady=2)
            ttk.Label(row, text=f"{label_text}:", width=15).pack(side=tk.LEFT)
            value_label = ttk.Label(row, text="-")
            value_label.pack(side=tk.LEFT)
            self.detail_labels[key] = value_label

        # 選択済み信号リスト
        self.selected_listbox_frame = ttk.LabelFrame(self.parent, text="選択済み信号")
        self.selected_listbox_frame.pack(fill=tk.BOTH, padx=5, pady=5)

        self.selected_listbox = tk.Listbox(self.selected_listbox_frame, height=5)
        self.selected_listbox.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)

        remove_btn = ttk.Button(
            self.selected_listbox_frame, text="削除", command=self._on_remove_signal
        )
        remove_btn.pack(side=tk.RIGHT, padx=5, pady=5)

    def _on_search_changed(self, *_args: object) -> None:
        """検索テキスト変更時"""
        self._update_combo_values()

    def _update_combo_values(self) -> None:
        """コンボボックスの選択肢を更新"""
        try:
            query = str(self.search_var.get())
        except Exception:
            query = ""
        signals = self.repository.search(query)
        values = [s.display_name for s in signals]
        self.signal_combo["values"] = values

    def _on_combo_selected(self, _event: object = None) -> None:
        """コンボボックス選択時"""
        selected_name = self.signal_combo.get()
        signal = self._find_signal_by_display_name(selected_name)
        if signal:
            self._show_signal_detail(signal)

    def _on_add_signal(self) -> None:
        """信号追加ボタン押下"""
        selected_name = self.signal_combo.get()
        signal = self._find_signal_by_display_name(selected_name)
        if signal and signal not in self._selected_signals:
            self._selected_signals.append(signal)
            self.selected_listbox.insert(tk.END, signal.display_name)

    def _on_remove_signal(self) -> None:
        """選択済み信号削除"""
        selection = self.selected_listbox.curselection()
        if selection:
            idx = selection[0]
            self.selected_listbox.delete(idx)
            self._selected_signals.pop(idx)

    def _find_signal_by_display_name(self, display_name: str) -> SignalInfo | None:
        """表示名から SignalInfo を検索"""
        for s in self.repository.get_all():
            if s.display_name == display_name:
                return s
        return None

    def _show_signal_detail(self, signal: SignalInfo) -> None:
        """信号の詳細情報を表示"""
        self.detail_labels["signal_name"].config(text=signal.signal_name)
        self.detail_labels["message_name"].config(text=signal.message_name)
        self.detail_labels["data_type"].config(text=signal.data_type)
        self.detail_labels["min_max"].config(text=f"{signal.min_value} ~ {signal.max_value}")
        self.detail_labels["unit"].config(text=signal.unit or "-")
        self.detail_labels["protocol"].config(text=signal.protocol.value)

    def get_selected_signals(self) -> list[SignalInfo]:
        """選択された信号のリストを返す"""
        return list(self._selected_signals)

    def get_signal_names(self) -> list[str]:
        """リポジトリ内の全信号の表示名リストを返す"""
        return [s.display_name for s in self.repository.get_all()]

    def filter_signals(self, query: str) -> list[str]:
        """検索クエリで絞り込んだ信号名リストを返す"""
        signals = self.repository.search(query)
        return [s.display_name for s in signals]

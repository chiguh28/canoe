"""テストパターン作成タブ

テストパターンの入力フォーム、信号選択、一覧表示、
保存・読込、一括変換連携を提供する。
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from src.gui.error_messages import ErrorMessages
from src.models.signal_model import SignalRepository
from src.models.test_pattern import TestPattern, TestPatternRepository


class PatternTab:
    """テストパターン作成タブ

    テストパターンの入力・編集・削除・保存・読込を管理する。
    """

    COLUMNS = [
        "test_case_id", "test_case_name", "target_signal",
        "operation", "expected_value", "precondition",
        "wait_time_ms", "remarks",
    ]

    COLUMN_HEADERS = [
        "TC-ID", "テストケース名", "対象信号",
        "操作内容", "期待値", "前提条件",
        "待機時間(ms)", "備考",
    ]

    def __init__(
        self,
        parent: tk.Widget | ttk.Frame,
        signal_repository: SignalRepository,
        pattern_repository: TestPatternRepository | None = None,
    ) -> None:
        self.parent = parent
        self.signal_repository = signal_repository
        self.pattern_repository = pattern_repository or TestPatternRepository()

        self._create_widgets()

    def _create_widgets(self) -> None:
        """ウィジェット生成"""
        # 入力フォームフレーム
        form_frame = ttk.LabelFrame(self.parent, text="テストパターン入力")
        form_frame.pack(fill=tk.X, padx=5, pady=5)

        # フィールド定義
        fields = [
            ("テストケース名:", "name_var"),
            ("対象信号:", "signal_var"),
            ("操作内容:", "operation_var"),
            ("期待値:", "expected_var"),
            ("前提条件:", "precondition_var"),
            ("待機時間(ms):", "wait_var"),
            ("備考:", "remarks_var"),
        ]

        self._form_vars: dict[str, tk.StringVar] = {}
        for label, var_name in fields:
            row = ttk.Frame(form_frame)
            row.pack(fill=tk.X, padx=5, pady=2)
            ttk.Label(row, text=label, width=15).pack(side=tk.LEFT)

            if var_name == "signal_var":
                # 信号選択はコンボボックス
                var = tk.StringVar()
                self._form_vars[var_name] = var
                self.signal_combo = ttk.Combobox(row, textvariable=var, state="readonly", width=40)
                self.signal_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
                self._update_signal_combo()
            else:
                var = tk.StringVar()
                self._form_vars[var_name] = var
                entry = ttk.Entry(row, textvariable=var, width=50)
                entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # ボタンフレーム
        btn_frame = ttk.Frame(form_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        self.add_button = ttk.Button(btn_frame, text="追加", command=self._on_add)
        self.add_button.pack(side=tk.LEFT, padx=5)

        self.update_button = ttk.Button(btn_frame, text="更新", command=self._on_update)
        self.update_button.pack(side=tk.LEFT, padx=5)

        self.delete_button = ttk.Button(btn_frame, text="削除", command=self._on_delete)
        self.delete_button.pack(side=tk.LEFT, padx=5)

        self.clear_button = ttk.Button(btn_frame, text="クリア", command=self._on_clear_form)
        self.clear_button.pack(side=tk.LEFT, padx=5)

        # ファイル操作ボタン
        file_btn_frame = ttk.Frame(form_frame)
        file_btn_frame.pack(fill=tk.X, padx=5, pady=5)

        self.save_button = ttk.Button(
            file_btn_frame, text="パターン保存", command=self._on_save
        )
        self.save_button.pack(side=tk.LEFT, padx=5)

        self.load_button = ttk.Button(
            file_btn_frame, text="パターン読込", command=self._on_load
        )
        self.load_button.pack(side=tk.LEFT, padx=5)

        # パターン一覧 Treeview
        tree_frame = ttk.LabelFrame(self.parent, text="テストパターン一覧")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        self.treeview = ttk.Treeview(
            tree_frame,
            columns=self.COLUMNS,
            show="headings",
            yscrollcommand=scrollbar_y.set,
        )
        scrollbar_y.config(command=self.treeview.yview)

        for col, header in zip(self.COLUMNS, self.COLUMN_HEADERS, strict=True):
            self.treeview.heading(col, text=header)
            self.treeview.column(col, width=120, minwidth=80)

        self.treeview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.treeview.bind("<<TreeviewSelect>>", self._on_tree_select)

    def _update_signal_combo(self) -> None:
        """信号コンボボックスの選択肢を更新"""
        signals = self.signal_repository.get_all()
        values = [s.display_name for s in signals]
        if hasattr(self, "signal_combo"):
            self.signal_combo["values"] = values

    def refresh_signals(self) -> None:
        """信号リストを外部から更新"""
        self._update_signal_combo()

    def _on_add(self) -> None:
        """追加ボタン"""
        name = self._form_vars["name_var"].get()
        if not name:
            messagebox.showwarning("警告", "テストケース名を入力してください")
            return

        self.create_pattern(
            test_case_name=name,
            target_signal=self._form_vars["signal_var"].get(),
            operation=self._form_vars["operation_var"].get(),
            expected_value=self._form_vars["expected_var"].get(),
            precondition=self._form_vars.get("precondition_var", tk.StringVar()).get(),
            wait_time_ms=int(self._form_vars.get("wait_var", tk.StringVar()).get() or "0"),
            remarks=self._form_vars.get("remarks_var", tk.StringVar()).get(),
        )
        self._on_clear_form()
        self._refresh_treeview()

    def _on_update(self) -> None:
        """更新ボタン"""
        selection = self.treeview.selection()
        if not selection:
            messagebox.showwarning("警告", "更新するパターンを選択してください")
            return

        item = self.treeview.item(selection[0])
        tc_id = item["values"][0]

        updated = TestPattern(
            test_case_name=self._form_vars["name_var"].get(),
            target_signal=self._form_vars["signal_var"].get(),
            operation=self._form_vars["operation_var"].get(),
            expected_value=self._form_vars["expected_var"].get(),
            precondition=self._form_vars.get("precondition_var", tk.StringVar()).get(),
            wait_time_ms=int(self._form_vars.get("wait_var", tk.StringVar()).get() or "0"),
            remarks=self._form_vars.get("remarks_var", tk.StringVar()).get(),
        )
        try:
            self.update_pattern(str(tc_id), updated)
            self._refresh_treeview()
        except KeyError:
            messagebox.showerror("エラー", f"パターンが見つかりません: {tc_id}")

    def _on_delete(self) -> None:
        """削除ボタン"""
        selection = self.treeview.selection()
        if not selection:
            messagebox.showwarning("警告", "削除するパターンを選択してください")
            return

        item = self.treeview.item(selection[0])
        tc_id = item["values"][0]
        try:
            self.delete_pattern(str(tc_id))
            self._refresh_treeview()
            self._on_clear_form()
        except KeyError:
            messagebox.showerror("エラー", f"パターンが見つかりません: {tc_id}")

    def _on_clear_form(self) -> None:
        """フォームクリア"""
        for var in self._form_vars.values():
            var.set("")

    def _on_tree_select(self, _event: object = None) -> None:
        """Treeview 行選択時にフォームに反映"""
        selection = self.treeview.selection()
        if not selection:
            return

        item = self.treeview.item(selection[0])
        values = item["values"]
        if len(values) >= 8:
            self._form_vars["name_var"].set(str(values[1]))
            self._form_vars["signal_var"].set(str(values[2]))
            self._form_vars["operation_var"].set(str(values[3]))
            self._form_vars["expected_var"].set(str(values[4]))
            self._form_vars["precondition_var"].set(str(values[5]))
            self._form_vars["wait_var"].set(str(values[6]))
            self._form_vars["remarks_var"].set(str(values[7]))

    def _on_save(self) -> None:
        """パターン保存ダイアログ"""
        path = filedialog.asksaveasfilename(
            title="テストパターンを保存",
            defaultextension=".json",
            filetypes=[("JSONファイル", "*.json"), ("すべて", "*.*")],
        )
        if path:
            try:
                self.save_patterns(Path(path))
                messagebox.showinfo("完了", f"保存しました: {path}")
            except Exception as e:
                messagebox.showerror("エラー", ErrorMessages.save_error(path, str(e)))

    def _on_load(self) -> None:
        """パターン読込ダイアログ"""
        path = filedialog.askopenfilename(
            title="テストパターンを読込",
            filetypes=[("JSONファイル", "*.json"), ("すべて", "*.*")],
        )
        if path:
            try:
                self.load_patterns(Path(path))
                self._refresh_treeview()
                messagebox.showinfo("完了", f"読込みました: {path}")
            except Exception as e:
                messagebox.showerror("エラー", ErrorMessages.parse_error(path, str(e)))

    def _refresh_treeview(self) -> None:
        """Treeview を更新"""
        for item in self.treeview.get_children():
            self.treeview.delete(item)

        for pattern in self.pattern_repository.get_all():
            row = self.pattern_to_row(pattern)
            self.treeview.insert("", tk.END, values=row)

    # --- Public API ---

    def create_pattern(
        self,
        test_case_name: str,
        target_signal: str,
        operation: str,
        expected_value: str,
        precondition: str = "",
        wait_time_ms: int = 0,
        remarks: str = "",
    ) -> TestPattern:
        """テストパターンを作成・追加"""
        pattern = TestPattern(
            test_case_name=test_case_name,
            target_signal=target_signal,
            operation=operation,
            expected_value=expected_value,
            precondition=precondition,
            wait_time_ms=wait_time_ms,
            remarks=remarks,
        )
        return self.pattern_repository.add(pattern)

    def delete_pattern(self, test_case_id: str) -> None:
        """テストパターンを削除"""
        self.pattern_repository.delete(test_case_id)

    def update_pattern(self, test_case_id: str, updated: TestPattern) -> TestPattern:
        """テストパターンを更新"""
        return self.pattern_repository.update(test_case_id, updated)

    def get_all_patterns(self) -> list[TestPattern]:
        """全テストパターンを取得"""
        return self.pattern_repository.get_all()

    def save_patterns(self, path: Path) -> None:
        """テストパターンをJSONファイルに保存"""
        self.pattern_repository.save_to_json(path)

    def load_patterns(self, path: Path) -> None:
        """テストパターンをJSONファイルから読込"""
        self.pattern_repository.load_from_json(path)

    def pattern_to_row(self, pattern: TestPattern) -> tuple[str, ...]:
        """TestPattern を Treeview の行データに変換"""
        return (
            pattern.test_case_id,
            pattern.test_case_name,
            pattern.target_signal,
            pattern.operation,
            pattern.expected_value,
            pattern.precondition,
            str(pattern.wait_time_ms),
            pattern.remarks,
        )

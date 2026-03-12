"""結果・帳票タブ (Issue #24 - F02)

テスト実行結果の表示と Excel 帳票出力を管理する。
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.engine.judgment import JudgmentDetail
    from src.engine.test_runner import ExecutionSummary


class ResultTab:
    """結果・帳票タブ

    テスト実行結果の表示と Excel 帳票出力を管理する。
    """

    def __init__(
        self,
        parent: tk.Widget | ttk.Frame,
    ) -> None:
        self.parent = parent
        self._summary: ExecutionSummary | None = None
        self._judgments: list[JudgmentDetail] = []
        self._create_widgets()

    def _create_widgets(self) -> None:
        """ウィジェット生成"""
        # サマリフレーム
        summary_frame = ttk.LabelFrame(self.parent, text="実行結果サマリ")
        summary_frame.pack(fill=tk.X, padx=5, pady=5)

        # OK/NG/ERROR 数を表示するラベル群
        self.total_label = ttk.Label(summary_frame, text="総テスト数: 0")
        self.total_label.pack(side=tk.LEFT, padx=10, pady=5)

        self.passed_label = ttk.Label(summary_frame, text="成功: 0", foreground="green")
        self.passed_label.pack(side=tk.LEFT, padx=10, pady=5)

        self.failed_label = ttk.Label(summary_frame, text="失敗: 0", foreground="red")
        self.failed_label.pack(side=tk.LEFT, padx=10, pady=5)

        self.error_label = ttk.Label(summary_frame, text="エラー: 0", foreground="orange")
        self.error_label.pack(side=tk.LEFT, padx=10, pady=5)

        self.pass_rate_label = ttk.Label(summary_frame, text="合格率: 0.0%")
        self.pass_rate_label.pack(side=tk.LEFT, padx=10, pady=5)

        # 帳票出力ボタン
        export_frame = ttk.Frame(self.parent)
        export_frame.pack(fill=tk.X, padx=5, pady=5)

        self.export_button = ttk.Button(export_frame, text="Excel帳票出力", command=self._on_export)
        self.export_button.pack(side=tk.LEFT, padx=5)
        self.export_button.config(state=tk.DISABLED)  # 初期状態は無効

        # 結果テーブル（Treeview）
        tree_frame = ttk.LabelFrame(self.parent, text="テスト結果詳細")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ("test_id", "test_name", "status", "actual", "expected", "message")
        self.result_tree = ttk.Treeview(tree_frame, columns=columns, show="headings")

        # カラムヘッダー設定
        self.result_tree.heading("test_id", text="テストID")
        self.result_tree.heading("test_name", text="テスト名")
        self.result_tree.heading("status", text="結果")
        self.result_tree.heading("actual", text="実測値")
        self.result_tree.heading("expected", text="期待値")
        self.result_tree.heading("message", text="メッセージ")

        # カラム幅設定
        self.result_tree.column("test_id", width=100)
        self.result_tree.column("test_name", width=200)
        self.result_tree.column("status", width=80)
        self.result_tree.column("actual", width=100)
        self.result_tree.column("expected", width=100)
        self.result_tree.column("message", width=200)

        # スクロールバー
        scrollbar_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        scrollbar_x = ttk.Scrollbar(
            tree_frame, orient=tk.HORIZONTAL, command=self.result_tree.xview
        )
        self.result_tree.config(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        # レイアウト
        self.result_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

    def set_results(
        self,
        summary: ExecutionSummary,
        judgments: list[JudgmentDetail],
    ) -> None:
        """結果データを設定して表示を更新

        Args:
            summary: 実行サマリ
            judgments: 判定詳細リスト
        """
        self._summary = summary
        self._judgments = judgments
        self._refresh_display()

    def _refresh_display(self) -> None:
        """表示を更新"""
        if self._summary is None:
            return

        # サマリラベル更新
        self.total_label.config(text=f"総テスト数: {self._summary.total}")
        self.passed_label.config(text=f"成功: {self._summary.passed}")
        self.failed_label.config(text=f"失敗: {self._summary.failed}")
        self.error_label.config(text=f"エラー: {self._summary.error}")
        self.pass_rate_label.config(text=f"合格率: {self._summary.pass_rate:.1f}%")

        # エクスポートボタンを有効化
        self.export_button.config(state=tk.NORMAL)

        # Treeview 更新
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)

        for judgment in self._judgments:
            values = (
                judgment.test_case_id,
                getattr(judgment, "test_case_name", "-"),
                judgment.result.value,
                str(judgment.actual_value) if judgment.actual_value else "-",
                str(judgment.expected_value) if judgment.expected_value else "-",
                judgment.reason or "",
            )
            # ステータスに応じて色分け（タグ設定）
            tag = "passed" if judgment.result.value == "OK" else "failed"
            self.result_tree.insert("", tk.END, values=values, tags=(tag,))

        # タグの色設定
        self.result_tree.tag_configure("passed", foreground="green")
        self.result_tree.tag_configure("failed", foreground="red")

    def _on_export(self) -> None:
        """Excel 帳票出力"""
        if self._summary is None:
            messagebox.showwarning("警告", "出力する結果がありません")
            return

        # ファイル保存ダイアログ
        file_path = filedialog.asksaveasfilename(
            title="Excel帳票を保存",
            defaultextension=".xlsx",
            filetypes=[("Excel ファイル", "*.xlsx"), ("すべてのファイル", "*.*")],
        )

        if not file_path:
            return  # キャンセル

        try:
            # Excel 帳票生成
            from src.report.excel_report import ExcelReportGenerator

            generator = ExcelReportGenerator()
            generator.generate(
                summary=self._summary,
                judgments=self._judgments,
                output_path=Path(file_path),
            )
            messagebox.showinfo("完了", f"Excel帳票を出力しました。\n\n{file_path}")
        except Exception as e:
            messagebox.showerror(
                "エラー",
                f"Excel帳票の出力中にエラーが発生しました。\n\n詳細: {e}",
            )

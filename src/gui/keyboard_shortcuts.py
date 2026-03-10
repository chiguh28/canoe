"""キーボードショートカット管理 (Issue #24)

アプリケーション全体のキーボードショートカットを管理する。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class ShortcutEntry:
    """ショートカット定義"""

    key: str
    description: str
    callback: Callable[[], None]


class KeyboardShortcutManager:
    """キーボードショートカットマネージャ

    ショートカットキーの登録・解除・一覧表示を管理する。
    """

    def __init__(self) -> None:
        self._shortcuts: dict[str, ShortcutEntry] = {}

    def register(
        self, key: str, description: str, callback: Callable[[], None]
    ) -> None:
        """ショートカットを登録

        Args:
            key: キーバインド文字列 (例: "Ctrl+O")
            description: 機能説明
            callback: 実行するコールバック関数
        """
        self._shortcuts[key] = ShortcutEntry(
            key=key, description=description, callback=callback
        )

    def unregister(self, key: str) -> None:
        """ショートカットを解除"""
        self._shortcuts.pop(key, None)

    def get_shortcuts(self) -> list[str]:
        """登録済みショートカットキーの一覧を取得"""
        return list(self._shortcuts.keys())

    def get_description(self, key: str) -> str:
        """ショートカットの説明を取得"""
        entry = self._shortcuts.get(key)
        return entry.description if entry else ""

    def get_callback(self, key: str) -> Callable[[], None] | None:
        """ショートカットのコールバックを取得"""
        entry = self._shortcuts.get(key)
        return entry.callback if entry else None

    def get_formatted_list(self) -> str:
        """ショートカット一覧をフォーマットされた文字列で取得"""
        lines = []
        for key, entry in self._shortcuts.items():
            lines.append(f"{key}: {entry.description}")
        return "\n".join(lines)

    @staticmethod
    def get_default_shortcuts() -> dict[str, str]:
        """デフォルトのショートカット定義を取得"""
        return {
            "Ctrl+O": "ファイルを開く",
            "Ctrl+S": "保存",
            "Ctrl+Q": "終了",
            "F5": "テスト実行",
            "Escape": "中断",
            "Ctrl+F": "検索",
            "Ctrl+E": "Excel帳票出力",
        }

    def bind_to_widget(self, widget: object) -> None:
        """tkinter ウィジェットにショートカットをバインド

        Args:
            widget: バインド対象の tkinter ウィジェット
        """
        key_map = {
            "Ctrl+O": "<Control-o>",
            "Ctrl+S": "<Control-s>",
            "Ctrl+Q": "<Control-q>",
            "Ctrl+F": "<Control-f>",
            "Ctrl+E": "<Control-e>",
            "F5": "<F5>",
            "Escape": "<Escape>",
        }
        for key, entry in self._shortcuts.items():
            tk_key = key_map.get(key)
            if tk_key and hasattr(widget, "bind"):
                widget.bind(tk_key, lambda _e, cb=entry.callback: cb())

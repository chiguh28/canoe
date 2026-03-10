"""設定管理 (アプリケーション設定の保存・読込)

ツール設定をJSON形式で永続化する。
"""

from __future__ import annotations

import json
from pathlib import Path


class SettingsManager:
    """アプリケーション設定マネージャ

    設定の取得・更新・保存・読込を管理する。
    """

    def __init__(self) -> None:
        self._settings: dict[str, str] = dict(self.get_defaults())

    @staticmethod
    def get_defaults() -> dict[str, str]:
        """デフォルト設定を取得"""
        return {
            "canoe_config_path": "",
            "log_directory": "logs",
            "report_output_directory": "",
            "azure_openai_endpoint": "",
            "azure_openai_deployment": "",
            "azure_openai_api_version": "2024-02-01",
        }

    def get(self, key: str, default: str = "") -> str:
        """設定値を取得"""
        return self._settings.get(key, default)

    def set(self, key: str, value: str) -> None:
        """設定値を更新"""
        self._settings[key] = value

    def get_all(self) -> dict[str, str]:
        """全設定を取得"""
        return dict(self._settings)

    def reset(self) -> None:
        """デフォルト設定にリセット"""
        self._settings = dict(self.get_defaults())

    def save(self, file_path: Path) -> None:
        """設定をJSONファイルに保存"""
        file_path.write_text(
            json.dumps(self._settings, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load(self, file_path: Path) -> None:
        """設定をJSONファイルから読込"""
        text = file_path.read_text(encoding="utf-8")
        data = json.loads(text)
        self._settings.update(data)

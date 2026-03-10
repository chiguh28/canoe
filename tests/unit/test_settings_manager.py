"""設定管理のテスト

アプリケーション設定の保存・読込のテスト。
"""

from __future__ import annotations

import json

import pytest

from src.config.settings_manager import SettingsManager


class TestSettingsManager:
    """設定マネージャのテスト"""

    def test_default_settings(self):
        mgr = SettingsManager()
        settings = mgr.get_all()
        assert "canoe_config_path" in settings
        assert "log_directory" in settings
        assert "report_output_directory" in settings

    def test_get_set(self):
        mgr = SettingsManager()
        mgr.set("canoe_config_path", "/path/to/config.cfg")
        assert mgr.get("canoe_config_path") == "/path/to/config.cfg"

    def test_get_default(self):
        mgr = SettingsManager()
        assert mgr.get("nonexistent", "default_val") == "default_val"

    def test_save_load(self, tmp_path):
        mgr = SettingsManager()
        mgr.set("canoe_config_path", "/test/config.cfg")
        mgr.set("log_directory", "/test/logs")

        settings_path = tmp_path / "settings.json"
        mgr.save(settings_path)
        assert settings_path.exists()

        loaded_mgr = SettingsManager()
        loaded_mgr.load(settings_path)
        assert loaded_mgr.get("canoe_config_path") == "/test/config.cfg"
        assert loaded_mgr.get("log_directory") == "/test/logs"

    def test_save_load_roundtrip(self, tmp_path):
        mgr = SettingsManager()
        mgr.set("azure_openai_endpoint", "https://example.openai.azure.com/")
        mgr.set("azure_openai_deployment", "gpt-4o")

        path = tmp_path / "settings.json"
        mgr.save(path)

        mgr2 = SettingsManager()
        mgr2.load(path)
        assert mgr2.get("azure_openai_endpoint") == "https://example.openai.azure.com/"

    def test_load_invalid_file(self, tmp_path):
        mgr = SettingsManager()
        path = tmp_path / "invalid.json"
        path.write_text("not json", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            mgr.load(path)

    def test_load_nonexistent_file(self, tmp_path):
        mgr = SettingsManager()
        with pytest.raises(FileNotFoundError):
            mgr.load(tmp_path / "nonexistent.json")

    def test_reset_to_defaults(self):
        mgr = SettingsManager()
        mgr.set("canoe_config_path", "/custom/path")
        mgr.reset()
        assert mgr.get("canoe_config_path") == ""

    def test_default_settings_keys(self):
        defaults = SettingsManager.get_defaults()
        assert "canoe_config_path" in defaults
        assert "log_directory" in defaults
        assert "report_output_directory" in defaults
        assert "azure_openai_endpoint" in defaults
        assert "azure_openai_deployment" in defaults

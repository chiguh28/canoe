"""エラーメッセージ定義 (Issue #24)

ユーザー向けの日本語エラーメッセージを一元管理する。
"""


class ErrorMessages:
    """日本語エラーメッセージ集"""

    @staticmethod
    def file_not_found(file_path: str) -> str:
        """ファイルが見つからない"""
        return f"ファイルが見つかりません: {file_path}\nパスを確認してください。"

    @staticmethod
    def unsupported_format(extension: str) -> str:
        """サポートされていないファイル形式"""
        return (
            f"サポートされていないファイル形式です: {extension}\n"
            "対応形式: .dbc (CAN), .ldf (LIN)"
        )

    @staticmethod
    def parse_error(file_path: str, detail: str) -> str:
        """ファイル解析エラー"""
        return f"ファイルの解析に失敗しました: {file_path}\n詳細: {detail}"

    @staticmethod
    def connection_error(detail: str) -> str:
        """CANoe 接続エラー"""
        return f"CANoe への接続に失敗しました。\n詳細: {detail}"

    @staticmethod
    def no_patterns() -> str:
        """テストパターンが未設定"""
        return "実行するテストパターンがありません。\nテストパターンを作成してください。"

    @staticmethod
    def execution_error(test_case_id: str, detail: str) -> str:
        """テスト実行エラー"""
        return f"テスト実行中にエラーが発生しました: {test_case_id}\n詳細: {detail}"

    @staticmethod
    def save_error(file_path: str, detail: str) -> str:
        """ファイル保存エラー"""
        return f"ファイルの保存に失敗しました: {file_path}\n詳細: {detail}"

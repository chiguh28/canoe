# canoe

CANoe 自動テストツール — 車載通信テストの自動化

## 概要

CANoe を用いた車載通信テストにおけるテストパターン作成・実行・判定・報告書作成を自動化するPythonツールです。
CANdb/LDFファイルから信号情報を取得し、日本語でテストパターンを作成、CANoe COM APIを通じてテストを自動実行・判定し、結果をExcel帳票として出力します。

## 主要機能

- **信号情報管理**: CANdb (.dbc) / LDF (.ldf) ファイルから信号情報を自動取得・一覧表示
- **テストパターン作成**: 日本語でテストパターンを作成、Azure OpenAI による自動変換対応
- **テスト自動実行**: CANoe COM API を通じてテストパターンを自動実行（進捗表示・中断対応）
- **テスト結果判定**: 5種類の判定ロジック（値一致・範囲・変化検知・タイムアウト・複合判定）
- **Excel帳票出力**: サマリ・統計・詳細シートを含む Excel レポートを自動生成

## 動作要件

- Python 3.10+
- CANoe (Vector 社製) ※ テスト実行時のみ必要
- Windows OS ※ CANoe COM API 使用時のみ必要

## インストール

```bash
git clone https://github.com/chiguh28/canoe.git
cd canoe
pip install -e ".[dev]"
```

Windows で CANoe COM API を使用する場合:

```bash
pip install -e ".[windows]"
```

## 使い方

```bash
python -m src
```

詳細は [取扱説明書](docs/user_manual.md) を参照してください。

## 開発

```bash
# テスト実行
pytest

# リンター
ruff check .

# 型チェック
mypy src/
```

詳細は [開発者ガイド](docs/developer_guide.md) を参照してください。

## ドキュメント

- [取扱説明書](docs/user_manual.md) - インストールから基本操作まで
- [開発者ガイド](docs/developer_guide.md) - アーキテクチャ、モジュール構成、テスト手順
- [要件定義書](docs/requirements.md) - 詳細な要件定義

## ライセンス

TBD

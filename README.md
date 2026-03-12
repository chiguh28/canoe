# CANoe 自動テストツール

車載通信テスト（CAN/LIN）のテストパターン作成・実行・判定・帳票出力を自動化する Python ツールです。

## 概要

CANoe を用いた車載通信テストにおいて、以下の作業を自動化します。

- **信号情報取得**: CANdb（`.dbc`）/ LDF（`.ldf`）ファイルから信号情報を統一モデルに変換
- **テストパターン作成**: 日本語でテスト内容を記述し、Azure OpenAI（GPT-4o）で構造化パラメータに自動変換
- **テスト自動実行**: CANoe COM API を通じてテストパターンを自動実行し、ログを記録
- **結果判定・帳票**: 5 種類の判定タイプ（EXACT/RANGE/CHANGE/TIMEOUT/COMPOUND）で自動判定し、Excel 帳票を出力

## 機能一覧

| Phase | 機能 | 説明 |
|-------|------|------|
| Phase 1 | 信号情報取得 | DBC/LDF ファイルのパース、信号一覧表示、検索・ソート |
| Phase 2 | テストパターン作成 | 日本語テスト記述、AI 一括変換、プレビュー・手動修正・確定 |
| Phase 3 | テスト自動実行 | CANoe 接続、順次テスト実行、進捗表示、中断対応 |
| Phase 4 | 結果判定・帳票 | 5 種類の自動判定、Excel 帳票（3 シート構成）出力 |

## 動作環境

| 項目 | 要件 |
|------|------|
| OS | Windows 10 / 11 |
| Python | 3.10 以上 |
| CANoe | バージョン 10.0 以降（COM API 対応） |
| Azure OpenAI | GPT-4o デプロイメント（Phase 2 で使用） |

## クイックスタート

### 1. インストール

```bash
git clone https://github.com/chiguh28/canoe.git
cd canoe
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

### 2. 起動

```bash
python -m src
```

### 3. DBC/LDF ファイルを読み込む

1. 「信号情報」タブの「ファイルを開く」ボタンをクリック
2. DBC または LDF ファイルを選択
3. 信号情報が一覧に表示される

### 4. テストパターンを作成・実行

1. 「テストパターン作成」タブでテスト内容を日本語で記述
2. 「一括変換」で AI がパラメータに変換
3. 「テスト実行」タブで CANoe 構成ファイルを指定して実行
4. 「結果・帳票」タブで結果を確認し、Excel 帳票を出力

## プロジェクト構成

```
canoe/
├── src/                     # アプリケーション本体
│   ├── models/              #   データモデル (SignalInfo, TestPattern)
│   ├── parsers/             #   ファイルパーサー (DBC, LDF)
│   ├── converter/           #   AI 変換 (Azure OpenAI)
│   ├── engine/              #   テスト実行エンジン (CANoe COM, 判定)
│   ├── report/              #   帳票生成 (Excel)
│   └── gui/                 #   GUI (tkinter)
├── tests/                   # テストコード
│   ├── unit/                #   ユニットテスト
│   ├── integration/         #   結合テスト
│   └── fixtures/            #   テスト用サンプルファイル
├── docs/                    # ドキュメント
│   ├── user_guide.md        #   取扱説明書
│   ├── developer_guide.md   #   開発者ガイド
│   ├── requirements.md      #   要件定義書
│   └── DESIGN.md            #   設計ドキュメント
└── pyproject.toml           # プロジェクト設定
```

## ドキュメント

| ドキュメント | 対象読者 | 内容 |
|-------------|---------|------|
| [取扱説明書](docs/user_guide.md) | エンドユーザー | インストール、操作手順、トラブルシューティング |
| [開発者ガイド](docs/developer_guide.md) | 開発者 | アーキテクチャ、モジュール詳細、拡張方法 |
| [要件定義書](docs/requirements.md) | 開発者 | 機能要件・非機能要件 |
| [設計ドキュメント](docs/DESIGN.md) | 開発者 | 詳細設計 |

## 開発

### 環境セットアップ

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

### テスト実行

```bash
# 全テスト（カバレッジ付き）
pytest

# 特定テスト
pytest tests/unit/test_signal_model.py -v
```

### コード品質チェック

```bash
# フォーマット
ruff format .

# リント
ruff check .

# 型チェック
mypy src/
```

### CI

GitHub Actions で以下を自動実行:
- `ruff check` — リント
- `mypy src/` — 型チェック
- `pytest` — テスト（Python 3.10 / 3.11 / 3.12）

## ライセンス

MIT License

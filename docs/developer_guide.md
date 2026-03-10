# 開発者ガイド

## アーキテクチャ概要

本ツールは以下のレイヤー構成で設計されています:

```
┌─────────────────────────────────┐
│         GUI Layer (tkinter)     │
│  MainWindow / SignalTab /       │
│  ExecutionTab / SignalSelector  │
├─────────────────────────────────┤
│       Converter Layer           │
│  OpenAIConverter /              │
│  BatchConverter                 │
├─────────────────────────────────┤
│        Engine Layer             │
│  TestRunner / CANoeCOMWrapper / │
│  LogManager / JudgmentEngine    │
├─────────────────────────────────┤
│        Model Layer              │
│  SignalInfo / TestPattern /     │
│  SignalRepository               │
├─────────────────────────────────┤
│       Parser Layer              │
│  DBCParser / LDFParser          │
├─────────────────────────────────┤
│       Report Layer              │
│  ExcelReportGenerator           │
└─────────────────────────────────┘
```

## モジュール構成

```
src/
├── __init__.py          # パッケージ初期化
├── __main__.py          # エントリーポイント
├── main.py              # アプリケーション起動
├── models/
│   ├── signal_model.py  # 信号データモデル (SignalInfo, SignalRepository)
│   └── test_pattern.py  # テストパターンモデル (TestPattern, TestPatternRepository)
├── parsers/
│   ├── dbc_parser.py    # DBC (CAN) パーサー
│   └── ldf_parser.py    # LDF (LIN) パーサー
├── gui/
│   ├── main_window.py       # メインウィンドウ
│   ├── signal_tab.py        # 信号情報タブ
│   ├── signal_selector.py   # 信号選択UI
│   ├── execution_tab.py     # テスト実行タブ
│   ├── error_messages.py    # エラーメッセージ定義
│   └── keyboard_shortcuts.py # キーボードショートカット管理
├── engine/
│   ├── canoe_com.py     # CANoe COM API ラッパー
│   ├── test_runner.py   # テスト実行エンジン
│   ├── log_manager.py   # ログ管理
│   └── judgment.py      # 判定エンジン
├── converter/
│   ├── openai_converter.py  # Azure OpenAI 変換
│   └── batch_converter.py   # バッチ変換
└── report/
    └── excel_report.py  # Excel 帳票生成
```

## データフロー

```
DBC/LDF Files
     ↓  (DBCParser / LDFParser)
SignalInfo[]
     ↓  (SignalRepository.add_signals)
SignalRepository (in-memory)
     ↓  (GUI: SignalTab, SignalSelector)
TestPattern[]
     ↓  (OpenAIConverter → BatchConverter)
TestPatternRepository
     ↓  (TestRunner.execute)
TestResult[] + ExecutionSummary
     ↓  (LogManager → JudgmentEngine)
JudgmentDetail[]
     ↓  (ExcelReportGenerator.generate)
Excel Report (.xlsx)
```

## ビルドとテスト

### 依存関係のインストール

```bash
pip install -e ".[dev]"
```

### テスト実行

```bash
# 全テスト
pytest

# カバレッジ付き
pytest --cov=src --cov-report=term-missing

# 特定テスト
pytest tests/unit/test_signal_model.py -v

# 統合テスト
pytest tests/integration/ -v
```

### 静的解析

```bash
# Ruff (リンター)
ruff check .

# 自動修正
ruff check . --fix

# mypy (型チェック)
mypy src/
```

### CI パイプライン

GitHub Actions で以下を自動実行:

- Python 3.10/3.11/3.12 マトリクスビルド
- pytest + カバレッジ
- ruff lint
- mypy strict mode

## 設計パターン

### 依存性注入 (DI)

`TestRunner` は `CANoeCOMWrapper` をコンストラクタで受け取ります。テスト時にはモックを注入できます:

```python
from unittest.mock import MagicMock
runner = TestRunner(com_wrapper=MagicMock())
```

### リポジトリパターン

`SignalRepository` と `TestPatternRepository` はインメモリデータストアとして機能し、検索・フィルタ・永続化を提供します。

### コールバックパターン

`TestRunner` と `BatchConverter` は進捗通知のためのコールバック関数を受け取ります:

```python
runner.set_progress_callback(lambda current, total, name: print(f"{current}/{total}: {name}"))
```

### Frozen Dataclass

`SignalInfo` は `frozen=True` で不変性を保証しています。パース後のデータ変更を防ぎます。

## テスト戦略

### テスト構成

```
tests/
├── unit/           # ユニットテスト（各モジュール単体）
├── integration/    # 統合テスト（複数モジュール連携）
├── fixtures/       # テスト用サンプルファイル
└── conftest.py     # pytest 共通設定（tkinter モック等）
```

### ヘッドレス環境対応

`tests/conftest.py` で tkinter をモック化しており、GUI なしの環境（CI等）でもテストが実行可能です。

### テストカバレッジ目標

- ユニットテスト: 90% 以上
- 統合テスト: 主要ワークフローの網羅

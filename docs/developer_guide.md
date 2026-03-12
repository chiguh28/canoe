# CANoe 自動テストツール 開発者ガイド

**バージョン:** 0.1.0
**最終更新日:** 2026-03-12

---

## 目次

1. [アーキテクチャ概要](#1-アーキテクチャ概要)
2. [モジュール間連携](#2-モジュール間連携)
3. [各モジュール詳細](#3-各モジュール詳細)
4. [テスト](#4-テスト)
5. [開発環境セットアップ](#5-開発環境セットアップ)
6. [コーディング規約](#6-コーディング規約)
7. [CI/CD](#7-cicd)
8. [拡張ガイド](#8-拡張ガイド)

---

## 1. アーキテクチャ概要

### 1.1 全体構成図

```
┌──────────────────────────────────────────────────────────────┐
│                          GUI Layer                           │
│  ┌────────────┐ ┌──────────────┐ ┌──────────────┐ ┌───────┐│
│  │ SignalTab   │ │ PatternTab   │ │ ExecutionTab │ │Result ││
│  │ (Phase 1)  │ │ (Phase 2)    │ │ (Phase 3)    │ │Tab    ││
│  │            │ │              │ │              │ │(Ph 4) ││
│  └─────┬──────┘ └──────┬───────┘ └──────┬───────┘ └──┬────┘│
│        │               │               │             │      │
├────────┼───────────────┼───────────────┼─────────────┼──────┤
│        ▼               ▼               ▼             ▼      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                    Model Layer                        │   │
│  │  SignalInfo / MessageInfo / SignalRepository           │   │
│  │  TestPattern / TestPatternRepository                  │   │
│  └────┬──────────────────────┬───────────────────────────┘   │
│       │                      │                                │
│       ▼                      ▼                                │
│  ┌─────────────┐   ┌──────────────────────┐                  │
│  │ Parsers      │   │  Converter Layer     │                  │
│  │ DBCParser    │   │  OpenAIConverter     │                  │
│  │ LDFParser    │   │  BatchConverter      │                  │
│  └─────────────┘   └──────────┬───────────┘                  │
│                               │                               │
│                               ▼                               │
│  ┌──────────────────────────────────────────────────────────┐│
│  │                     Engine Layer                          ││
│  │ CANoeCOMWrapper → TestRunner → LogManager → JudgmentEngine││
│  └────────────────────────────────────┬─────────────────────┘│
│                                       │                       │
│                                       ▼                       │
│  ┌──────────────────────────────────────────────────────────┐│
│  │                     Report Layer                          ││
│  │                 ExcelReportGenerator                      ││
│  └──────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

### 1.2 レイヤー構造

| レイヤー | ディレクトリ | 責務 |
|---------|-------------|------|
| **GUI** | `src/gui/` | ユーザーインターフェース（tkinter） |
| **Model** | `src/models/` | データモデルとリポジトリ |
| **Parsers** | `src/parsers/` | ファイルパーサー（DBC/LDF → SignalInfo） |
| **Converter** | `src/converter/` | AI 変換（日本語 → 構造化パラメータ） |
| **Engine** | `src/engine/` | テスト実行エンジン（CANoe COM 操作、ログ、判定） |
| **Report** | `src/report/` | 帳票生成（Excel） |

各レイヤーは上位から下位への一方向の依存を持ちます。下位レイヤーは上位レイヤーに依存しません。

### 1.3 データフロー図

```
Phase 1: 信号読み込み
  .dbc/.ldf ファイル
      ↓ DBCParser / LDFParser
  list[SignalInfo]
      ↓ SignalRepository.add_signals()
  SignalRepository（メモリ内保持）

Phase 2: テストパターン作成
  ユーザー入力（日本語）
      ↓ TestPattern.from_dict()
  TestPattern
      ↓ OpenAIConverter.convert()
  ConversionResult
      ↓ BatchConverter.convert_all() → preview → confirm
  list[PreviewItem]
      ↓ export_confirmed()
  confirmed_params.json

Phase 3: テスト実行
  list[TestPattern] + CANoe 構成ファイル
      ↓ TestRunner.execute()
  CANoeCOMWrapper（信号送受信）
      ↓ LogManager（ログ記録）
  ExecutionSummary + list[TestResult]

Phase 4: 判定・帳票
  TestLog + JudgmentCriteria
      ↓ JudgmentEngine.judge()
  list[JudgmentDetail]
      ↓ ExcelReportGenerator.generate()
  test_report_YYYYMMDD_HHMMSS.xlsx
```

---

## 2. モジュール間連携

### 2.1 主要なデータの流れ

```
Signal ──→ TestPattern ──→ Converter ──→ Runner ──→ Judgment ──→ Report

SignalInfo    TestPattern    ConversionResult  TestResult    JudgmentDetail  Excel
(from DBC/   (user input)   (AI converted     (execution    (OK/NG/ERROR    (.xlsx)
 LDF file)                   parameters)       result)       with reason)
```

### 2.2 インターフェース一覧（公開 API）

| クラス | 主要メソッド | 入力 | 出力 |
|-------|-------------|------|------|
| `DBCParser` | `parse(path)` | `Path` | `list[SignalInfo]` |
| `LDFParser` | `parse(path)` | `Path` | `list[SignalInfo]` |
| `SignalRepository` | `add_signals()`, `search()`, `filter_by_protocol()` | `list[SignalInfo]`, `str`, `Protocol` | `None`, `list[SignalInfo]` |
| `TestPatternRepository` | `add()`, `save_to_json()`, `load_from_json()` | `TestPattern`, `Path` | `TestPattern`, `None` |
| `OpenAIConverter` | `convert()`, `convert_batch()` | テキスト | `ConversionResult` |
| `BatchConverter` | `convert_all()`, `export_confirmed()` | `list[TestPattern]`, `Path` | `list[PreviewItem]`, `Path` |
| `CANoeCOMWrapper` | `connect()`, `set_signal_value()`, `get_signal_value()` | 信号情報 | `None`, `float` |
| `TestRunner` | `execute()` | `list[TestPattern]` | `ExecutionSummary` |
| `JudgmentEngine` | `judge()` | `TestLog`, `JudgmentCriteria` | `JudgmentDetail` |
| `ExcelReportGenerator` | `generate()` | `ExecutionSummary`, `list[JudgmentDetail]` | `Path` |

### 2.3 依存関係図

```
src/gui/main_window.py
  ├── src/gui/signal_tab.py
  │     ├── src/parsers/dbc_parser.py    → cantools (外部)
  │     ├── src/parsers/ldf_parser.py    → ldfparser (外部)
  │     └── src/models/signal_model.py
  ├── src/gui/signal_selector.py
  │     └── src/models/signal_model.py
  ├── src/gui/execution_tab.py
  │     ├── src/engine/test_runner.py
  │     │     ├── src/engine/canoe_com.py → pywin32 (外部/Windows)
  │     │     └── src/engine/log_manager.py
  │     └── src/models/test_pattern.py
  └── src/converter/batch_converter.py
        └── src/converter/openai_converter.py → httpx / Azure OpenAI (外部)

src/engine/judgment.py
  └── src/engine/log_manager.py

src/report/excel_report.py  → openpyxl (外部)
  ├── src/engine/test_runner.py (ExecutionSummary)
  └── src/engine/judgment.py (JudgmentDetail)
```

---

## 3. 各モジュール詳細

### 3.1 models/ — データモデル

#### signal_model.py

| クラス | 種類 | 説明 |
|-------|------|------|
| `Protocol` | Enum | 通信プロトコル（CAN / LIN） |
| `SignalInfo` | frozen dataclass | 統一信号情報モデル |
| `MessageInfo` | frozen dataclass | メッセージ情報（信号のグループ） |
| `SignalRepository` | class | 信号のメモリ内リポジトリ |

**SignalInfo の主要フィールド:**

```python
@dataclass(frozen=True)
class SignalInfo:
    signal_name: str        # 信号名
    message_name: str       # メッセージ名
    message_id: int         # メッセージID
    data_type: str          # データ型 (unsigned/signed/float)
    min_value: float        # 最小物理値
    max_value: float        # 最大物理値
    unit: str               # 物理単位
    node_info: str          # ノード情報 ("送信元 -> 受信先")
    source_file: str        # ソースファイルパス
    protocol: Protocol      # CAN or LIN
```

**SignalRepository の主要メソッド:**

```python
class SignalRepository:
    def add_signals(self, signals: list[SignalInfo]) -> None: ...
    def clear(self) -> None: ...
    def get_all(self) -> list[SignalInfo]: ...
    def search(self, query: str) -> list[SignalInfo]: ...
    def filter_by_protocol(self, protocol: Protocol) -> list[SignalInfo]: ...
    def get_by_message(self, message_name: str) -> list[SignalInfo]: ...
    @property
    def count(self) -> int: ...
```

#### test_pattern.py

| クラス | 種類 | 説明 |
|-------|------|------|
| `TestPattern` | dataclass | テストケースモデル |
| `TestPatternRepository` | class | テストパターンのリポジトリ（JSON 永続化対応） |

**TestPattern のフィールド:**

```python
@dataclass
class TestPattern:
    test_case_id: str       # "TC-001" 形式（自動採番）
    test_case_name: str     # テストケース名
    target_signal: str      # 対象信号名
    operation: str          # 操作内容（日本語）
    expected_value: str     # 期待値（日本語）
    precondition: str       # 前提条件
    wait_time_ms: int       # 待機時間 (ms)
    remarks: str            # 備考
```

### 3.2 parsers/ — ファイルパーサー

#### dbc_parser.py

DBC（CAN データベース）ファイルを `cantools` ライブラリでパースし、`list[SignalInfo]` に変換します。

```python
class DBCParser:
    def parse(self, dbc_path: Path) -> list[SignalInfo]:
        """DBC ファイルをパースして SignalInfo リストを返す。

        Raises:
            DBCParseError: ファイルが存在しない、空、または不正な形式
        """
```

**変換ルール:**
- `cantools.Signal.is_signed` → `"signed"` / `"unsigned"`
- `cantools.Signal.minimum` / `maximum` → `min_value` / `max_value`
- `cantools.Signal.unit` → `unit`
- ノード情報: `"送信ノード -> 受信ノード1, 受信ノード2"`

#### ldf_parser.py

LDF（LIN データベース）ファイルを `ldfparser` ライブラリでパースします。

```python
class LDFParser:
    def parse(self, ldf_path: Path | str) -> list[SignalInfo]:
        """LDF ファイルをパースして SignalInfo リストを返す。

        Raises:
            LDFParseError: ファイルが存在しない、空、または不正な形式
        """
```

**変換ルール:**
- データ型: デフォルト `"unsigned"`
- 物理値: `converter.phy_min` / `phy_max` / `unit`（エンコーディングから取得）
- ノード情報: `"パブリッシャー -> サブスクライバー1, サブスクライバー2"`

### 3.3 converter/ — AI 変換エンジン

#### openai_converter.py

Azure OpenAI（GPT-4o）を使用して、日本語のテスト記述を構造化パラメータに変換します。

```python
class OpenAIConverter:
    def configure_from_env(self) -> None:
        """環境変数から設定を読み込む。
        必須: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT
        """

    def convert(
        self,
        test_case_id: str,
        operation_text: str,
        expected_text: str,
        signal_list: list[str] | None = None,
    ) -> ConversionResult:
        """日本語テスト記述を構造化パラメータに変換。
        リトライ: 最大3回、指数バックオフ（ベース2秒）
        キャッシュ: (operation_text, expected_text) をキーにキャッシュ
        """
```

**ConversionResult:**

```python
@dataclass
class ConversionResult:
    test_case_id: str
    original_text: str       # 元の日本語テキスト
    converted_params: dict   # 変換後の構造化パラメータ
    success: bool            # 変換成功フラグ
    error_message: str       # エラー時のメッセージ
    confidence: float        # 信頼度 (0.0〜1.0)
```

#### batch_converter.py

複数テストパターンの一括変換を管理し、プレビュー・手動修正・確定のワークフローを提供します。

```python
class BatchConverter:
    def convert_all(
        self,
        patterns: list[TestPattern],
        signal_list: list[str] | None = None,
    ) -> list[PreviewItem]:
        """全パターンを一括変換。プログレスコールバック対応。"""

    def update_preview_item(
        self, test_case_id: str, new_params: dict
    ) -> PreviewItem:
        """プレビュー項目を手動修正。manually_edited=True にセット。"""

    def confirm_all(self) -> list[PreviewItem]:
        """成功した全項目を確定。"""

    def export_confirmed(self, output_path: Path) -> Path:
        """確定済みパラメータを JSON にエクスポート。"""
```

### 3.4 engine/ — テスト実行エンジン

#### canoe_com.py

CANoe COM API のラッパー。状態管理（DISCONNECTED → CONNECTED → MEASURING）を行います。

```python
class CANoeCOMWrapper:
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def load_config(self, config_path: str) -> None: ...
    def start_measurement(self) -> None: ...
    def stop_measurement(self) -> None: ...
    def set_signal_value(self, channel: int, message: str, signal: str, value: float) -> None: ...
    def get_signal_value(self, channel: int, message: str, signal: str) -> float: ...

    @property
    def state(self) -> CANoeState: ...
```

**状態遷移:**

```
DISCONNECTED ──connect()──→ CONNECTED ──start_measurement()──→ MEASURING
                  ↑                                               │
                  └──────────stop_measurement()───────────────────┘
```

#### test_runner.py

テストパターンを順次実行し、結果を集約します。

```python
class TestRunner:
    def execute(
        self, patterns: list[TestPattern], config_file: str = ""
    ) -> ExecutionSummary:
        """全パターンを順次実行。中断対応。別スレッドで実行推奨。"""

    def abort(self) -> None:
        """実行中断を要求。残りパターンは SKIPPED。"""

    def set_progress_callback(
        self, callback: Callable[[int, int, str], None]
    ) -> None:
        """進捗コールバック設定。(current, total, test_name)"""
```

**TestStatus:**

```
PENDING → RUNNING → PASSED / FAILED / ERROR / SKIPPED / ABORTED
```

#### log_manager.py

テスト実行ログの記録・保存・読み込みを管理します。

```python
class LogManager:
    def start_log(self, test_case_id: str) -> TestLog: ...
    def add_entry(self, test_case_id: str, entry: LogEntry) -> None: ...
    def end_log(self, test_case_id: str) -> TestLog: ...
    def save_log_csv(self, test_case_id: str) -> Path: ...
    def save_log_json(self, test_case_id: str) -> Path: ...
```

**LogEntry:**

```python
@dataclass
class LogEntry:
    timestamp: float     # 開始からの経過秒数
    channel: int         # CAN/LIN チャネル
    message_name: str    # メッセージ名
    signal_name: str     # 信号名
    value: float         # 信号値
    direction: str       # "Tx" or "Rx"
```

#### judgment.py

テスト結果の判定エンジン。5 種類の判定タイプをサポートします。

```python
class JudgmentEngine:
    def judge(
        self, test_case_id: str, log: TestLog, criteria: JudgmentCriteria
    ) -> JudgmentDetail:
        """テストログと判定基準に基づいて OK/NG/ERROR を判定。"""
```

**判定タイプ:**

| タイプ | 判定ロジック |
|-------|-------------|
| `EXACT` | `abs(actual - expected) <= tolerance` |
| `RANGE` | `range_min <= actual <= range_max` |
| `CHANGE` | 信号値の変化方向（INCREASE/DECREASE/NO_CHANGE） |
| `TIMEOUT` | `elapsed_ms <= timeout_ms` |
| `COMPOUND` | 複数条件の AND / OR 論理演算 |

### 3.5 report/ — 帳票生成

#### excel_report.py

テスト結果を 3 シートの Excel ファイルとして出力します。

```python
class ExcelReportGenerator:
    def generate(
        self,
        summary: ExecutionSummary,
        judgments: list[JudgmentDetail] | None = None,
        output_path: Path | None = None,
        config_file: str = "",
    ) -> Path:
        """Excel 帳票を生成。
        シート構成: サマリ / 統計 / 各テストケース詳細
        """
```

**Excel のスタイル:**
- ヘッダー: 濃紺背景、白文字、太字
- OK: 緑 (#C6EFCE)
- NG: 赤 (#FFC7CE)
- ERROR: 黄 (#FFEB9C)

### 3.6 gui/ — ユーザーインターフェース

| ファイル | クラス | 責務 |
|---------|-------|------|
| `main_window.py` | `MainWindow` | メインウィンドウ（タブ管理、メニュー、ステータスバー） |
| `signal_tab.py` | `SignalTab` | 信号情報タブ（ファイル読み込み、一覧表示、検索・ソート） |
| `signal_selector.py` | `SignalSelector` | 信号選択コンポーネント（検索・選択・詳細表示） |
| `execution_tab.py` | `ExecutionTab` | テスト実行タブ（進捗表示、中断、ログ） |

**MainWindow のタブ構成:**

```python
class MainWindow:
    def __init__(self) -> None:
        self.signal_repository = SignalRepository()  # タブ間共有
        # タブ: 信号情報, テストパターン作成, テスト実行, 結果・帳票
```

---

## 4. テスト

### 4.1 テスト構成

```
tests/
├── conftest.py                        # 共通設定（tkinter モック等）
├── fixtures/                          # テスト用サンプルファイル
│   ├── sample.dbc                     # CAN サンプル
│   └── sample.ldf                     # LIN サンプル
├── unit/                              # ユニットテスト
│   ├── test_signal_model.py           # SignalInfo, SignalRepository
│   └── test_ldf_parser.py            # LDFParser
├── integration/                       # 結合テスト
│   ├── test_parsers_integration.py    # DBC+LDF パーサー連携
│   └── test_e2e_basic.py             # 基本 E2E テスト
├── test_dbc_parser.py                 # DBCParser
└── test_gui.py                        # MainWindow
```

### 4.2 モック戦略

| モック対象 | モック方法 | 理由 |
|-----------|----------|------|
| tkinter | `conftest.py` でモジュールモック | Linux CI 環境で X11 不要 |
| CANoe COM API | `CANoeCOMWrapper` への DI | Windows + CANoe 必須のため |
| Azure OpenAI | `OpenAIConverter` への DI / Mock | API キー不要、コスト回避 |

### 4.3 テスト実行方法

```bash
# 全テスト実行（カバレッジ付き）
pytest

# 特定テストのみ
pytest tests/unit/test_signal_model.py -v

# カバレッジレポート表示
pytest --cov=src --cov-report=term-missing

# HTML カバレッジレポート生成
pytest --cov=src --cov-report=html
# → htmlcov/index.html をブラウザで開く
```

### 4.4 カバレッジの確認

カバレッジ目標は **85% 以上** です。

```bash
# ターミナルでカバレッジ確認
pytest --cov=src --cov-report=term-missing

# 出力例:
# Name                                Stmts   Miss  Cover   Missing
# -----------------------------------------------------------------
# src/models/signal_model.py             85      3    96%   120-122
# src/parsers/dbc_parser.py              45      0   100%
# ...
# -----------------------------------------------------------------
# TOTAL                                 500     50    90%
```

---

## 5. 開発環境セットアップ

### 5.1 リポジトリのクローン

```bash
git clone https://github.com/chiguh28/canoe.git
cd canoe
```

### 5.2 仮想環境の構築

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

### 5.3 依存ライブラリのインストール

```bash
# 開発用依存を含めてインストール
pip install -e ".[dev]"

# Windows で CANoe 連携を使う場合
pip install -e ".[dev,windows]"
```

### 5.4 IDE の設定

#### VSCode

推奨する `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": ".venv/Scripts/python",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"],
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": "explicit",
      "source.organizeImports": "explicit"
    }
  }
}
```

推奨拡張機能:
- `charliermarsh.ruff` — Ruff リンター/フォーマッター
- `ms-python.python` — Python 拡張
- `ms-python.mypy-type-checker` — mypy 型チェック

#### PyCharm

1. **File → Settings → Project → Python Interpreter** で `.venv` を選択
2. **File → Settings → Tools → Python Integrated Tools**:
   - Testing: pytest
   - Default test runner: pytest
3. **Languages & Frameworks → Python → Type Hinting** を有効化

---

## 6. コーディング規約

### 6.1 PEP 8 + ruff

ruff によるリント・フォーマットを使用します。設定は `pyproject.toml` で管理しています。

```bash
# フォーマット
ruff format .

# リントチェック
ruff check .

# 自動修正
ruff check --fix .
```

**主要な ruff ルール:**

| ルール | 説明 |
|-------|------|
| E / W | pycodestyle エラー/警告 |
| F | pyflakes |
| I | isort（import ソート） |
| N | PEP 8 命名規則 |
| UP | pyupgrade（Python バージョン対応） |
| B | flake8-bugbear（バグの温床検出） |
| C4 | flake8-comprehensions（内包表記の改善） |
| PT | flake8-pytest-style（pytest ルール） |

**行の最大文字数:** 100 文字

### 6.2 型ヒント（mypy strict）

全ての関数シグネチャに型ヒントを記述します。mypy の strict モード設定を使用しています。

```bash
mypy src/
```

**設定（pyproject.toml）:**

```toml
[tool.mypy]
python_version = "3.10"
warn_return_any = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true
strict_equality = true
```

**型ヒントの例:**

```python
def parse(self, dbc_path: Path) -> list[SignalInfo]:
    ...

signals: list[SignalInfo] = []
callback: Callable[[int, int, str], None] | None = None
```

### 6.3 docstring（Google Style）

パブリックメソッドには Google Style の docstring を記述します。

```python
def search(self, query: str) -> list[SignalInfo]:
    """Search signals by keyword.

    Args:
        query: Search keyword (case-insensitive).

    Returns:
        List of matching SignalInfo objects.

    Raises:
        ValueError: If query is empty.
    """
```

### 6.4 命名規則

| 対象 | 規則 | 例 |
|------|------|-----|
| 関数・変数 | snake_case | `parse_dbc_file`, `signal_list` |
| クラス | PascalCase | `SignalInfo`, `DBCParser` |
| 定数 | UPPER_CASE | `DEFAULT_TIMEOUT`, `MAX_SIGNALS` |
| プライベートメソッド | `_snake_case` | `_convert_signal`, `_validate_file` |
| テスト関数 | `test_` + snake_case | `test_parse_valid_dbc` |
| テストクラス | `Test` + PascalCase | `TestDBCParser` |

---

## 7. CI/CD

### 7.1 GitHub Actions 設定

CI は `.github/workflows/ci.yml` で定義されています。`main` ブランチへの push と PR で自動実行されます。

### 7.2 CI ジョブ構成

| ジョブ | 内容 | Python |
|-------|------|--------|
| **lint** | `ruff check .` | 3.10 |
| **typecheck** | `mypy src/` | 3.10 |
| **test** | `pytest` + カバレッジ | 3.10 / 3.11 / 3.12 |

### 7.3 テストマトリックス

```yaml
strategy:
  matrix:
    python-version: ["3.10", "3.11", "3.12"]
```

3 つの Python バージョンで並列テストを実行します。

### 7.4 カバレッジレポート

- Python 3.10 のテスト結果からカバレッジレポートを生成
- HTML レポートをアーティファクトとしてアップロード
- PR にカバレッジサマリを表示

---

## 8. 拡張ガイド

### 8.1 新しいパーサーの追加方法

例: ARXML（AUTOSAR）パーサーの追加

1. `src/parsers/arxml_parser.py` を作成:

```python
from pathlib import Path
from src.models.signal_model import SignalInfo, Protocol


class ARXMLParseError(Exception):
    """ARXML パースエラー"""


class ARXMLParser:
    """ARXML ファイルパーサー"""

    def parse(self, arxml_path: Path) -> list[SignalInfo]:
        """ARXML ファイルをパースして SignalInfo リストを返す。

        Args:
            arxml_path: ARXML ファイルのパス。

        Returns:
            パースされた SignalInfo のリスト。

        Raises:
            ARXMLParseError: パースに失敗した場合。
        """
        # 実装
        ...
```

2. `src/gui/signal_tab.py` のファイルダイアログに `.arxml` 拡張子を追加
3. `signal_tab.py` の `load_file()` に ARXML の分岐を追加
4. テストを作成: `tests/unit/test_arxml_parser.py`

### 8.2 新しい判定タイプの追加方法

例: PATTERN 判定（信号値のパターンマッチ）の追加

1. `src/engine/judgment.py` の `JudgmentType` に追加:

```python
class JudgmentType(Enum):
    EXACT = "exact"
    RANGE = "range"
    CHANGE = "change"
    TIMEOUT = "timeout"
    COMPOUND = "compound"
    PATTERN = "pattern"  # 追加
```

2. `JudgmentCriteria` にパターン用フィールドを追加:

```python
@dataclass
class JudgmentCriteria:
    ...
    expected_pattern: list[float] | None = None  # 追加
    pattern_tolerance: float = 0.0               # 追加
```

3. `JudgmentEngine` に判定メソッドを追加:

```python
def _judge_pattern(
    self, test_case_id: str, entries: list[LogEntry], criteria: JudgmentCriteria
) -> JudgmentDetail:
    """パターンマッチ判定"""
    ...
```

4. `judge()` のディスパッチに `PATTERN` を追加
5. テストを作成

### 8.3 LLM プロバイダーの差し替え方法

Azure OpenAI 以外の LLM を使用する場合:

1. `src/converter/openai_converter.py` と同じインターフェースを持つクラスを作成:

```python
class CustomLLMConverter:
    """カスタム LLM コンバーター"""

    def configure(self, **kwargs: str) -> None:
        """設定を適用"""
        ...

    def convert(
        self,
        test_case_id: str,
        operation_text: str,
        expected_text: str,
        signal_list: list[str] | None = None,
    ) -> ConversionResult:
        """変換を実行"""
        ...
```

2. `BatchConverter` のコンストラクタにカスタムコンバーターを注入:

```python
converter = CustomLLMConverter()
converter.configure(api_key="...")
batch = BatchConverter(converter=converter)
```

`BatchConverter` は DI（依存性注入）パターンを採用しているため、`convert()` メソッドを持つ任意のオブジェクトを注入できます。

---

*本書は CANoe 自動テストツール v0.1.0 の開発者ガイドです。*

# Phase 2: テストパターン作成機能 — 設計書

**Version:** 1.0　|　**作成日:** 2026-03-10　|　**対応Issue:** #2, #12〜#15

---

## 1. ディレクトリ構成

Phase 1 で構築した基盤に、以下のモジュールを追加する。

```
canoe/                              # リポジトリルート
├── src/
│   ├── models/
│   │   ├── signal_model.py         # (Phase 1) 信号情報データモデル — 変更なし
│   │   └── test_pattern.py         # ★ テストパターンデータモデル (Issue #13)
│   │
│   ├── parsers/                    # (Phase 1) パーサー群 — 変更なし
│   │   ├── dbc_parser.py
│   │   └── ldf_parser.py
│   │
│   ├── converter/                  # ★ 変換エンジン (Issue #14, #15)
│   │   ├── __init__.py
│   │   ├── openai_converter.py     # Azure OpenAI 変換ロジック
│   │   └── batch_converter.py      # 一括変換・プレビュー・確定
│   │
│   └── gui/
│       ├── main_window.py          # (Phase 1) メインウィンドウ — Phase 2 タブ統合
│       ├── signal_tab.py           # (Phase 1/Issue #11) 信号情報タブ
│       └── signal_selector.py      # ★ 信号選択UIコンポーネント (Issue #12)
│
├── tests/
│   ├── unit/
│   │   ├── test_test_pattern.py    # ★ テストパターンモデルのテスト
│   │   ├── test_openai_converter.py # ★ Azure OpenAI 変換のテスト
│   │   ├── test_batch_converter.py # ★ 一括変換・プレビューのテスト
│   │   └── test_signal_selector.py # ★ 信号選択UIのテスト
│   └── integration/
│       └── test_pattern_flow.py    # ★ パターン作成→変換→プレビュー統合テスト
│
└── pyproject.toml                  # Phase 2 依存追加
```

### pyproject.toml 更新事項

Phase 2 では Azure OpenAI API 呼び出しに HTTP クライアントを使用する。
`openai` 公式ライブラリの `AzureOpenAI` クライアント、または `urllib.request`（標準ライブラリ）を使用する。

```toml
[project.optional-dependencies]
phase2 = [
    "openai>=1.0.0",     # Azure OpenAI 公式クライアント（オプション）
]
```

> **設計判断:** 実装では `openai` ライブラリへの依存を避け、`urllib.request`（標準ライブラリ）をデフォルトの HTTP クライアントとして使用する。`httpx` が利用可能な場合は優先的に使用する。これにより CI 環境での依存を最小化し、テストでのモック化も容易にする。

---

## 2. モジュール構成図

```
┌──────────────────────────────────────────────────────────────────┐
│                         GUI Layer                                │
│                                                                  │
│  ┌────────────────────────┐   ┌────────────────────────────────┐ │
│  │ MainWindow             │   │ テストパターン作成タブ           │ │
│  │ (main_window.py)       │   │ ┌──────────────────────────┐   │ │
│  │ - Phase 2 タブ統合     │   │ │ SignalSelector           │   │ │
│  │                        │   │ │ (signal_selector.py)     │   │ │
│  │                        │   │ │ - コンボボックス選択     │   │ │
│  │                        │   │ │ - 絞り込み検索           │   │ │
│  │                        │   │ │ - 信号詳細表示           │   │ │
│  │                        │   │ └──────────────────────────┘   │ │
│  │                        │   │ ┌──────────────────────────┐   │ │
│  │                        │   │ │ TestPatternForm (将来)   │   │ │
│  │                        │   │ │ - テストパターン入力     │   │ │
│  │                        │   │ │ - 一括作成ボタン         │   │ │
│  │                        │   │ │ - プレビューペイン       │   │ │
│  │                        │   │ └──────────────────────────┘   │ │
│  └────────────────────────┘   └────────────────────────────────┘ │
│                                       │                          │
│            list[TestPattern]          │                          │
│            list[SignalInfo]           │                          │
│                                       ▼                          │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                       Model Layer                             │ │
│  │  ┌──────────────────────┐  ┌─────────────────────────────┐  │ │
│  │  │ SignalInfo            │  │ TestPattern                 │  │ │
│  │  │ SignalRepository      │  │ TestPatternRepository       │  │ │
│  │  │ (signal_model.py)     │  │ (test_pattern.py)           │  │ │
│  │  │ ← Phase 1 で実装済み │  │ - CRUD + 自動採番          │  │ │
│  │  │                      │  │ - JSON 保存/読込           │  │ │
│  │  └──────────────────────┘  └──────────────┬──────────────┘  │ │
│  └───────────────────────────────────────────┼──────────────────┘ │
│                                               │                    │
│                        list[TestPattern]      │                    │
│                                               ▼                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                     Converter Layer                           │ │
│  │  ┌────────────────────────┐  ┌───────────────────────────┐  │ │
│  │  │ OpenAIConverter        │  │ BatchConverter            │  │ │
│  │  │ (openai_converter.py)  │  │ (batch_converter.py)      │  │ │
│  │  │ - 環境変数ベース認証   │  │ - 全パターン一括変換     │  │ │
│  │  │ - リトライ(最大3回)    │  │ - プレビュー管理         │  │ │
│  │  │ - レスポンスキャッシュ │  │ - 手動修正・個別確定     │  │ │
│  │  │ - JSON構造化出力      │  │ - 確定済みエクスポート   │  │ │
│  │  └────────────────────────┘  └───────────────────────────┘  │ │
│  │              │                            │                   │ │
│  └──────────────┼────────────────────────────┼───────────────────┘ │
│                 │                            │                     │
│                 ▼                            ▼                     │
│         Azure OpenAI API            JSON ファイル出力              │
│         (HTTPS REST)                                               │
└──────────────────────────────────────────────────────────────────┘
```

### データフロー

```
ユーザー操作
    │
    ├─→ [信号選択] SignalSelector
    │       │  コンボボックスから信号を選択
    │       ▼
    │   SignalInfo (Phase 1 SignalRepository 経由)
    │
    ├─→ [パターン入力] TestPatternForm
    │       │  日本語で操作内容・期待値を入力
    │       ▼
    │   TestPattern (TestPatternRepository に保存)
    │
    └─→ [一括作成ボタン]
            │
            ▼
        BatchConverter.convert_all()
            │  全 TestPattern を順次 OpenAIConverter に渡す
            ▼
        OpenAIConverter.convert()
            │  Azure OpenAI API 呼び出し → JSON 構造化変換
            ▼
        list[PreviewItem]
            │  プレビューペインに表示
            ▼
        ユーザー確認・手動修正
            │
            ▼
        BatchConverter.confirm_all() / confirm_item()
            │
            ▼
        確定済みパラメータ (JSON 出力)
            │  → Phase 3 テスト実行エンジンへ引き渡し
```

---

## 3. クラス設計

### 3.1 TestPattern データクラス（src/models/test_pattern.py — Issue #13）

```python
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class TestPattern:
    """テストパターン

    要件定義書 3.1.2 に準拠。
    1件のテストパターンを構成するフィールドを管理する。
    """

    test_case_id: str = ""         # TC-001 形式（自動採番）
    test_case_name: str = ""       # テストケース名（日本語テキスト）
    target_signal: str = ""        # 対象信号名（SignalSelector から選択）
    operation: str = ""            # 操作内容（日本語テキスト）
    expected_value: str = ""       # 期待値（日本語テキスト）
    precondition: str = ""         # 前提条件（日本語テキスト）
    wait_time_ms: int = 0          # 待機時間(ms)
    remarks: str = ""              # 備考（任意）

    def to_dict(self) -> dict[str, object]:
        """辞書に変換"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> TestPattern:
        """辞書から生成"""
        return cls(
            test_case_id=str(data.get("test_case_id", "")),
            test_case_name=str(data.get("test_case_name", "")),
            target_signal=str(data.get("target_signal", "")),
            operation=str(data.get("operation", "")),
            expected_value=str(data.get("expected_value", "")),
            precondition=str(data.get("precondition", "")),
            wait_time_ms=int(str(data.get("wait_time_ms", 0))),
            remarks=str(data.get("remarks", "")),
        )
```

**設計判断:**

| 観点 | 決定 | 理由 |
|------|------|------|
| `frozen=True` を使わない | `@dataclass`（ミュータブル） | TestPatternRepository で ID を後から付与するため |
| 保存形式 | JSON | Phase 3 以降との連携で汎用的。YAML も候補だったが依存ライブラリ追加を避けた |
| ID 採番 | `TC-{N:03d}` 形式 | 要件定義書 3.1.2 のテストケースID仕様に準拠 |

**フィールドマッピング（要件定義書 → クラス）:**

| No. | 要件定義書フィールド | クラスフィールド | 入力方式 |
|-----|---------------------|-----------------|---------|
| 1 | テストケースID | `test_case_id` | 自動生成 |
| 2 | テストケース名 | `test_case_name` | 日本語テキスト入力 |
| 3 | 対象信号 | `target_signal` | SignalSelector で選択 |
| 4 | 操作内容 | `operation` | 日本語テキスト入力 |
| 5 | 期待値 | `expected_value` | 日本語テキスト入力 |
| 6 | 前提条件 | `precondition` | 日本語テキスト入力 |
| 7 | 待機時間（ms） | `wait_time_ms` | 数値入力 |
| 8 | 備考 | `remarks` | 日本語テキスト入力（任意） |

### 3.2 TestPatternRepository（src/models/test_pattern.py 内 — Issue #13）

```python
class TestPatternRepository:
    """テストパターンのリポジトリ

    テストパターンの管理（CRUD）と自動採番、
    JSON 形式での保存・読込機能を提供する。
    """

    def __init__(self) -> None:
        self._patterns: list[TestPattern] = []
        self._next_id: int = 1

    def add(self, pattern: TestPattern) -> TestPattern:
        """テストパターンを追加（IDを自動採番）

        Args:
            pattern: 追加するテストパターン（test_case_id は上書きされる）

        Returns:
            ID が付与されたテストパターン
        """
        pattern.test_case_id = f"TC-{self._next_id:03d}"
        self._next_id += 1
        self._patterns.append(pattern)
        return pattern

    def update(self, test_case_id: str, updated: TestPattern) -> TestPattern:
        """テストパターンを更新

        Raises:
            KeyError: 指定IDのパターンが存在しない場合
        """
        ...

    def delete(self, test_case_id: str) -> None:
        """テストパターンを削除

        Raises:
            KeyError: 指定IDのパターンが存在しない場合
        """
        ...

    def get(self, test_case_id: str) -> TestPattern:
        """テストパターンを取得

        Raises:
            KeyError: 指定IDのパターンが存在しない場合
        """
        ...

    def get_all(self) -> list[TestPattern]:
        """全テストパターンを取得"""
        return list(self._patterns)

    @property
    def count(self) -> int:
        """テストパターン数"""
        return len(self._patterns)

    def save_to_json(self, file_path: Path) -> None:
        """JSON ファイルに保存

        フォーマット: list[dict] の JSON 配列。
        ensure_ascii=False で日本語をそのまま保存。
        """
        data = [p.to_dict() for p in self._patterns]
        file_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_from_json(self, file_path: Path) -> None:
        """JSON ファイルから読み込み

        読み込み後、next_id を最大ID + 1 に復元する。
        これにより、保存 → 読込 → 追加 で ID が連番を維持する。
        """
        text = file_path.read_text(encoding="utf-8")
        data_list = json.loads(text)
        self._patterns.clear()
        max_id = 0
        for data in data_list:
            pattern = TestPattern.from_dict(data)
            self._patterns.append(pattern)
            if pattern.test_case_id.startswith("TC-"):
                try:
                    num = int(pattern.test_case_id[3:])
                    max_id = max(max_id, num)
                except ValueError:
                    pass
        self._next_id = max_id + 1
```

**CRUD API 一覧:**

| メソッド | 操作 | 引数 | 戻り値 | 例外 |
|---------|------|------|--------|------|
| `add(pattern)` | 追加（自動採番） | `TestPattern` | `TestPattern`（ID付き） | なし |
| `update(id, pattern)` | 更新 | ID, `TestPattern` | `TestPattern` | `KeyError` |
| `delete(id)` | 削除 | ID | `None` | `KeyError` |
| `get(id)` | 取得 | ID | `TestPattern` | `KeyError` |
| `get_all()` | 全件取得 | なし | `list[TestPattern]` | なし |
| `count` | 件数 | プロパティ | `int` | なし |
| `save_to_json(path)` | 保存 | `Path` | `None` | `IOError` |
| `load_from_json(path)` | 読込 | `Path` | `None` | `IOError`, `JSONDecodeError` |

**JSON 保存形式:**

```json
[
  {
    "test_case_id": "TC-001",
    "test_case_name": "エンジン回転数テスト",
    "target_signal": "EngineData.EngineSpeed",
    "operation": "エンジン回転数を 2000rpm に設定する",
    "expected_value": "スロットル開度が 20% 以上になること",
    "precondition": "エンジン停止状態",
    "wait_time_ms": 1000,
    "remarks": ""
  },
  {
    "test_case_id": "TC-002",
    ...
  }
]
```

---

### 3.3 OpenAIConverter（src/converter/openai_converter.py — Issue #14）

Azure OpenAI API を使用して日本語テスト記述を CANoe 操作パラメータに変換するエンジン。

#### 3.3.1 ConversionResult データクラス

```python
@dataclass
class ConversionResult:
    """変換結果

    1回の API 変換の結果を保持する。
    成功時は converted_params に構造化パラメータが入る。
    失敗時は success=False, error_message に原因が入る。
    """

    test_case_id: str                    # テストケースID
    original_text: str                   # 元の日本語テスト記述
    converted_params: dict[str, Any]     # 変換後のパラメータ
    success: bool = True                 # 変換成功フラグ
    error_message: str = ""              # エラーメッセージ
    confidence: float = 1.0              # 変換の信頼度 (0.0-1.0)
```

#### 3.3.2 OpenAIConverter クラス

```python
class OpenAIConverter:
    """Azure OpenAI 変換エンジン

    日本語テスト記述を構造化パラメータに変換する。
    要件定義書 3.1.3「日本語による自動生成」に準拠。
    """

    # --- 定数 ---
    MAX_RETRIES = 3                  # 最大リトライ回数
    RETRY_DELAY_BASE = 2.0           # リトライ基本待機秒数（指数バックオフ）

    # --- 環境変数キー ---
    ENV_ENDPOINT = "AZURE_OPENAI_ENDPOINT"
    ENV_API_KEY = "AZURE_OPENAI_API_KEY"
    ENV_DEPLOYMENT = "AZURE_OPENAI_DEPLOYMENT"
    ENV_API_VERSION = "AZURE_OPENAI_API_VERSION"
```

**公開API:**

| メソッド | 説明 | 引数 | 戻り値 |
|---------|------|------|--------|
| `configure_from_env()` | 環境変数から設定読み込み | なし | `None` (失敗時 `OpenAIConfigError`) |
| `configure(endpoint, api_key, deployment)` | 直接設定 | 3 つの `str` | `None` |
| `convert(test_case_id, operation_text, expected_text, signal_list?)` | 単一変換 | `str`, `str`, `str`, `list[str]?` | `ConversionResult` |
| `convert_batch(items, signal_list?)` | バッチ変換 | `list[tuple]`, `list[str]?` | `list[ConversionResult]` |

**内部メソッド:**

| メソッド | 説明 |
|---------|------|
| `_build_user_message(op, exp, signals)` | API 呼び出し用プロンプト構築 |
| `_call_api(user_message)` | HTTP リクエスト送信 |
| `_parse_response(id, op, exp, text)` | JSON レスポンス解析 |

#### 3.3.3 システムプロンプト設計

```
あなたはCANoe自動テストツールのアシスタントです。
ユーザーが日本語で記述したテストパターン（操作内容・期待値）を解析し、
以下のJSON構造に変換してください。

出力フォーマット:
{
    "signal_name": "信号名",
    "message_name": "メッセージ名",
    "action": "set" | "get" | "wait",
    "value": 数値または文字列,
    "channel": チャンネル番号(デフォルト1),
    "wait_ms": 待機時間(ms),
    "expected_value": 期待値(数値),
    "tolerance": 許容差(数値, デフォルト0),
    "judgment_type": "exact" | "range" | "change" | "timeout"
}

利用可能な信号リストが提供される場合は、そのリストから最適な信号を選択してください。
変換できない場合は {"error": "理由"} を返してください。
```

**プロンプト設計のポイント:**

| 設計要素 | 理由 |
|---------|------|
| `response_format: json_object` | GPT-4o の JSON モード使用。パースエラーを最小化 |
| `temperature: 0.1` | 変換の再現性を重視。ランダム性を抑制 |
| 信号リスト挿入 | 利用可能な信号から最適なものを選ばせる |
| `"error"` キー | 変換不可時の明示的なフォールバック |

#### 3.3.4 Azure OpenAI API 通信仕様

```
POST {endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}

Headers:
    Content-Type: application/json
    api-key: {api_key}

Body:
{
    "messages": [
        {"role": "system", "content": "<SYSTEM_PROMPT>"},
        {"role": "user", "content": "<操作内容 + 期待値 + 信号リスト>"}
    ],
    "temperature": 0.1,
    "response_format": {"type": "json_object"}
}
```

**HTTP クライアント優先順位:**

```
1. httpx (インストール済みの場合) — 非同期対応の高機能クライアント
2. urllib.request (標準ライブラリ) — 追加依存なし。CI 環境で確実に動作
```

#### 3.3.5 エラーハンドリング・リトライ戦略

```
attempt 1: API 呼び出し
    │
    ├─ 成功 → ConversionResult(success=True) を返す
    │
    └─ 失敗 → 2.0 秒待機（指数バックオフ: 2^0 = 1 × base）
              │
              ▼
attempt 2: API 呼び出し
    │
    ├─ 成功 → ConversionResult(success=True) を返す
    │
    └─ 失敗 → 4.0 秒待機（2^1 × base）
              │
              ▼
attempt 3: API 呼び出し（最終）
    │
    ├─ 成功 → ConversionResult(success=True) を返す
    │
    └─ 失敗 → OpenAIConversionError を送出
```

**指数バックオフの計算式:** `delay = RETRY_DELAY_BASE × 2^attempt`

| 試行 | 待機時間 |
|------|---------|
| 1→2 | 2.0 秒 |
| 2→3 | 4.0 秒 |

**レスポンスキャッシュ:**

同一の `(operation_text, expected_text)` ペアに対する API 応答をセッション内でキャッシュする。

```python
cache_key = f"{operation_text}|{expected_text}"
```

- **利点:** 同じ操作記述の重複呼び出しを回避し、API コストを削減
- **スコープ:** インスタンス内メモリキャッシュ（セッション終了で揮発）
- **キー方式:** 操作内容と期待値の文字列結合

#### 3.3.6 例外クラス

| 例外 | 用途 | 発生箇所 |
|------|------|---------|
| `OpenAIConfigError` | Azure OpenAI の設定不備 | `configure_from_env()` |
| `OpenAIConversionError` | API 呼び出し失敗・レスポンス不正 | `_call_api()`, `convert()` |

---

### 3.4 BatchConverter（src/converter/batch_converter.py — Issue #15）

全テストパターンを一括で Azure OpenAI 変換し、プレビュー・手動修正・確定の機能を提供する。

#### 3.4.1 PreviewItem データクラス

```python
@dataclass
class PreviewItem:
    """プレビュー項目

    1件のテストパターンに対する変換結果を保持する。
    ユーザーが確認・修正した後に confirmed=True にする。
    """

    test_case_id: str                        # テストケースID
    original_operation: str                  # 元の操作内容テキスト
    original_expected: str                   # 元の期待値テキスト
    converted_params: dict[str, object]      # 変換後パラメータ
    success: bool = True                     # 変換成功フラグ
    error_message: str = ""                  # エラーメッセージ
    manually_edited: bool = False            # 手動修正フラグ
    confirmed: bool = False                  # 確定フラグ
```

#### 3.4.2 BatchConverter クラス

```python
class BatchConverter:
    """テストパターン一括変換エンジン

    要件定義書 3.1.3「一括作成」に準拠。
    全テストパターンを順次変換し、プレビュー→手動修正→確定の
    ワークフローを管理する。
    """

    def __init__(self, converter: OpenAIConverter | None = None) -> None:
        self._converter = converter or OpenAIConverter()
        self._preview_items: list[PreviewItem] = []
        self._progress_callback: Callable[[int, int], None] | None = None
```

**公開 API:**

| メソッド | 説明 | 引数 | 戻り値 |
|---------|------|------|--------|
| `set_progress_callback(cb)` | 進捗コールバック設定 | `Callable[[int, int], None]` | `None` |
| `convert_all(patterns, signal_list?)` | 全パターン一括変換 | `list[TestPattern]`, `list[str]?` | `list[PreviewItem]` |
| `get_preview_items()` | プレビュー項目取得 | なし | `list[PreviewItem]` |
| `update_preview_item(id, params)` | 手動修正 | `str`, `dict` | `PreviewItem` |
| `confirm_all()` | 全件確定 | なし | `list[PreviewItem]`（成功分のみ） |
| `confirm_item(id)` | 個別確定 | `str` | `PreviewItem` |
| `export_confirmed(path)` | 確定済みJSON出力 | `Path` | `Path` |

#### 3.4.3 一括変換フロー

```
convert_all(patterns, signal_list)
    │
    ├── for each pattern in patterns:
    │       │
    │       ├── progress_callback(i+1, total)  ← 進捗通知
    │       │
    │       ├── converter.convert(id, op, expected, signals)
    │       │       │
    │       │       ├── 成功 → PreviewItem(success=True)
    │       │       │
    │       │       └── 例外 → PreviewItem(success=False, error_message)
    │       │
    │       └── _preview_items に追加
    │
    └── return list[PreviewItem]
```

**プレビュー→確定ワークフロー:**

```
一括変換
    │
    ▼
プレビュー表示（全 PreviewItem）
    │
    ├── 成功項目: パラメータ表示（確認用）
    │   ├── そのまま → confirm_item() or confirm_all()
    │   └── 修正が必要 → update_preview_item(id, new_params)
    │
    └── 失敗項目: エラーメッセージ表示
        └── 手動でパラメータを入力 → update_preview_item(id, params)
                                     └── confirm_item()
    │
    ▼
export_confirmed(output_path)
    │
    ▼
確定済み JSON ファイル → Phase 3 へ
```

**確定済み JSON 出力形式:**

```json
[
  {
    "test_case_id": "TC-001",
    "params": {
      "signal_name": "EngineSpeed",
      "message_name": "EngineData",
      "action": "set",
      "value": 2000,
      "channel": 1,
      "wait_ms": 1000,
      "expected_value": 20,
      "tolerance": 0,
      "judgment_type": "range"
    }
  }
]
```

---

### 3.5 SignalSelector（src/gui/signal_selector.py — Issue #12）

信号選択UIコンポーネント。Phase 1 の SignalRepository から信号を取得し、コンボボックスによる選択と絞り込み検索を提供する。

#### 3.5.1 クラス構造

```python
class SignalSelector:
    """信号選択コンポーネント

    要件定義書 3.1.1「信号選択UI」に準拠。
    ドロップダウン（コンボボックス）方式。
    信号名・メッセージ名での絞り込み検索対応。
    """

    def __init__(
        self,
        parent: tk.Widget | ttk.Frame,
        repository: SignalRepository,
    ) -> None:
        ...
```

#### 3.5.2 UI レイアウト

```
┌─ 信号選択 ─────────────────────────────────────────┐
│  信号検索: [___________________________]            │
│  信号:     [▼ コンボボックス          ] [追加]      │
└─────────────────────────────────────────────────────┘
┌─ 信号詳細 ─────────────────────────────────────────┐
│  信号名:       EngineSpeed                          │
│  メッセージ名: EngineData                           │
│  データ型:     unsigned                             │
│  値範囲:       0.0 ~ 8000.0                        │
│  単位:         rpm                                  │
│  プロトコル:   CAN                                  │
└─────────────────────────────────────────────────────┘
┌─ 選択済み信号 ─────────────────────────────────────┐
│  EngineData.EngineSpeed                             │
│  BrakeData.BrakeStatus                              │
│                                         [削除]      │
└─────────────────────────────────────────────────────┘
```

#### 3.5.3 ウィジェット構成

| ウィジェット | tkinter クラス | 役割 |
|-------------|---------------|------|
| 信号検索エントリ | `ttk.Entry` | 絞り込み検索テキスト入力 |
| 信号コンボボックス | `ttk.Combobox` | 信号選択（readonly） |
| 追加ボタン | `ttk.Button` | 選択信号を選択済みリストに追加 |
| 信号詳細ラベル群 | `ttk.Label` × 6 | 選択中の信号の詳細情報表示 |
| 選択済みリスト | `tk.Listbox` | 選択済み信号一覧 |
| 削除ボタン | `ttk.Button` | 選択済み信号を削除 |

#### 3.5.4 公開 API

| メソッド | 説明 | 戻り値 |
|---------|------|--------|
| `get_selected_signals()` | 選択された信号リスト取得 | `list[SignalInfo]` |
| `get_signal_names()` | 全信号の表示名リスト取得 | `list[str]` |
| `filter_signals(query)` | 検索結果の信号名リスト | `list[str]` |

#### 3.5.5 イベント処理

```
検索テキスト変更 (trace_add "write")
    └── _on_search_changed()
        └── _update_combo_values()
            └── repository.search(query) → コンボボックス更新

コンボボックス選択 (<<ComboboxSelected>>)
    └── _on_combo_selected()
        └── _find_signal_by_display_name(name)
            └── _show_signal_detail(signal)
                └── 詳細ラベル 6 項目を更新

追加ボタン押下
    └── _on_add_signal()
        └── 選択信号を _selected_signals リストに追加
            └── Listbox に表示名を追加

削除ボタン押下
    └── _on_remove_signal()
        └── Listbox の選択項目と _selected_signals から削除
```

---

## 4. インターフェース定義

### 4.1 Model → Converter

TestPatternRepository から TestPattern リストを取得し、BatchConverter に渡す:

```
TestPatternRepository.get_all() -> list[TestPattern]
    │
    └── BatchConverter.convert_all(patterns, signal_list)
            │
            └── OpenAIConverter.convert(id, operation, expected, signals)
```

### 4.2 GUI → Model

```
SignalSelector → SignalRepository（Phase 1 実装済み）
    SignalRepository.search(query) -> list[SignalInfo]
    SignalRepository.get_all() -> list[SignalInfo]

TestPatternForm → TestPatternRepository
    TestPatternRepository.add(pattern) -> TestPattern
    TestPatternRepository.update(id, pattern) -> TestPattern
    TestPatternRepository.delete(id) -> None
    TestPatternRepository.get_all() -> list[TestPattern]
    TestPatternRepository.save_to_json(path) -> None
    TestPatternRepository.load_from_json(path) -> None
```

### 4.3 Converter → Azure OpenAI API

```
OpenAIConverter._call_api(user_message: str) -> str
    │
    ├── HTTP POST: {endpoint}/openai/deployments/{deployment}/chat/completions
    │   Headers: api-key, Content-Type
    │   Body: messages + temperature + response_format
    │
    └── Response: {"choices": [{"message": {"content": "<JSON>"}}]}
```

### 4.4 BatchConverter → JSON 出力

```
BatchConverter.export_confirmed(output_path: Path) -> Path
    │
    └── JSON 配列: [{"test_case_id": "TC-001", "params": {...}}, ...]
```

### 4.5 エラーハンドリング方針

| 層 | エラー種別 | 処理 |
|----|-----------|------|
| Model | `KeyError` | 存在しないパターンIDのCRUD操作 |
| Model | `json.JSONDecodeError` | JSON 読み込み失敗 |
| Converter | `OpenAIConfigError` | 環境変数未設定 |
| Converter | `OpenAIConversionError` | API 呼び出し失敗（リトライ後） |
| Converter | JSON パースエラー | `ConversionResult(success=False)` で吸収 |
| BatchConverter | 個別変換例外 | `PreviewItem(success=False)` で吸収。バッチ全体は中断しない |
| GUI | Converter 例外 | `messagebox.showerror()` で日本語エラー表示 |

**重要な設計判断:** BatchConverter はバッチ内の個別失敗で全体を中断しない。失敗した項目は `PreviewItem(success=False)` として記録し、ユーザーが手動で修正・リトライできるようにする。

---

## 5. Azure OpenAI 連携設計

### 5.1 抽象化設計（LLMProvider Protocol）

将来的な LLM プロバイダーの差し替えを見据え、Protocol（構造的部分型）による抽象化を行う。

```python
from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """LLM プロバイダー抽象インターフェース

    Azure OpenAI 以外の LLM（例: Claude, Gemini, ローカル LLM）への
    差し替えを可能にするための Protocol。
    """

    def convert_pattern(
        self,
        test_case_id: str,
        operation_text: str,
        expected_text: str,
        signal_list: list[str] | None = None,
    ) -> ConversionResult:
        """日本語テスト記述を構造化パラメータに変換

        Args:
            test_case_id: テストケースID
            operation_text: 操作内容（日本語）
            expected_text: 期待値（日本語）
            signal_list: 利用可能な信号名リスト

        Returns:
            変換結果
        """
        ...
```

**現在の実装:**

```
LLMProvider (Protocol)
    │
    └── OpenAIConverter   ← 現在唯一の実装
        │
        ├── configure_from_env()    — 環境変数から認証情報読み込み
        ├── configure()             — 直接設定
        ├── convert()               — LLMProvider.convert_pattern() に対応
        └── convert_batch()         — バッチ変換（BatchConverter 経由）
```

**差し替え例（将来）:**

```python
# ローカル LLM を使う場合
class LocalLLMConverter:
    def convert_pattern(self, test_case_id, operation_text, expected_text, signal_list=None):
        # ローカルモデルで変換
        ...

# BatchConverter に注入
batch = BatchConverter(converter=LocalLLMConverter())
```

> **注:** 現在の実装では `OpenAIConverter` のメソッド名は `convert()` であり、Protocol の `convert_pattern()` とは異なる。Phase 2 後半のリファクタリングで統一するか、アダプタパターンで接続する。

### 5.2 環境変数設定

| 環境変数名 | 必須 | 説明 | 例 |
|-----------|------|------|-----|
| `AZURE_OPENAI_ENDPOINT` | はい | Azure OpenAI エンドポイント URL | `https://myresource.openai.azure.com` |
| `AZURE_OPENAI_API_KEY` | はい | API キー | `abc123...` |
| `AZURE_OPENAI_DEPLOYMENT` | はい | デプロイメント名 | `gpt-4o` |
| `AZURE_OPENAI_API_VERSION` | いいえ | API バージョン（デフォルト: `2024-02-01`） | `2024-02-01` |

### 5.3 変換入出力例

**入力（日本語テスト記述）:**

```
操作内容: エンジン回転数を 2000rpm に設定して、スロットル開度が 20% 以上になることを確認する
期待値: スロットル開度 >= 20%

利用可能な信号:
EngineData.EngineSpeed, EngineData.ThrottlePosition, BrakeData.BrakePedal
```

**出力（構造化パラメータ）:**

```json
{
    "signal_name": "EngineSpeed",
    "message_name": "EngineData",
    "action": "set",
    "value": 2000,
    "channel": 1,
    "wait_ms": 1000,
    "expected_value": 20,
    "tolerance": 0,
    "judgment_type": "range"
}
```

**変換不可時:**

```json
{
    "error": "操作対象の信号を特定できません。信号名を明示してください。"
}
```

### 5.4 セキュリティ考慮

| 観点 | 対策 |
|------|------|
| API Key 管理 | 環境変数で管理。コードにハードコード禁止 |
| Key Vault | 将来対応: Azure Key Vault からの取得をサポート予定 |
| ログ出力 | API Key をログに出力しない（`logger.warning` でリトライ情報のみ） |
| CI 環境 | API Key 不要（テストではモック/スタブ使用） |
| ネットワーク | HTTPS のみ。タイムアウト 30 秒 |

---

## 6. テスト方針

### 6.1 TDD プロセス

Phase 1 と同様、全実装は TDD で進める:

```
Red:   テストを書く → 失敗を確認
Green: 最小限の実装でテストを通す
Refactor: コードを整理（テストは引き続きパス）
```

### 6.2 テスト構成

| テスト種別 | ファイル | 対象 Issue | テスト数（目安） |
|-----------|---------|-----------|----------------|
| ユニットテスト | `test_test_pattern.py` | #13 | 12 件 |
| ユニットテスト | `test_openai_converter.py` | #14 | 12 件 |
| ユニットテスト | `test_batch_converter.py` | #15 | 10 件 |
| ユニットテスト | `test_signal_selector.py` | #12 | 10 件 |
| 統合テスト | `test_pattern_flow.py` | #12-15 | 5 件 |

### 6.3 AI 部分のモック/スタブ戦略

**原則:** Azure OpenAI API の実際の呼び出しはテストで行わない。全て モック/スタブ で代替する。

```python
# テストでの OpenAIConverter モック例
from unittest.mock import MagicMock, patch

def test_convert_batch_success():
    mock_converter = MagicMock(spec=OpenAIConverter)
    mock_converter.convert.return_value = ConversionResult(
        test_case_id="TC-001",
        original_text="操作",
        converted_params={"signal_name": "EngineSpeed", "action": "set", "value": 3000},
        success=True,
    )
    batch = BatchConverter(converter=mock_converter)
    results = batch.convert_all([pattern])
    assert results[0].success
```

**モック対象と方法:**

| 対象 | モック方法 | 理由 |
|------|----------|------|
| `OpenAIConverter._call_api()` | `patch.object()` | API 呼び出しを遮断 |
| `OpenAIConverter` インスタンス | `MagicMock(spec=OpenAIConverter)` | BatchConverter テストで注入 |
| `os.environ` | `patch.dict("os.environ", ...)` | 環境変数の設定テスト |
| `time.sleep` | `patch("...time.sleep")` | リトライ待機をスキップ |
| `tkinter` ウィジェット | `MagicMock()` | GUI なし環境（CI）対応 |

### 6.4 ユニットテスト詳細

#### test_test_pattern.py（Issue #13）

```python
class TestTestPattern:
    def test_create_pattern(self): ...              # デフォルト値で生成
    def test_to_dict(self): ...                     # 辞書変換
    def test_from_dict(self): ...                   # 辞書から復元

class TestTestPatternRepository:
    def test_add_auto_assigns_id(self): ...         # ID自動採番 TC-001
    def test_add_sequential_ids(self): ...          # 連番 TC-001, TC-002
    def test_count(self): ...                       # 件数
    def test_get_all(self): ...                     # 全件取得
    def test_get_by_id(self): ...                   # ID指定取得
    def test_get_nonexistent_raises(self): ...      # 存在しないIDでKeyError
    def test_update(self): ...                      # 更新（ID保持）
    def test_update_nonexistent_raises(self): ...   # 存在しないIDでKeyError
    def test_delete(self): ...                      # 削除
    def test_delete_nonexistent_raises(self): ...   # 存在しないIDでKeyError
    def test_save_and_load_json(self): ...          # 保存→読込の往復
    def test_load_preserves_next_id(self): ...      # 読込後の採番継続
```

#### test_openai_converter.py（Issue #14）

```python
class TestOpenAIConverterConfig:
    def test_configure_from_env_missing_endpoint(self): ...   # ENDPOINT 未設定
    def test_configure_from_env_missing_api_key(self): ...    # API_KEY 未設定
    def test_configure_from_env_missing_deployment(self): ... # DEPLOYMENT 未設定
    def test_configure_from_env_success(self): ...            # 正常設定
    def test_configure_direct(self): ...                      # 直接設定

class TestOpenAIConverterConvert:
    def test_convert_not_configured_raises(self): ...    # 未設定で変換→エラー
    def test_parse_response_success(self): ...           # 正常JSON解析
    def test_parse_response_error(self): ...             # "error" キー含むレスポンス
    def test_parse_response_invalid_json(self): ...      # 不正JSON
    def test_cache_hit(self): ...                        # キャッシュヒット
    def test_build_user_message_with_signals(self): ...  # 信号リスト付きメッセージ
    def test_build_user_message_without_signals(self): ... # 信号リストなし

class TestOpenAIConverterBatch:
    def test_convert_batch_with_failures(self): ...      # バッチ変換（一部失敗）
```

#### test_batch_converter.py（Issue #15）

```python
class TestBatchConverterConvertAll:
    def test_convert_all_empty(self): ...                # 空リスト
    def test_convert_all_success(self): ...              # 正常変換
    def test_convert_all_with_error(self): ...           # エラー発生時
    def test_progress_callback(self): ...                # 進捗コールバック

class TestBatchConverterPreview:
    def test_get_preview_items(self): ...                # プレビュー取得
    def test_update_preview_item(self): ...              # 手動修正
    def test_update_nonexistent_raises(self): ...        # 存在しないID

class TestBatchConverterConfirm:
    def test_confirm_all(self): ...                      # 全件確定
    def test_confirm_item(self): ...                     # 個別確定
    def test_confirm_nonexistent_raises(self): ...       # 存在しないID
    def test_export_confirmed(self): ...                 # JSON出力
```

#### test_signal_selector.py（Issue #12）

```python
class TestSignalSelectorCreation:
    def test_creates_with_repo(self): ...             # リポジトリ注入
    def test_has_search_entry(self): ...              # 検索エントリ存在
    def test_has_combo(self): ...                     # コンボボックス存在
    def test_has_detail_labels(self): ...             # 詳細ラベル存在

class TestSignalSelectorSearch:
    def test_get_signal_names(self): ...              # 全信号名取得
    def test_filter_signals(self): ...                # 絞り込み検索
    def test_filter_empty_returns_all(self): ...      # 空検索は全件

class TestSignalSelectorSelection:
    def test_initial_selection_empty(self): ...       # 初期選択は空
    def test_find_signal_by_display_name(self): ...   # 表示名から信号検索
    def test_find_nonexistent_signal(self): ...       # 存在しない信号
```

### 6.5 統合テスト（test_pattern_flow.py）

```python
class TestPatternCreationFlow:
    def test_create_pattern_to_json(self): ...         # パターン作成→JSON保存
    def test_load_and_convert_batch(self): ...          # JSON読込→一括変換
    def test_preview_edit_confirm_export(self): ...     # プレビュー→修正→確定→出力
    def test_signal_selection_to_pattern(self): ...     # 信号選択→パターン作成
    def test_full_flow_mock_api(self): ...              # E2E（API モック）
```

### 6.6 CI 環境での考慮事項

| 環境 | 対応 |
|------|------|
| Linux CI（GitHub Actions） | tkinter モック（conftest.py 既存対応） |
| Azure OpenAI API | 全テストでモック使用。実 API 呼び出しなし |
| 環境変数 | `patch.dict("os.environ")` で注入 |
| ヘッドレス環境 | `display` 不要。GUI テストは tkinter モックで対応 |

### 6.7 カバレッジ目標

| モジュール | 目標カバレッジ |
|-----------|--------------|
| `src/models/test_pattern.py` | 95% 以上 |
| `src/converter/openai_converter.py` | 90% 以上 |
| `src/converter/batch_converter.py` | 90% 以上 |
| `src/gui/signal_selector.py` | 70% 以上 |
| Phase 2 全体 | 85% 以上 |

---

## 7. 実装順序（推奨）

```
Step 1: テストパターンデータモデル (Issue #13)
        ├── TestPattern dataclass
        ├── TestPatternRepository (CRUD + JSON)
        └── ユニットテスト (test_test_pattern.py)

Step 2: (並列実行可能)
        ├── 信号選択UI (Issue #12)
        │   ├── SignalSelector コンポーネント
        │   └── ユニットテスト (test_signal_selector.py)
        │
        └── Azure OpenAI 変換ロジック (Issue #14)
            ├── OpenAIConverter クラス
            ├── ConversionResult dataclass
            └── ユニットテスト (test_openai_converter.py)

Step 3: テストパターン一括生成・プレビュー (Issue #15)
        ├── BatchConverter クラス
        ├── PreviewItem dataclass
        ├── ユニットテスト (test_batch_converter.py)
        └── 統合テスト (test_pattern_flow.py)

Step 4: テストパターン入力フォーム GUI (Issue #13 の GUI 部分)
        ├── TestPatternForm（テストパターン入力画面）
        ├── MainWindow 統合（Phase 2 タブのプレースホルダ置き換え）
        └── 動作確認
```

### 依存関係

```
Issue #13 (TestPattern)
    │
    ├──→ Issue #12 (SignalSelector) — 並列可: SignalRepository は Phase 1 で実装済み
    │
    └──→ Issue #14 (OpenAIConverter)
             │
             └──→ Issue #15 (BatchConverter) — #14 に依存
```

### 並列実行の最適化

足軽2〜3名で実施する場合の最適配分:

```
足軽A: #13 (モデル)     → #15 (BatchConverter, #14完了待ち)
足軽B: #12 (信号選択UI) → GUI統合（テストパターン入力フォーム）
足軽C: #14 (OpenAI変換) → 統合テスト
```

**クリティカルパス:** `#13 → #14 → #15`

> **注意:** #13（TestPattern）はConverter (#14, #15) と GUI (#12, フォーム) の両方が依存するため、最優先で完了させること。Phase 1 の #9（SignalInfo）と同じ位置付け。

---

## 8. Phase 1 からの変更点

### MainWindow の更新

Phase 2 タブのプレースホルダを実コンポーネントに置き換える:

```python
# Before (Phase 1):
ph2_frame = ttk.Frame(self.notebook)
ttk.Label(ph2_frame, text="準備中（Phase 2 で実装）").pack(pady=50)
self.notebook.add(ph2_frame, text="テストパターン作成")

# After (Phase 2):
self.pattern_frame = ttk.Frame(self.notebook)
self.notebook.add(self.pattern_frame, text="テストパターン作成")
# SignalSelector + TestPatternForm を pattern_frame に配置
```

### 依存ライブラリ追加

| ライブラリ | バージョン | 用途 | 必須 |
|-----------|-----------|------|------|
| openai | >= 1.0.0 | Azure OpenAI 公式クライアント | オプション |
| httpx | >= 0.25.0 | HTTP クライアント（openai 不使用時） | オプション |

> **注:** 現在の実装では `urllib.request`（標準ライブラリ）をフォールバックとして使用しており、追加の依存ライブラリなしで動作する。

---

## 9. Phase 3 との接続ポイント

Phase 2 の出力が Phase 3（テスト自動実行）の入力になる:

```
Phase 2 出力                         Phase 3 入力
─────────────                       ─────────────
BatchConverter.export_confirmed()    → TestRunner.load_test_params()
    │                                      │
    ▼                                      ▼
confirmed_params.json                テスト実行エンジン
[                                    ├── CANoe COM API 連携
  {                                  ├── 信号送信/受信
    "test_case_id": "TC-001",        └── 結果判定
    "params": {
      "signal_name": "EngineSpeed",
      "action": "set",
      "value": 2000,
      ...
    }
  }
]
```

**Phase 3 が Phase 2 に期待する出力:**

- JSON ファイル（`confirmed_params.json`）
- 各項目に `test_case_id` と構造化 `params` が含まれる
- `params` は `signal_name`, `action`, `value`, `expected_value`, `judgment_type` を必ず含む

---

## 10. 用語集（Phase 2 追加分）

| 用語 | 読み方 | 意味 |
|------|--------|------|
| Azure OpenAI | アジュールオープンエーアイ | Microsoft Azure 上でホストされた OpenAI の GPT モデルサービス |
| GPT-4o | ジーピーティーフォーオー | OpenAI のマルチモーダル大規模言語モデル |
| JSON mode | ジェイソンモード | GPT-4o の機能。出力を有効な JSON に制約する |
| LLMProvider | エルエルエムプロバイダー | 本設計における LLM 抽象インターフェース（Protocol） |
| Protocol (typing) | プロトコル | Python の構造的部分型（ダックタイピングの型チェック版） |
| PreviewItem | プレビューアイテム | 変換結果のプレビュー単位。確認・修正・確定のワークフロー管理 |
| BatchConverter | バッチコンバーター | 全テストパターンを一括で変換するエンジン |
| 指数バックオフ | しすうバックオフ | リトライ間隔を指数関数的に増やす戦略。API サーバーへの負荷を分散 |
| キャッシュ | — | 同一入力の API 応答をメモリに保持し、重複呼び出しを回避する仕組み |
| runtime_checkable | ランタイムチェッカブル | Protocol を `isinstance()` で実行時チェック可能にするデコレータ |

---

## 付録A: 変換パラメータ JSON スキーマ

Azure OpenAI API が返す変換結果の期待フォーマット:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "signal_name": {
      "type": "string",
      "description": "対象信号名（CANdb/LDF の信号名）"
    },
    "message_name": {
      "type": "string",
      "description": "メッセージ名（CANdb/LDF のメッセージ名）"
    },
    "action": {
      "type": "string",
      "enum": ["set", "get", "wait"],
      "description": "操作種別"
    },
    "value": {
      "description": "送信値（数値または文字列）"
    },
    "channel": {
      "type": "integer",
      "default": 1,
      "description": "CANoe チャンネル番号"
    },
    "wait_ms": {
      "type": "integer",
      "description": "操作後の待機時間（ms）"
    },
    "expected_value": {
      "description": "期待値（数値）"
    },
    "tolerance": {
      "type": "number",
      "default": 0,
      "description": "許容差"
    },
    "judgment_type": {
      "type": "string",
      "enum": ["exact", "range", "change", "timeout"],
      "description": "判定種別（要件定義書 3.3.1 準拠）"
    }
  },
  "required": ["signal_name", "action"]
}
```

---

## 付録B: 依存ライブラリ一覧（Phase 2 累積）

| ライブラリ | バージョン | 何に使う? | 必須? | Phase |
|-----------|-----------|----------|------|-------|
| cantools | >= 39.0.0 | .dbc ファイルのパース | はい | 1 |
| ldfparser | >= 0.24.0 | .ldf ファイルのパース | はい | 1 |
| pytest | >= 8.0.0 | テスト実行 | 開発時のみ | 1 |
| pytest-cov | >= 4.1.0 | テストカバレッジ計測 | 開発時のみ | 1 |
| ruff | >= 0.2.0 | コードの書き方チェック（リンター） | 開発時のみ | 1 |
| mypy | >= 1.8.0 | 型のチェック（静的解析） | 開発時のみ | 1 |
| openai | >= 1.0.0 | Azure OpenAI 公式クライアント | オプション | 2 |
| httpx | >= 0.25.0 | HTTP クライアント | オプション | 2 |
| pywin32 | >= 306 | CANoe COM API 操作 | Phase 3 以降 | 3 |
| openpyxl | >= 3.1.0 | Excel ファイル生成 | Phase 4 以降 | 4 |

---

*本文書は Phase 2 設計書 Ver.1.0 です。実装中に判明した設計変更は版管理のうえ更新してください。*

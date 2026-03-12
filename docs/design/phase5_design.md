# Phase 5: E2Eテスト・改善 — 設計書

**Version:** 1.0　|　**作成日:** 2026-03-12　|　**対応Issue:** #23, #24, #25

---

## 目次

1. [Phase 5 概要・目的](#1-phase-5-概要目的)
2. [E2Eテスト設計（Issue #23）](#2-e2eテスト設計issue-23)
3. [UI/UX改善計画（Issue #24）](#3-uiux改善計画issue-24)
4. [ドキュメント構成計画（Issue #25）](#4-ドキュメント構成計画issue-25)
5. [新規ファイル・変更ファイル一覧](#5-新規ファイル変更ファイル一覧)
6. [テスト方針](#6-テスト方針)
7. [実装順序（推奨）](#7-実装順序推奨)

---

## 1. Phase 5 概要・目的

### 1.1 位置づけ

Phase 5 は CANoe 自動テストツールの最終フェーズであり、Phase 1〜4 で構築した全機能を統合的に検証し、ユーザー体験を改善し、ドキュメントを整備する「仕上げ」のフェーズである。

### 1.2 目的

| 目的 | 説明 |
|------|------|
| **品質保証** | Phase 1〜4 を横断する E2E テストにより、一気通貫の動作を保証する |
| **操作性向上** | 既存 GUI の課題を解消し、日常業務で快適に使えるツールにする |
| **知識の定着** | 取扱説明書・開発者ドキュメントにより、属人性を排除する |

### 1.3 スコープ（3 Issue）

| Issue | タイトル | 内容 |
|-------|---------|------|
| #23 | E2Eシナリオテスト実装 | 全フェーズ通しテスト、モック戦略、テストデータ設計 |
| #24 | UI改善・UX最適化 | エラーメッセージ改善、キーボードショートカット、操作性向上 |
| #25 | ドキュメント整備・取扱説明書作成 | 取扱説明書、開発者ドキュメント、README 更新 |

---

## 2. E2Eテスト設計（Issue #23）

### 2.1 現状のテスト構成と課題

#### 2.1.1 現在のテストカバレッジ

| テスト種別 | ファイル数 | テスト数 | カバー範囲 |
|-----------|----------|---------|-----------|
| ユニットテスト | 13 | ~150 | 各モジュール単体 |
| 結合テスト | 2 | ~10 | パーサー連携、基本 E2E |
| E2E テスト | 1 | 4 | Phase 1 のみ（パース→検索→フィルタ） |

#### 2.1.2 未カバーの領域（Phase 5 で対応）

| ギャップ | 説明 |
|---------|------|
| **フェーズ横断テスト** | Phase 1→2→3→4 を通した一連のワークフローテストが存在しない |
| **CANoe モック統合** | CANoe COM API のモックを使った実行シナリオテストが未実装 |
| **異常系 E2E** | API タイムアウト、COM 切断、ファイル破損等の復旧テストがない |
| **GUI 統合テスト** | タブ間のデータ連携テストが存在しない |
| **帳票出力 E2E** | 判定結果 → Excel 帳票の一連の流れのテストがない |

### 2.2 ディレクトリ構成

```
tests/
├── conftest.py                          # (既存) tkinter モック等
├── fixtures/                            # (既存) テスト用サンプルファイル
│   ├── sample.dbc                       # (既存) CAN サンプル
│   ├── sample.ldf                       # (既存) LIN サンプル
│   ├── e2e/                             # ★ E2E テスト用フィクスチャ
│   │   ├── test_patterns.json           # ★ テストパターンサンプル
│   │   ├── confirmed_params.json        # ★ 変換確定済みパラメータ
│   │   ├── expected_results.json        # ★ 期待結果データ
│   │   ├── mock_canoe_responses.json    # ★ CANoe モックレスポンス定義
│   │   └── expected_report.json         # ★ 期待帳票データ
│   └── error/                           # ★ 異常系テスト用
│       ├── corrupted.dbc                # ★ 破損 DBC ファイル
│       ├── empty.ldf                    # ★ 空 LDF ファイル
│       └── invalid_pattern.json         # ★ 不正テストパターン
├── unit/                                # (既存) ユニットテスト
├── integration/                         # (既存) 結合テスト
│   ├── test_parsers_integration.py      # (既存)
│   └── test_e2e_basic.py               # (既存) Phase 1 E2E
└── e2e/                                 # ★ Phase 5 E2E テスト
    ├── __init__.py                      # ★
    ├── conftest.py                      # ★ E2E 専用フィクスチャ・ヘルパー
    ├── test_full_pipeline.py            # ★ 全フェーズ通し E2E
    ├── test_conversion_flow.py          # ★ パターン作成→変換 E2E
    ├── test_execution_flow.py           # ★ 実行→判定→帳票 E2E
    └── test_error_recovery.py           # ★ 異常系・回復 E2E
```

### 2.3 モック戦略

#### 2.3.1 モック対象一覧

E2E テストでは以下の外部依存をモックで代替する。

| モック対象 | モック方法 | 理由 |
|-----------|----------|------|
| **CANoe COM API** | `MockCANoeCOM` クラス | Linux CI 環境で動作不可（Windows + CANoe 必須） |
| **Azure OpenAI API** | `MockOpenAIConverter` クラス | API キー不要、コスト回避、再現性確保 |
| **tkinter** | 既存 conftest.py モック | Linux CI 環境で X11 不要 |
| **ファイルシステム** | `tmp_path` フィクスチャ | テスト間の独立性確保 |

#### 2.3.2 MockCANoeCOM 設計

```python
class MockCANoeCOM:
    """CANoe COM API モック

    E2E テスト用。シナリオに応じた信号値を返す。
    JSON ファイルで応答パターンを定義可能。
    """

    def __init__(self, response_file: Path | None = None) -> None:
        self._state: CANoeState = CANoeState.DISCONNECTED
        self._config_path: str = ""
        self._signal_values: dict[str, float] = {}
        self._responses: dict[str, list[dict]] = {}  # シナリオ応答
        if response_file:
            self._load_responses(response_file)

    def connect(self) -> None:
        """接続（常に成功）"""
        self._state = CANoeState.CONNECTED

    def load_config(self, config_path: str) -> None:
        """構成ファイル読み込み（パス保持のみ）"""
        self._config_path = config_path
        self._state = CANoeState.CONNECTED

    def start_measurement(self) -> None:
        """測定開始"""
        self._state = CANoeState.MEASURING

    def stop_measurement(self) -> None:
        """測定停止"""
        self._state = CANoeState.CONNECTED

    def set_signal_value(
        self, channel: int, message: str, signal: str, value: float
    ) -> None:
        """信号値設定（内部辞書に保持）"""
        key = f"{channel}.{message}.{signal}"
        self._signal_values[key] = value
        # シナリオ応答: 入力に応じた期待値を自動設定
        self._apply_scenario_response(key, value)

    def get_signal_value(
        self, channel: int, message: str, signal: str
    ) -> float:
        """信号値取得（シナリオ応答 or 設定値を返す）"""
        key = f"{channel}.{message}.{signal}"
        return self._signal_values.get(key, 0.0)

    def _load_responses(self, path: Path) -> None:
        """JSON からシナリオ応答を読み込み"""
        import json
        text = path.read_text(encoding="utf-8")
        self._responses = json.loads(text)

    def _apply_scenario_response(self, key: str, value: float) -> None:
        """シナリオに基づく応答値を設定"""
        for scenario in self._responses.get(key, []):
            if scenario.get("input") == value:
                for out_key, out_val in scenario.get("outputs", {}).items():
                    self._signal_values[out_key] = out_val
```

#### 2.3.3 MockOpenAIConverter 設計

```python
class MockOpenAIConverter:
    """Azure OpenAI 変換モック

    固定の変換結果を返す。テストデータ JSON から応答を定義可能。
    """

    def __init__(self, responses: dict[str, ConversionResult] | None = None) -> None:
        self._responses = responses or {}
        self._call_count: int = 0

    def convert(
        self,
        test_case_id: str,
        operation_text: str,
        expected_text: str,
        signal_list: list[str] | None = None,
    ) -> ConversionResult:
        """固定レスポンスを返す"""
        self._call_count += 1
        if test_case_id in self._responses:
            return self._responses[test_case_id]
        # デフォルト: 操作テキストから信号名を推測
        return ConversionResult(
            test_case_id=test_case_id,
            original_text=operation_text,
            converted_params={
                "signal_name": "MockSignal",
                "action": "set",
                "value": 0,
                "judgment_type": "exact",
            },
            success=True,
        )
```

#### 2.3.4 モック応答 JSON 形式（mock_canoe_responses.json）

```json
{
  "1.EngineData.EngineSpeed": [
    {
      "input": 2000,
      "outputs": {
        "1.EngineData.ThrottlePosition": 22.5
      }
    },
    {
      "input": 0,
      "outputs": {
        "1.EngineData.ThrottlePosition": 0.0
      }
    }
  ]
}
```

### 2.4 テストシナリオ一覧

#### 2.4.1 正常系シナリオ

| # | シナリオ名 | テスト内容 | カバーするフェーズ |
|---|-----------|----------|------------------|
| E2E-N01 | **全フェーズ通しテスト** | DBC/LDF 読込→パターン作成→AI 変換→CANoe 実行→判定→帳票出力 | Ph1→2→3→4 |
| E2E-N02 | **複数ファイル混合テスト** | DBC + LDF を同時読み込み、CAN/LIN 混合のテストパターンを実行 | Ph1→2→3 |
| E2E-N03 | **一括変換→プレビュー→確定** | 10 件のテストパターンを一括変換し、プレビュー確認後に確定・JSON 出力 | Ph2 |
| E2E-N04 | **テスト実行→判定→帳票** | 確定済みパラメータ JSON → TestRunner 実行 → JudgmentEngine 判定 → Excel 帳票 | Ph3→4 |
| E2E-N05 | **全判定タイプテスト** | EXACT / RANGE / CHANGE / TIMEOUT / COMPOUND の 5 判定タイプを含む混合テスト | Ph3→4 |
| E2E-N06 | **テスト結果 JSON 永続化** | 実行結果 JSON + ログ CSV/JSON の保存・再読み込み検証 | Ph3→4 |
| E2E-N07 | **帳票フォーマット検証** | Excel 帳票の全 3 シート（サマリ・統計・詳細）の内容・書式検証 | Ph4 |
| E2E-N08 | **大量パターン実行** | 50 件のテストパターンを連続実行し、進捗コールバックの正確性を検証 | Ph3 |

#### 2.4.2 異常系シナリオ

| # | シナリオ名 | テスト内容 | 期待動作 |
|---|-----------|----------|---------|
| E2E-E01 | **破損ファイル読込** | 破損 DBC / 空 LDF / 不正形式ファイルの読み込み | DBCParseError / LDFParseError を適切に送出 |
| E2E-E02 | **AI 変換失敗** | OpenAI API モック: 全件エラー → PreviewItem(success=False) | バッチ全体は中断せず、失敗項目を記録 |
| E2E-E03 | **AI 変換部分失敗** | 10 件中 3 件が変換失敗 → 成功 7 件のみ確定可能 | 成功分のみ export_confirmed() で出力 |
| E2E-E04 | **CANoe 接続失敗** | MockCANoeCOM: connect() で CANoeError 送出 | TestRunner が ERROR ステータスで結果返却 |
| E2E-E05 | **CANoe 測定中切断** | 実行中に stop_measurement() が例外 | 実行中断、ABORTED ステータスで結果記録 |
| E2E-E06 | **テスト中断（abort）** | 実行中に runner.abort() 呼び出し | 残りパターンを SKIPPED で記録、部分結果を保持 |
| E2E-E07 | **不正テストパターン** | 信号名が空 / wait_time_ms が負値 / 不正 JSON | バリデーションエラーまたは ERROR 結果 |
| E2E-E08 | **帳票出力先なし** | 存在しないディレクトリへの Excel 出力 | FileNotFoundError を適切に送出 |

### 2.5 テストデータ設計（フィクスチャ）

#### 2.5.1 test_patterns.json

```json
[
  {
    "test_case_id": "TC-001",
    "test_case_name": "エンジン回転数設定テスト",
    "target_signal": "EngineData.EngineSpeed",
    "operation": "エンジン回転数を 2000rpm に設定する",
    "expected_value": "スロットル開度が 20% 以上",
    "precondition": "エンジン停止状態",
    "wait_time_ms": 1000,
    "remarks": ""
  },
  {
    "test_case_id": "TC-002",
    "test_case_name": "ブレーキペダル応答テスト",
    "target_signal": "BrakeData.BrakePedal",
    "operation": "ブレーキペダルを 50% まで踏み込む",
    "expected_value": "ブレーキランプが点灯",
    "precondition": "車速 60km/h 走行中",
    "wait_time_ms": 500,
    "remarks": "安全系テスト"
  },
  {
    "test_case_id": "TC-003",
    "test_case_name": "冷却水温度変化テスト",
    "target_signal": "EngineData.CoolantTemp",
    "operation": "冷却水温度を監視する（操作なし）",
    "expected_value": "温度が 80℃〜100℃ の範囲内",
    "precondition": "エンジン暖機完了後",
    "wait_time_ms": 3000,
    "remarks": "RANGE 判定"
  }
]
```

#### 2.5.2 confirmed_params.json

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
      "expected_signal": "ThrottlePosition",
      "expected_message": "EngineData",
      "expected_value": 20,
      "tolerance": 0,
      "judgment_type": "range"
    }
  },
  {
    "test_case_id": "TC-002",
    "params": {
      "signal_name": "BrakePedal",
      "message_name": "BrakeData",
      "action": "set",
      "value": 50,
      "channel": 1,
      "wait_ms": 500,
      "expected_signal": "BrakeLamp",
      "expected_message": "BrakeData",
      "expected_value": 1,
      "tolerance": 0,
      "judgment_type": "exact"
    }
  },
  {
    "test_case_id": "TC-003",
    "params": {
      "signal_name": "CoolantTemp",
      "message_name": "EngineData",
      "action": "get",
      "value": null,
      "channel": 1,
      "wait_ms": 3000,
      "expected_signal": "CoolantTemp",
      "expected_message": "EngineData",
      "expected_value": null,
      "tolerance": 0,
      "judgment_type": "range",
      "range_min": 80,
      "range_max": 100
    }
  }
]
```

#### 2.5.3 expected_results.json

```json
{
  "total": 3,
  "passed": 2,
  "failed": 1,
  "error": 0,
  "pass_rate": 66.7,
  "results": [
    {"test_case_id": "TC-001", "status": "PASSED"},
    {"test_case_id": "TC-002", "status": "PASSED"},
    {"test_case_id": "TC-003", "status": "FAILED", "reason": "温度が範囲外 (75.3℃)"}
  ]
}
```

### 2.6 E2E テスト実装詳細

#### 2.6.1 conftest.py（E2E 専用）

```python
"""E2E テスト専用フィクスチャ"""

import json
from pathlib import Path

import pytest

from src.converter.batch_converter import BatchConverter
from src.converter.openai_converter import ConversionResult
from src.engine.canoe_com import CANoeState
from src.engine.judgment import JudgmentEngine
from src.engine.log_manager import LogManager
from src.engine.test_runner import TestRunner
from src.models.signal_model import SignalRepository
from src.models.test_pattern import TestPattern, TestPatternRepository
from src.parsers.dbc_parser import DBCParser
from src.parsers.ldf_parser import LDFParser
from src.report.excel_report import ExcelReportGenerator


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
E2E_FIXTURES_DIR = FIXTURES_DIR / "e2e"


@pytest.fixture
def sample_dbc_path() -> Path:
    return FIXTURES_DIR / "sample.dbc"


@pytest.fixture
def sample_ldf_path() -> Path:
    return FIXTURES_DIR / "sample.ldf"


@pytest.fixture
def signal_repository(sample_dbc_path, sample_ldf_path) -> SignalRepository:
    """DBC + LDF を読み込んだ SignalRepository"""
    repo = SignalRepository()
    dbc_signals = DBCParser().parse(sample_dbc_path)
    ldf_signals = LDFParser().parse(sample_ldf_path)
    repo.add_signals(dbc_signals)
    repo.add_signals(ldf_signals)
    return repo


@pytest.fixture
def test_patterns() -> list[TestPattern]:
    """テストパターンフィクスチャ"""
    path = E2E_FIXTURES_DIR / "test_patterns.json"
    text = path.read_text(encoding="utf-8")
    data_list = json.loads(text)
    return [TestPattern.from_dict(d) for d in data_list]


@pytest.fixture
def mock_canoe():
    """MockCANoeCOM インスタンス"""
    response_file = E2E_FIXTURES_DIR / "mock_canoe_responses.json"
    return MockCANoeCOM(response_file if response_file.exists() else None)


@pytest.fixture
def mock_converter():
    """MockOpenAIConverter インスタンス"""
    return MockOpenAIConverter()
```

#### 2.6.2 test_full_pipeline.py — 全フェーズ通し E2E

```python
"""全フェーズ通し E2E テスト

Phase 1（信号読込） → Phase 2（パターン作成・変換）
→ Phase 3（テスト実行） → Phase 4（判定・帳票出力）
の一連のワークフローを検証する。
"""


class TestFullPipeline:
    """E2E-N01: 全フェーズ通しテスト"""

    def test_full_workflow(
        self, signal_repository, mock_canoe, mock_converter, tmp_path
    ):
        """DBC/LDF 読込 → パターン作成 → 変換 → 実行 → 判定 → 帳票"""
        # Phase 1: 信号が正しく読み込まれていること
        assert signal_repository.count > 0

        # Phase 2: テストパターン作成・変換
        ...

        # Phase 3: テスト実行
        ...

        # Phase 4: 判定・帳票出力
        ...

    def test_multi_file_mixed(
        self, sample_dbc_path, sample_ldf_path, mock_canoe, tmp_path
    ):
        """E2E-N02: CAN/LIN 混合テスト"""
        ...

    def test_large_batch_execution(self, mock_canoe, tmp_path):
        """E2E-N08: 大量パターン実行"""
        ...
```

#### 2.6.3 test_conversion_flow.py — パターン作成→変換 E2E

```python
"""パターン作成→変換 E2E テスト

Phase 2 のワークフロー:
パターン入力 → 一括変換 → プレビュー → 手動修正 → 確定 → JSON 出力
"""


class TestConversionFlow:
    """E2E-N03: 一括変換→プレビュー→確定"""

    def test_batch_convert_preview_confirm(
        self, test_patterns, mock_converter, tmp_path
    ):
        """10 件一括変換 → プレビュー確認 → 全件確定 → JSON 出力"""
        ...

    def test_partial_failure_handling(self, mock_converter, tmp_path):
        """E2E-E03: 部分失敗時のハンドリング"""
        ...

    def test_manual_edit_after_preview(self, mock_converter, tmp_path):
        """プレビュー後の手動修正 → 確定"""
        ...
```

#### 2.6.4 test_execution_flow.py — 実行→判定→帳票 E2E

```python
"""実行→判定→帳票 E2E テスト

Phase 3→4 のワークフロー:
確定済みパラメータ → TestRunner → JudgmentEngine → ExcelReportGenerator
"""


class TestExecutionFlow:
    """E2E-N04〜N07: テスト実行→判定→帳票"""

    def test_execute_judge_report(self, mock_canoe, tmp_path):
        """確定済み JSON → 実行 → 判定 → Excel 帳票"""
        ...

    def test_all_judgment_types(self, mock_canoe, tmp_path):
        """E2E-N05: 全判定タイプ混合テスト"""
        ...

    def test_result_persistence(self, mock_canoe, tmp_path):
        """E2E-N06: 結果 JSON + ログ CSV の永続化検証"""
        ...

    def test_excel_report_format(self, mock_canoe, tmp_path):
        """E2E-N07: Excel 帳票フォーマット検証"""
        ...
```

#### 2.6.5 test_error_recovery.py — 異常系 E2E

```python
"""異常系・回復 E2E テスト

エラー発生時の適切なハンドリングと復旧を検証する。
"""


class TestFileErrors:
    """E2E-E01: ファイル読込エラー"""

    def test_corrupted_dbc(self, tmp_path):
        """破損 DBC ファイルの読み込み"""
        ...

    def test_empty_ldf(self, tmp_path):
        """空 LDF ファイルの読み込み"""
        ...


class TestConversionErrors:
    """E2E-E02〜E03: AI 変換エラー"""

    def test_all_conversion_failure(self, mock_converter, tmp_path):
        """全件変換失敗"""
        ...

    def test_partial_conversion_failure(self, mock_converter, tmp_path):
        """部分変換失敗"""
        ...


class TestExecutionErrors:
    """E2E-E04〜E07: 実行エラー"""

    def test_canoe_connection_failure(self, tmp_path):
        """CANoe 接続失敗"""
        ...

    def test_canoe_disconnect_during_measurement(self, mock_canoe, tmp_path):
        """測定中の CANoe 切断"""
        ...

    def test_abort_during_execution(self, mock_canoe, tmp_path):
        """実行中断"""
        ...

    def test_invalid_test_pattern(self, mock_canoe, tmp_path):
        """不正テストパターン"""
        ...


class TestReportErrors:
    """E2E-E08: 帳票出力エラー"""

    def test_invalid_output_directory(self, mock_canoe, tmp_path):
        """存在しない出力先"""
        ...
```

---

## 3. UI/UX改善計画（Issue #24）

### 3.1 既存 UI の課題分析

実際のソースコードを読み、以下の課題を特定した。

#### 3.1.1 main_window.py の課題

| # | 課題 | ファイル:行 | 詳細 |
|---|------|-----------|------|
| U01 | メニューのコマンド未接続 | main_window.py:44-57 | 「ファイルを開く」「設定」「バージョン情報」にコマンドハンドラがない |
| U02 | Phase 2 タブが空 | main_window.py:70-71 | Phase 2 フレームにコンテンツなし（プレースホルダも未表示） |
| U03 | Phase 4 タブが「準備中」 | main_window.py:80 | excel_report.py が実装済みだが、GUI 未統合 |
| U04 | キーボードショートカットなし | main_window.py 全体 | アクセラレータキーが一切定義されていない |
| U05 | タブ間データ連携なし | main_window.py 全体 | Phase 1 で読み込んだ信号を Phase 2/3 に渡す仕組みがない |

#### 3.1.2 signal_tab.py の課題

| # | 課題 | ファイル:行 | 詳細 |
|---|------|-----------|------|
| U06 | ファイル読込中の進捗表示なし | signal_tab.py:136-159 | 大きいファイルでもフィードバックなし |
| U07 | エラーメッセージが不親切 | signal_tab.py:134 | `str(e)` のみ。どのファイルで何が問題かが不明瞭 |
| U08 | Treeview 右クリックメニューなし | signal_tab.py:91-97 | コンテキストメニューがない（コピー等） |
| U09 | 信号数の表示なし | signal_tab.py 全体 | 読み込み信号総数がステータスバーに表示されない |

#### 3.1.3 execution_tab.py の課題

| # | 課題 | ファイル:行 | 詳細 |
|---|------|-----------|------|
| U10 | パターン設定が API のみ | execution_tab.py:108-110 | GUI からパターンを設定する手段がない |
| U11 | 実行結果の要約表示なし | execution_tab.py:139 | ログ表示のみ。OK/NG 数などのサマリがない |
| U12 | 帳票出力ボタンなし | execution_tab.py 全体 | Phase 4 の帳票出力機能への導線がない |
| U13 | 失敗テスト再実行なし | execution_tab.py 全体 | NG のテストのみ再実行する機能がない |

#### 3.1.4 signal_selector.py の課題

| # | 課題 | ファイル:行 | 詳細 |
|---|------|-----------|------|
| U14 | コンボボックス初期値が空 | signal_selector.py:55-56 | 信号選択コンボが初期表示時に空。検索実行まで候補が出ない |
| U15 | キーボードで追加不可 | signal_selector.py:60-63 | Enter キーでの追加がサポートされていない |

#### 3.1.5 全体的な課題

| # | 課題 | 詳細 |
|---|------|------|
| U16 | グローバルエラーハンドリング | 未捕捉例外がコンソールに出力されるのみ |
| U17 | ステータスバー未活用 | set_status() が定義されているが、どこからも呼ばれていない |
| U18 | ウィンドウ閉じる確認なし | 実行中にウィンドウを閉じても確認ダイアログが出ない |

### 3.2 改善ポイントリスト（優先度付き）

#### 優先度 P0（必須）

| # | 改善内容 | 対象課題 | 実装方針 |
|---|---------|---------|---------|
| F01 | メニュー「ファイルを開く」を SignalTab に連携 | U01 | `file_menu.add_command(command=self.signal_tab._on_open_file)` |
| F02 | Phase 4 タブに帳票出力 UI を追加 | U03, U12 | 帳票出力ボタン + ファイル保存ダイアログ + 結果要約表示 |
| F03 | エラーメッセージの日本語化・詳細化 | U07 | ファイル名・エラー種別を含む日本語メッセージに改善 |
| F04 | タブ間データ連携の実装 | U05 | SignalRepository と TestPatternRepository を MainWindow で共有 |

#### 優先度 P1（重要）

| # | 改善内容 | 対象課題 | 実装方針 |
|---|---------|---------|---------|
| F05 | キーボードショートカット追加 | U04, U15 | Ctrl+O, Ctrl+Q, Ctrl+Tab 等を bind |
| F06 | ステータスバー活用 | U09, U17 | 信号数、実行状態、最終更新時刻を表示 |
| F07 | 実行結果サマリ表示 | U11 | 実行完了後に OK/NG/ERROR 数をダイアログ表示 |
| F08 | Phase 2 タブにパターン作成 UI 追加 | U02 | SignalSelector + テストパターン入力フォーム |

#### 優先度 P2（改善）

| # | 改善内容 | 対象課題 | 実装方針 |
|---|---------|---------|---------|
| F09 | ファイル読込進捗表示 | U06 | ステータスバー + カーソル変更（wait） |
| F10 | Treeview 右クリックメニュー | U08 | コピー、詳細表示、フィルタの右クリックメニュー |
| F11 | ウィンドウ閉じる確認ダイアログ | U18 | `WM_DELETE_WINDOW` プロトコルハンドラ追加 |
| F12 | コンボボックス初期値の自動設定 | U14 | `__init__` 内で `_update_combo_values()` を呼ぶ |
| F13 | バージョン情報ダイアログ | U01 | アプリ名・バージョン・Python バージョンを表示 |
| F14 | テストパターン読込（JSON）ボタン | U10 | ExecutionTab に「パターン読込」ボタン追加 |

### 3.3 キーボードショートカット一覧

| ショートカット | 機能 | スコープ |
|--------------|------|---------|
| `Ctrl+O` | ファイルを開く | グローバル |
| `Ctrl+Q` | アプリケーション終了 | グローバル |
| `Ctrl+Tab` | 次のタブに移動 | グローバル |
| `Ctrl+Shift+Tab` | 前のタブに移動 | グローバル |
| `Ctrl+F` | 検索フィールドにフォーカス | 信号情報タブ |
| `Ctrl+S` | テストパターン保存（JSON） | テストパターンタブ |
| `F5` | テスト実行開始 | テスト実行タブ |
| `Escape` | テスト中断 / ダイアログ閉じる | テスト実行タブ |
| `Ctrl+E` | Excel 帳票出力 | 結果・帳票タブ |
| `Enter` | 信号追加（コンボボックス選択時） | 信号選択コンポーネント |
| `Delete` | 選択済み信号削除 | 信号選択コンポーネント |

### 3.4 エラーメッセージ改善例

| 改善前 | 改善後 |
|-------|-------|
| `str(e)` (例: "No such file") | `「{ファイル名}」の読み込みに失敗しました。\nファイルが存在するか確認してください。\n\n詳細: {e}` |
| `str(e)` (例: "Invalid DBC") | `「{ファイル名}」は有効な DBC ファイルではありません。\nCANoe で正しく読み込めるファイルを選択してください。\n\n詳細: {e}` |
| `"実行するテストパターンがありません"` | `テスト実行にはテストパターンが必要です。\n「テストパターン作成」タブでパターンを作成するか、\nJSON ファイルからパターンを読み込んでください。` |
| (未処理例外) | `予期しないエラーが発生しました。\nログファイルを確認してください。\n\n詳細: {e}` |

### 3.5 実装設計

#### 3.5.1 キーボードショートカットの実装

```python
# main_window.py に追加

def _bind_shortcuts(self) -> None:
    """キーボードショートカットのバインド"""
    self.root.bind("<Control-o>", lambda e: self.signal_tab._on_open_file())
    self.root.bind("<Control-q>", lambda e: self._on_quit())
    self.root.bind("<Control-Tab>", lambda e: self._next_tab())
    self.root.bind("<Control-Shift-Tab>", lambda e: self._prev_tab())
    self.root.bind("<F5>", lambda e: self._on_run_test())
    self.root.bind("<Escape>", lambda e: self._on_escape())

def _next_tab(self) -> None:
    """次のタブに移動"""
    current = self.notebook.index(self.notebook.select())
    total = self.notebook.index("end")
    self.notebook.select((current + 1) % total)

def _prev_tab(self) -> None:
    """前のタブに移動"""
    current = self.notebook.index(self.notebook.select())
    total = self.notebook.index("end")
    self.notebook.select((current - 1) % total)

def _on_quit(self) -> None:
    """終了確認"""
    if self.execution_tab.is_running:
        from tkinter import messagebox
        if not messagebox.askyesno(
            "確認", "テストが実行中です。終了しますか？"
        ):
            return
    self.root.quit()
```

#### 3.5.2 結果・帳票タブの実装

```python
# src/gui/result_tab.py (新規)

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
        ...

        # 帳票出力ボタン
        export_frame = ttk.Frame(self.parent)
        export_frame.pack(fill=tk.X, padx=5, pady=5)

        self.export_button = ttk.Button(
            export_frame, text="Excel帳票出力", command=self._on_export
        )
        self.export_button.pack(side=tk.LEFT, padx=5)

        # 結果テーブル（Treeview）
        ...

    def set_results(
        self,
        summary: ExecutionSummary,
        judgments: list[JudgmentDetail],
    ) -> None:
        """結果データを設定して表示を更新"""
        self._summary = summary
        self._judgments = judgments
        self._refresh_display()

    def _on_export(self) -> None:
        """Excel 帳票出力"""
        ...
```

---

## 4. ドキュメント構成計画（Issue #25）

### 4.1 取扱説明書（docs/user_guide.md）

エンドユーザー（テストエンジニア）向けの操作手順書。

#### 章立て

```
# CANoe 自動テストツール 取扱説明書

## 1. はじめに
   1.1 本ツールの目的
   1.2 動作環境
   1.3 前提条件

## 2. インストール
   2.1 Python のインストール
   2.2 ツールのインストール
   2.3 依存ライブラリのインストール
   2.4 CANoe の設定確認
   2.5 Azure OpenAI の設定

## 3. 起動と画面構成
   3.1 ツールの起動方法
   3.2 メインウィンドウの構成
   3.3 メニューバー
   3.4 ステータスバー

## 4. 信号情報の読み込み（Phase 1）
   4.1 DBC ファイルの読み込み
   4.2 LDF ファイルの読み込み
   4.3 複数ファイルの同時読み込み
   4.4 信号一覧の検索・ソート
   4.5 信号詳細の確認

## 5. テストパターンの作成（Phase 2）
   5.1 テストパターンの入力
   5.2 信号の選択
   5.3 日本語によるテスト記述
   5.4 一括変換（Azure OpenAI）
   5.5 プレビューと手動修正
   5.6 テストパターンの保存・読込

## 6. テストの実行（Phase 3）
   6.1 CANoe 構成ファイルの設定
   6.2 テスト実行の開始
   6.3 進捗の確認
   6.4 テストの中断
   6.5 実行ログの確認

## 7. 結果の確認と帳票出力（Phase 4）
   7.1 実行結果の確認
   7.2 判定結果の見方
   7.3 Excel 帳票の出力
   7.4 帳票の読み方

## 8. キーボードショートカット
   （ショートカット一覧表 — 3.3 節を参照）

## 9. トラブルシューティング
   9.1 ファイルが読み込めない
   9.2 Azure OpenAI に接続できない
   9.3 CANoe に接続できない
   9.4 テストが失敗する
   9.5 帳票が出力できない

## 10. FAQ
```

### 4.2 開発者向けドキュメント（docs/developer_guide.md）

開発者・メンテナ向けの技術ドキュメント。

#### 章立て

```
# CANoe 自動テストツール 開発者ガイド

## 1. アーキテクチャ概要
   1.1 全体構成図
   1.2 レイヤー構造（GUI / Model / Converter / Engine / Report）
   1.3 データフロー図（Phase 1→2→3→4）

## 2. モジュール間連携
   2.1 Signal → TestPattern → Converter → Runner → Judgment → Report
   2.2 インターフェース一覧（公開API）
   2.3 依存関係図

## 3. 各モジュール詳細
   3.1 models/ — データモデル
   3.2 parsers/ — ファイルパーサー
   3.3 converter/ — AI 変換エンジン
   3.4 engine/ — テスト実行エンジン
   3.5 report/ — 帳票生成
   3.6 gui/ — ユーザーインターフェース

## 4. テスト
   4.1 テスト構成（unit / integration / e2e）
   4.2 モック戦略
   4.3 テスト実行方法
   4.4 カバレッジの確認

## 5. 開発環境セットアップ
   5.1 リポジトリのクローン
   5.2 仮想環境の構築
   5.3 依存ライブラリのインストール
   5.4 IDE の設定（VSCode / PyCharm）

## 6. コーディング規約
   6.1 PEP 8 + ruff
   6.2 型ヒント（mypy strict）
   6.3 docstring（Google Style）
   6.4 命名規則

## 7. CI/CD
   7.1 GitHub Actions 設定
   7.2 テストマトリックス（Python 3.10/3.11/3.12）
   7.3 カバレッジレポート

## 8. 拡張ガイド
   8.1 新しいパーサーの追加方法
   8.2 新しい判定タイプの追加方法
   8.3 LLM プロバイダーの差し替え方法
```

### 4.3 アーキテクチャ図（開発者ガイド用）

```
┌──────────────────────────────────────────────────────────────────┐
│                            GUI Layer                             │
│  ┌────────────┐  ┌──────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ SignalTab   │  │ Pattern  │  │ ExecutionTab │  │ ResultTab │ │
│  │ (Phase 1)  │  │ Tab (Ph2)│  │ (Phase 3)    │  │ (Phase 4) │ │
│  └─────┬──────┘  └────┬─────┘  └──────┬───────┘  └─────┬─────┘ │
│        │              │               │                │        │
├────────┼──────────────┼───────────────┼────────────────┼────────┤
│        ▼              ▼               ▼                ▼        │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                        Model Layer                         │  │
│  │  SignalRepository ←→ TestPatternRepository                 │  │
│  │  SignalInfo              TestPattern                       │  │
│  └──────┬──────────────────────┬──────────────────────────────┘  │
│         │                      │                                  │
│         ▼                      ▼                                  │
│  ┌─────────────┐    ┌──────────────────────┐                     │
│  │  Parsers     │    │    Converter Layer    │                    │
│  │  DBCParser   │    │  OpenAIConverter      │                    │
│  │  LDFParser   │    │  BatchConverter       │                    │
│  └─────────────┘    └──────────┬───────────┘                     │
│                                │                                  │
│                                ▼                                  │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │                        Engine Layer                           ││
│  │  CANoeCOMWrapper → TestRunner → LogManager → JudgmentEngine ││
│  └───────────────────────────────────────────┬──────────────────┘│
│                                              │                    │
│                                              ▼                    │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │                        Report Layer                           ││
│  │                    ExcelReportGenerator                       ││
│  └──────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘
```

### 4.4 README.md 更新内容

現在の README.md に以下のセクションを追加・更新する。

| セクション | 更新内容 |
|-----------|---------|
| **インストール手順** | `pip install -e ".[dev]"` のステップバイステップガイド追加 |
| **クイックスタート** | 「5 分で始める」セクション追加（ファイル読み込み → テスト実行の最短パス） |
| **スクリーンショット** | 各タブの画面キャプチャを追加（Phase 5 UI 改善後） |
| **機能一覧** | Phase 1〜4 の全機能を表形式でリスト |
| **開発者向け情報** | テスト実行方法、コーディング規約へのリンク |
| **ライセンス** | MIT License |

---

## 5. 新規ファイル・変更ファイル一覧

### 5.1 新規ファイル

| ファイル | Issue | 説明 |
|---------|-------|------|
| `tests/e2e/__init__.py` | #23 | E2E テストパッケージ |
| `tests/e2e/conftest.py` | #23 | E2E 専用フィクスチャ（MockCANoeCOM, MockOpenAIConverter） |
| `tests/e2e/test_full_pipeline.py` | #23 | 全フェーズ通し E2E テスト |
| `tests/e2e/test_conversion_flow.py` | #23 | パターン作成→変換 E2E テスト |
| `tests/e2e/test_execution_flow.py` | #23 | 実行→判定→帳票 E2E テスト |
| `tests/e2e/test_error_recovery.py` | #23 | 異常系・回復 E2E テスト |
| `tests/fixtures/e2e/test_patterns.json` | #23 | テストパターンフィクスチャ |
| `tests/fixtures/e2e/confirmed_params.json` | #23 | 変換確定済みパラメータ |
| `tests/fixtures/e2e/expected_results.json` | #23 | 期待結果データ |
| `tests/fixtures/e2e/mock_canoe_responses.json` | #23 | CANoe モックレスポンス定義 |
| `tests/fixtures/error/corrupted.dbc` | #23 | 破損 DBC ファイル |
| `tests/fixtures/error/invalid_pattern.json` | #23 | 不正テストパターン |
| `src/gui/result_tab.py` | #24 | 結果・帳票タブ（Phase 4 GUI） |
| `docs/user_guide.md` | #25 | 取扱説明書 |
| `docs/developer_guide.md` | #25 | 開発者ガイド |

### 5.2 変更ファイル

| ファイル | Issue | 変更内容 |
|---------|-------|---------|
| `src/gui/main_window.py` | #24 | キーボードショートカット、メニュー接続、タブ間連携、終了確認 |
| `src/gui/signal_tab.py` | #24 | エラーメッセージ改善、右クリックメニュー、進捗表示 |
| `src/gui/execution_tab.py` | #24 | パターン読込ボタン、結果サマリ表示、帳票出力連携 |
| `src/gui/signal_selector.py` | #24 | コンボ初期値設定、Enter キー対応 |
| `README.md` | #25 | インストール手順、クイックスタート、機能一覧 |
| `tests/conftest.py` | #23 | E2E テスト用の追加モック設定 |

---

## 6. テスト方針

### 6.1 E2E テストの実行方法

```bash
# E2E テストのみ実行
pytest tests/e2e/ -v

# 全テスト実行（unit + integration + e2e）
pytest --cov=src --cov-report=term-missing

# E2E テストをマーカーで選択
pytest -m e2e -v
```

### 6.2 pytest マーカー設計

```python
# pyproject.toml に追加
[tool.pytest.ini_options]
markers = [
    "e2e: E2E テスト（Phase 5）",
    "slow: 実行時間が長いテスト",
]
```

### 6.3 CI 環境での考慮事項

| 環境 | 対応 |
|------|------|
| **Linux CI（GitHub Actions）** | tkinter モック（既存 conftest.py）、CANoe モック、OpenAI モック |
| **Windows ローカル** | CANoe 実機テスト可能（オプション: `--canoe-real` フラグ） |
| **Python バージョン** | 3.10 / 3.11 / 3.12 マトリックス（既存 CI 設定維持） |

### 6.4 カバレッジ目標

| テスト種別 | 目標 |
|-----------|------|
| Phase 5 E2E テスト | 全シナリオ（正常 8 + 異常 8 = 16 シナリオ）をカバー |
| UI 改善部分のテスト | 80% 以上 |
| Phase 5 追加コード全体 | 85% 以上 |
| プロジェクト全体 | 85% 以上を維持 |

### 6.5 E2E テスト設計のルール

| ルール | 理由 |
|-------|------|
| 各テストは独立して実行可能 | テスト間の依存を排除 |
| tmp_path を使用し、ファイルシステムを汚さない | CI 環境のクリーン性確保 |
| 全外部依存（CANoe, OpenAI）はモック | CI で確実に動作 |
| テストデータは JSON フィクスチャで管理 | データの再利用性とメンテナンス性 |
| 実行時間は 1 テストあたり 5 秒以内 | CI 全体の実行時間を適正に保つ |

---

## 7. 実装順序（推奨）

### 7.1 依存関係

```
Issue #23 (E2E テスト)
    │
    ├── Step 1: テストデータ設計（フィクスチャ作成）
    ├── Step 2: MockCANoeCOM + MockOpenAIConverter 実装
    ├── Step 3: E2E テストケース実装
    │   ├── test_full_pipeline.py
    │   ├── test_conversion_flow.py
    │   ├── test_execution_flow.py
    │   └── test_error_recovery.py
    └── Step 4: CI 設定更新（e2e マーカー追加）

Issue #24 (UI 改善) ← #23 と並列実行可能
    │
    ├── Step 1: キーボードショートカット実装 (main_window.py)
    ├── Step 2: エラーメッセージ改善 (signal_tab.py)
    ├── Step 3: ResultTab 新規作成 (result_tab.py)
    ├── Step 4: タブ間データ連携 (main_window.py)
    └── Step 5: 細部改善（右クリックメニュー、コンボ初期値等）

Issue #25 (ドキュメント) ← #24 完了後に開始推奨
    │
    ├── Step 1: 取扱説明書（docs/user_guide.md）
    ├── Step 2: 開発者ガイド（docs/developer_guide.md）
    └── Step 3: README.md 更新
```

### 7.2 足軽配分（推奨）

```
足軽A: #23 E2E テスト（フィクスチャ → モック → テスト実装）
足軽B: #24 UI 改善（ショートカット → エラーメッセージ → ResultTab）
足軽C: #25 ドキュメント（取扱説明書 → 開発者ガイド → README）
```

**クリティカルパス:** `#23 Step 1-2` → `#23 Step 3-4` (E2E テストの基盤が先)

**並列実行可能:** #23 と #24 は独立して並列実行可能。#25 は #24 の UI 改善後にスクリーンショットを含めるため、#24 完了後が望ましい。

---

*本文書は Phase 5 設計書 Ver.1.0 です。実装中に判明した設計変更は版管理のうえ更新してください。*

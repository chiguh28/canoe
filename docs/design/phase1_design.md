# Phase 1: 基盤構築 — 設計書

**Version:** 1.0　|　**作成日:** 2026-03-07　|　**対応Issue:** #1, #6〜#11

---

## 1. ディレクトリ構成

```
canoe/                          # リポジトリルート
├── src/                        # メインソースコード
│   ├── __init__.py
│   ├── main.py                 # エントリーポイント (python -m src で起動)
│   ├── models/                 # データモデル
│   │   ├── __init__.py
│   │   └── signal_model.py     # SignalInfo, MessageInfo データクラス
│   ├── parsers/                # ファイルパーサー
│   │   ├── __init__.py
│   │   ├── base.py             # BaseParser 抽象基底クラス
│   │   ├── dbc_parser.py       # DBC (.dbc) パーサー
│   │   └── ldf_parser.py       # LDF (.ldf) パーサー
│   └── gui/                    # GUI コンポーネント
│       ├── __init__.py
│       ├── main_window.py      # メインウィンドウ
│       └── signal_tab.py       # 信号情報タブ（ファイル読込・信号一覧表示）
├── tests/                      # テスト
│   ├── __init__.py
│   ├── conftest.py             # 共通フィクスチャ
│   ├── fixtures/               # テストデータ
│   │   ├── sample.dbc          # サンプル DBC ファイル
│   │   └── sample.ldf          # サンプル LDF ファイル
│   ├── unit/                   # ユニットテスト
│   │   ├── __init__.py
│   │   ├── test_signal_model.py
│   │   ├── test_dbc_parser.py
│   │   └── test_ldf_parser.py
│   └── integration/            # 統合テスト
│       ├── __init__.py
│       └── test_parser_to_gui.py
├── docs/                       # ドキュメント
│   ├── requirements.md         # 要件定義書
│   └── design/                 # 設計書
│       └── phase1_design.md    # 本ファイル
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions CI
├── pyproject.toml              # プロジェクト設定（既存）
├── README.md                   # プロジェクト説明（既存）
└── .gitignore                  # Git除外設定（既存）
```

### pyproject.toml 更新事項

既存の `pyproject.toml` を以下の点で更新する:

```toml
[tool.setuptools.packages.find]
where = ["."]
include = ["src*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]  # src モジュールを解決するために追加
```

---

## 2. モジュール構成図

```
┌──────────────────────────────────────────────────┐
│                  GUI Layer                        │
│  ┌────────────────────┐  ┌─────────────────────┐ │
│  │   MainWindow       │  │    SignalTab         │ │
│  │  (main_window.py)  │  │  (signal_tab.py)    │ │
│  │  - メニューバー     │  │  - ファイル選択     │ │
│  │  - タブ管理         │  │  - 信号一覧表示     │ │
│  │  - ステータスバー   │  │  - 検索フィルタ     │ │
│  └────────────────────┘  └──────┬──────────────┘ │
│                                  │                │
│           list[SignalInfo]       │                │
│                                  ▼                │
│  ┌──────────────────────────────────────────────┐ │
│  │              Model Layer                      │ │
│  │  ┌──────────────────────────────────────────┐ │ │
│  │  │  SignalInfo (signal_model.py)             │ │ │
│  │  │  - DBC/LDF 共通の正規化データモデル      │ │ │
│  │  │  - MessageInfo                            │ │ │
│  │  │  - SignalRepository (検索・フィルタ)      │ │ │
│  │  └──────────────────────────────────────────┘ │ │
│  └──────────────────────────────────────────────┘ │
│                       ▲                           │
│           list[SignalInfo]                        │
│                       │                           │
│  ┌──────────────────────────────────────────────┐ │
│  │              Parser Layer                     │ │
│  │  ┌───────────────┐  ┌──────────────────────┐ │ │
│  │  │  DbcParser    │  │  LdfParser           │ │ │
│  │  │ (dbc_parser)  │  │ (ldf_parser)         │ │ │
│  │  │  cantools     │  │  ldfparser           │ │ │
│  │  └───────┬───────┘  └──────────┬───────────┘ │ │
│  │          │ BaseParser           │             │ │
│  │          └──────────┬───────────┘             │ │
│  │                     │                         │ │
│  └─────────────────────┼─────────────────────────┘ │
│                        │                           │
│                   .dbc / .ldf ファイル              │
└──────────────────────────────────────────────────┘
```

### データフロー

```
.dbc/.ldf ファイル
    │
    ▼
Parser (DbcParser / LdfParser)
    │  parse() → list[SignalInfo]
    ▼
SignalRepository
    │  add_signals() / search() / filter()
    ▼
SignalTab (GUI)
    │  Treeview に表示
    ▼
ユーザー操作（閲覧・検索・選択）
```

---

## 3. クラス設計

### 3.1 SignalInfo データクラス（src/models/signal_model.py）

```python
from dataclasses import dataclass, field
from enum import Enum


class Protocol(Enum):
    """通信プロトコル種別"""
    CAN = "CAN"
    LIN = "LIN"


@dataclass(frozen=True)
class SignalInfo:
    """DBC/LDF 共通の正規化信号情報モデル

    要件定義書 3.1.1 に準拠。
    DBC (CAN) と LDF (LIN) の異なるフォーマットから取得した
    信号情報を統一的に扱うためのデータクラス。
    """
    signal_name: str           # 信号名
    message_name: str          # メッセージ名（LDF: フレーム名）
    message_id: int            # メッセージID（LDF: フレームID）
    data_type: str             # データ型（"unsigned", "signed", "float" 等）
    min_value: float           # 最小値（物理値）
    max_value: float           # 最大値（物理値）
    unit: str                  # 物理単位（"rpm", "km/h", "" 等）
    node_info: str             # 送受信ノード情報（"ECU1 -> ECU2" 形式）
    source_file: str           # 元ファイルパス
    protocol: Protocol         # CAN or LIN

    @property
    def display_name(self) -> str:
        """GUI表示用の名称（メッセージ名.信号名）"""
        return f"{self.message_name}.{self.signal_name}"

    def matches_query(self, query: str) -> bool:
        """検索クエリに一致するか判定"""
        q = query.lower()
        return (
            q in self.signal_name.lower()
            or q in self.message_name.lower()
        )


@dataclass(frozen=True)
class MessageInfo:
    """メッセージ/フレーム情報"""
    name: str                  # メッセージ名
    message_id: int            # メッセージID
    sender_node: str           # 送信ノード
    signals: tuple[SignalInfo, ...] = field(default_factory=tuple)
    source_file: str = ""
    protocol: Protocol = Protocol.CAN
```

### 3.2 SignalRepository（src/models/signal_model.py 内）

```python
class SignalRepository:
    """信号情報のインメモリリポジトリ

    セッション中に読み込んだ全信号情報を保持し、
    検索・フィルタ機能を提供する。
    （要件定義書 3.1.1「データ保持」に準拠）
    """

    def __init__(self) -> None:
        self._signals: list[SignalInfo] = []

    def add_signals(self, signals: list[SignalInfo]) -> None:
        """信号情報を追加"""
        self._signals.extend(signals)

    def clear(self) -> None:
        """全信号情報をクリア"""
        self._signals.clear()

    def get_all(self) -> list[SignalInfo]:
        """全信号情報を取得"""
        return list(self._signals)

    def search(self, query: str) -> list[SignalInfo]:
        """信号名・メッセージ名で検索"""
        if not query:
            return self.get_all()
        return [s for s in self._signals if s.matches_query(query)]

    def filter_by_protocol(self, protocol: Protocol) -> list[SignalInfo]:
        """プロトコル（CAN/LIN）でフィルタ"""
        return [s for s in self._signals if s.protocol == protocol]

    def get_by_message(self, message_name: str) -> list[SignalInfo]:
        """メッセージ名で信号を取得"""
        return [s for s in self._signals if s.message_name == message_name]

    @property
    def count(self) -> int:
        """登録信号数"""
        return len(self._signals)
```

### 3.3 BaseParser 抽象基底クラス（src/parsers/base.py）

```python
from abc import ABC, abstractmethod
from pathlib import Path


class BaseParser(ABC):
    """パーサー共通インターフェース"""

    @abstractmethod
    def parse(self, filepath: str | Path) -> list[SignalInfo]:
        """ファイルを解析し、SignalInfo のリストを返す

        Args:
            filepath: 解析対象ファイルのパス

        Returns:
            解析結果の SignalInfo リスト

        Raises:
            FileNotFoundError: ファイルが存在しない場合
            ParseError: ファイルフォーマットが不正な場合
        """
        ...

    @abstractmethod
    def can_parse(self, filepath: str | Path) -> bool:
        """指定ファイルを解析可能か判定"""
        ...


class ParseError(Exception):
    """パーサーエラー（ファイルフォーマット不正等）"""
    pass
```

### 3.4 DbcParser（src/parsers/dbc_parser.py）

```python
import cantools
from pathlib import Path

from src.models.signal_model import SignalInfo, Protocol
from src.parsers.base import BaseParser, ParseError


class DbcParser(BaseParser):
    """CANdb (.dbc) ファイルパーサー

    cantools ライブラリを使用して DBC ファイルを解析し、
    SignalInfo の統一フォーマットに変換する。
    """

    def parse(self, filepath: str | Path) -> list[SignalInfo]:
        """DBC ファイルを解析し SignalInfo リストを返す

        Args:
            filepath: .dbc ファイルのパス

        Returns:
            解析結果の SignalInfo リスト

        Raises:
            FileNotFoundError: ファイルが存在しない場合
            ParseError: DBC フォーマットが不正な場合
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"DBC ファイルが見つかりません: {path}")

        try:
            db = cantools.database.load_file(str(path))
        except Exception as e:
            raise ParseError(f"DBC ファイルの解析に失敗しました: {path} — {e}") from e

        signals: list[SignalInfo] = []
        for message in db.messages:
            sender = message.senders[0] if message.senders else ""
            for signal in message.signals:
                receivers = ", ".join(signal.receivers) if signal.receivers else ""
                node_info = f"{sender} -> {receivers}" if sender else receivers

                signals.append(SignalInfo(
                    signal_name=signal.name,
                    message_name=message.name,
                    message_id=message.frame_id,
                    data_type=self._resolve_type(signal),
                    min_value=float(signal.minimum or 0),
                    max_value=float(signal.maximum or 0),
                    unit=signal.unit or "",
                    node_info=node_info,
                    source_file=str(path),
                    protocol=Protocol.CAN,
                ))
        return signals

    def can_parse(self, filepath: str | Path) -> bool:
        """拡張子が .dbc であるか判定"""
        return Path(filepath).suffix.lower() == ".dbc"

    @staticmethod
    def _resolve_type(signal: cantools.database.Signal) -> str:
        """cantools の Signal から データ型文字列を解決"""
        if signal.is_float:
            return "float"
        if not signal.is_signed:
            return "unsigned"
        return "signed"
```

### 3.5 LdfParser（src/parsers/ldf_parser.py）

```python
import ldfparser
from pathlib import Path

from src.models.signal_model import SignalInfo, Protocol
from src.parsers.base import BaseParser, ParseError


class LdfParser(BaseParser):
    """LDF (.ldf) ファイルパーサー

    ldfparser ライブラリを使用して LDF ファイルを解析し、
    SignalInfo の統一フォーマットに変換する。
    """

    def parse(self, filepath: str | Path) -> list[SignalInfo]:
        """LDF ファイルを解析し SignalInfo リストを返す

        Args:
            filepath: .ldf ファイルのパス

        Returns:
            解析結果の SignalInfo リスト

        Raises:
            FileNotFoundError: ファイルが存在しない場合
            ParseError: LDF フォーマットが不正な場合
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"LDF ファイルが見つかりません: {path}")

        try:
            ldf = ldfparser.parse_ldf(str(path))
        except Exception as e:
            raise ParseError(f"LDF ファイルの解析に失敗しました: {path} — {e}") from e

        signals: list[SignalInfo] = []
        for frame in ldf.frames:
            publisher = frame.publisher.name if frame.publisher else ""
            for signal in frame.signals:
                subscribers = ", ".join(
                    s.name for s in getattr(signal, 'subscribers', [])
                )
                node_info = f"{publisher} -> {subscribers}" if publisher else ""

                signals.append(SignalInfo(
                    signal_name=signal.name,
                    message_name=frame.name,
                    message_id=frame.frame_id,
                    data_type=self._resolve_type(signal),
                    min_value=float(getattr(signal, 'minimum', 0) or 0),
                    max_value=float(getattr(signal, 'maximum', 0) or 0),
                    unit=getattr(signal, 'unit', "") or "",
                    node_info=node_info,
                    source_file=str(path),
                    protocol=Protocol.LIN,
                ))
        return signals

    def can_parse(self, filepath: str | Path) -> bool:
        """拡張子が .ldf であるか判定"""
        return Path(filepath).suffix.lower() == ".ldf"

    @staticmethod
    def _resolve_type(signal: object) -> str:
        """ldfparser の Signal からデータ型文字列を解決"""
        width = getattr(signal, 'width', 8)
        if width <= 1:
            return "boolean"
        return "unsigned"
```

### 3.6 MainWindow（src/gui/main_window.py）

```python
import tkinter as tk
from tkinter import ttk


class MainWindow:
    """メインウィンドウ

    アプリケーション全体のフレームを管理する。
    タブ構成で各フェーズの機能を統合する。
    """

    TITLE = "CANoe 自動テストツール"
    DEFAULT_WIDTH = 1024
    DEFAULT_HEIGHT = 768

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(self.TITLE)
        self.root.geometry(f"{self.DEFAULT_WIDTH}x{self.DEFAULT_HEIGHT}")
        self.root.minsize(800, 600)

        self._create_menu()
        self._create_notebook()
        self._create_statusbar()

    def _create_menu(self) -> None:
        """メニューバー作成"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # ファイルメニュー
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="ファイルを開く...")
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.root.quit)
        menubar.add_cascade(label="ファイル", menu=file_menu)

        # ツールメニュー
        tool_menu = tk.Menu(menubar, tearoff=0)
        tool_menu.add_command(label="設定...")
        menubar.add_cascade(label="ツール", menu=tool_menu)

        # ヘルプメニュー
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="バージョン情報")
        menubar.add_cascade(label="ヘルプ", menu=help_menu)

    def _create_notebook(self) -> None:
        """タブ (Notebook) 作成"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Phase 1: 信号情報タブ（SignalTab を配置）
        self.signal_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.signal_frame, text="信号情報")

        # Phase 2: テストパターンタブ（プレースホルダ）
        ph2_frame = ttk.Frame(self.notebook)
        ttk.Label(ph2_frame, text="準備中（Phase 2 で実装）").pack(pady=50)
        self.notebook.add(ph2_frame, text="テストパターン作成")

        # Phase 3: テスト実行タブ（プレースホルダ）
        ph3_frame = ttk.Frame(self.notebook)
        ttk.Label(ph3_frame, text="準備中（Phase 3 で実装）").pack(pady=50)
        self.notebook.add(ph3_frame, text="テスト実行")

        # Phase 4: 結果・帳票タブ（プレースホルダ）
        ph4_frame = ttk.Frame(self.notebook)
        ttk.Label(ph4_frame, text="準備中（Phase 4 で実装）").pack(pady=50)
        self.notebook.add(ph4_frame, text="結果・帳票")

    def _create_statusbar(self) -> None:
        """ステータスバー作成"""
        self.statusbar = ttk.Label(
            self.root, text="準備完了", relief=tk.SUNKEN, anchor=tk.W
        )
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

    def set_status(self, message: str) -> None:
        """ステータスバーのメッセージを更新"""
        self.statusbar.config(text=message)

    def run(self) -> None:
        """メインループ開始"""
        self.root.mainloop()
```

### 3.7 SignalTab（src/gui/signal_tab.py）

```python
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from src.models.signal_model import SignalInfo, SignalRepository
from src.parsers.dbc_parser import DbcParser
from src.parsers.ldf_parser import LdfParser


class SignalTab:
    """信号情報タブ

    DBC/LDF ファイルの読み込みと信号一覧表示を担当する。
    """

    COLUMNS = (
        ("signal_name", "信号名", 150),
        ("message_name", "メッセージ名", 150),
        ("message_id", "メッセージID", 100),
        ("data_type", "データ型", 80),
        ("min_value", "最小値", 80),
        ("max_value", "最大値", 80),
        ("unit", "単位", 60),
        ("protocol", "プロトコル", 80),
    )

    def __init__(self, parent: ttk.Frame, repository: SignalRepository,
                 on_status: callable) -> None:
        self.parent = parent
        self.repository = repository
        self.on_status = on_status  # ステータスバー更新コールバック
        self._dbc_parser = DbcParser()
        self._ldf_parser = LdfParser()

        self._create_toolbar()
        self._create_search()
        self._create_treeview()

    def _create_toolbar(self) -> None:
        """ツールバー（ファイル読込ボタン）"""
        toolbar = ttk.Frame(self.parent)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(
            toolbar, text="ファイルを開く",
            command=self._on_open_file
        ).pack(side=tk.LEFT, padx=2)

    def _create_search(self) -> None:
        """検索バー"""
        search_frame = ttk.Frame(self.parent)
        search_frame.pack(fill=tk.X, padx=5)

        ttk.Label(search_frame, text="検索:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search)
        ttk.Entry(
            search_frame, textvariable=self.search_var
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

    def _create_treeview(self) -> None:
        """信号一覧 Treeview"""
        tree_frame = ttk.Frame(self.parent)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        col_ids = [c[0] for c in self.COLUMNS]
        self.tree = ttk.Treeview(tree_frame, columns=col_ids, show="headings")

        for col_id, col_name, col_width in self.COLUMNS:
            self.tree.heading(col_id, text=col_name,
                            command=lambda c=col_id: self._sort_by(c))
            self.tree.column(col_id, width=col_width)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                                  command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _on_open_file(self) -> None:
        """ファイル選択ダイアログ → パース → 表示"""
        filepaths = filedialog.askopenfilenames(
            title="信号定義ファイルを選択",
            filetypes=[
                ("CANdb/LDF ファイル", "*.dbc *.ldf"),
                ("DBC ファイル", "*.dbc"),
                ("LDF ファイル", "*.ldf"),
                ("すべてのファイル", "*.*"),
            ]
        )
        if not filepaths:
            return

        for fp in filepaths:
            self._load_file(fp)

        self._refresh_treeview()
        self.on_status(f"{self.repository.count} 個の信号を読み込みました")

    def _load_file(self, filepath: str) -> None:
        """ファイルを解析して repository に追加"""
        path = Path(filepath)
        try:
            if self._dbc_parser.can_parse(path):
                signals = self._dbc_parser.parse(path)
            elif self._ldf_parser.can_parse(path):
                signals = self._ldf_parser.parse(path)
            else:
                messagebox.showerror("エラー",
                    f"未対応のファイル形式です: {path.suffix}")
                return
            self.repository.add_signals(signals)
        except (FileNotFoundError, Exception) as e:
            messagebox.showerror("読み込みエラー", str(e))

    def _refresh_treeview(self, signals: list[SignalInfo] | None = None) -> None:
        """Treeview を更新"""
        self.tree.delete(*self.tree.get_children())
        display = signals if signals is not None else self.repository.get_all()
        for s in display:
            self.tree.insert("", tk.END, values=(
                s.signal_name, s.message_name, hex(s.message_id),
                s.data_type, s.min_value, s.max_value,
                s.unit, s.protocol.value,
            ))

    def _on_search(self, *args: object) -> None:
        """検索ボックスの入力に応じて Treeview をフィルタ"""
        query = self.search_var.get()
        filtered = self.repository.search(query)
        self._refresh_treeview(filtered)

    def _sort_by(self, column: str) -> None:
        """列ヘッダクリックでソート"""
        items = list(self.tree.get_children())
        col_index = [c[0] for c in self.COLUMNS].index(column)
        items.sort(key=lambda item: self.tree.item(item)["values"][col_index])
        for i, item in enumerate(items):
            self.tree.move(item, "", i)
```

---

## 4. インターフェース定義

### 4.1 Parser → Model

全パーサーは `BaseParser` を継承し、統一インターフェースを提供する:

```
BaseParser.parse(filepath: str | Path) -> list[SignalInfo]
BaseParser.can_parse(filepath: str | Path) -> bool
```

- 入力: ファイルパス（str または Path）
- 出力: `list[SignalInfo]`（統一フォーマット）
- 例外: `FileNotFoundError`（ファイル不存在）, `ParseError`（フォーマット不正）

### 4.2 GUI → Parser

GUI 層はパーサーを直接使用する（SignalTab 内で統合）:

```
SignalTab._load_file(filepath: str) -> None
    内部で:
    1. 拡張子判定 (can_parse)
    2. 適切なパーサーで parse()
    3. 結果を SignalRepository に add_signals()
```

### 4.3 GUI → Model (SignalRepository)

```
SignalRepository.add_signals(signals: list[SignalInfo]) -> None
SignalRepository.get_all() -> list[SignalInfo]
SignalRepository.search(query: str) -> list[SignalInfo]
SignalRepository.filter_by_protocol(protocol: Protocol) -> list[SignalInfo]
SignalRepository.get_by_message(message_name: str) -> list[SignalInfo]
SignalRepository.count -> int
```

### 4.4 エラーハンドリング方針

| 層 | エラー種別 | 処理 |
|----|-----------|------|
| Parser | ファイル不存在 | `FileNotFoundError` を送出 |
| Parser | フォーマット不正 | `ParseError` を送出 |
| GUI | Parser例外 | `messagebox.showerror()` で日本語エラー表示 |
| GUI | 未対応拡張子 | `messagebox.showerror()` で通知 |
| Model | なし | Model層は例外を送出しない（入力はParser経由で検証済み） |

---

## 5. テスト方針

### 5.1 TDD プロセス

全実装は TDD（テスト駆動開発）で進める:

```
Red:   テストを書く → 失敗を確認
Green: 最小限の実装でテストを通す
Refactor: コードを整理（テストは引き続きパス）
```

### 5.2 テスト構成

| テスト種別 | ディレクトリ | 対象 | 実行タイミング |
|-----------|-------------|------|--------------|
| ユニットテスト | `tests/unit/` | 各クラス・関数の単体動作 | 常時（CI + ローカル） |
| 統合テスト | `tests/integration/` | パーサー→モデル→GUI連携 | CI + ローカル |

### 5.3 ユニットテスト詳細

#### test_signal_model.py（Issue #9 対応）

```python
class TestSignalInfo:
    """SignalInfo データクラスのテスト"""
    def test_create_can_signal(self): ...       # CAN信号の生成
    def test_create_lin_signal(self): ...       # LIN信号の生成
    def test_display_name(self): ...            # "メッセージ名.信号名" 形式
    def test_matches_query_signal_name(self): ... # 信号名で検索ヒット
    def test_matches_query_message_name(self): ... # メッセージ名で検索ヒット
    def test_matches_query_case_insensitive(self): ... # 大文字小文字無視
    def test_matches_query_no_match(self): ...  # 検索不一致

class TestSignalRepository:
    """SignalRepository のテスト"""
    def test_add_and_get_all(self): ...         # 追加・全件取得
    def test_search(self): ...                  # 検索
    def test_filter_by_protocol(self): ...      # プロトコルフィルタ
    def test_get_by_message(self): ...          # メッセージ単位取得
    def test_count(self): ...                   # 件数
    def test_clear(self): ...                   # クリア
    def test_empty_search_returns_all(self): ... # 空検索は全件返却
```

#### test_dbc_parser.py（Issue #7 対応）

```python
class TestDbcParser:
    """DBC パーサーのテスト"""
    def test_parse_valid_dbc(self): ...         # 正常系: 有効なDBCファイル
    def test_parse_signals_count(self): ...     # 信号数の検証
    def test_signal_attributes(self): ...       # 各属性値の検証
    def test_parse_multiple_messages(self): ... # 複数メッセージ
    def test_parse_file_not_found(self): ...    # ファイル不存在
    def test_parse_invalid_format(self): ...    # 不正フォーマット
    def test_can_parse_dbc(self): ...           # .dbc は True
    def test_can_parse_non_dbc(self): ...       # .ldf は False
    def test_protocol_is_can(self): ...         # プロトコルが CAN
```

#### test_ldf_parser.py（Issue #8 対応）

```python
class TestLdfParser:
    """LDF パーサーのテスト"""
    def test_parse_valid_ldf(self): ...         # 正常系: 有効なLDFファイル
    def test_parse_signals_count(self): ...     # 信号数の検証
    def test_signal_attributes(self): ...       # 各属性値の検証
    def test_parse_file_not_found(self): ...    # ファイル不存在
    def test_parse_invalid_format(self): ...    # 不正フォーマット
    def test_can_parse_ldf(self): ...           # .ldf は True
    def test_can_parse_non_ldf(self): ...       # .dbc は False
    def test_protocol_is_lin(self): ...         # プロトコルが LIN
```

### 5.4 統合テスト詳細

#### test_parser_to_gui.py（Issue #11 対応）

```python
class TestParserToModelIntegration:
    """パーサー → モデル統合テスト"""
    def test_dbc_to_repository(self): ...       # DBC → SignalRepository
    def test_ldf_to_repository(self): ...       # LDF → SignalRepository
    def test_mixed_protocols(self): ...         # DBC + LDF 混在
    def test_search_across_protocols(self): ... # 混在環境での検索
```

### 5.5 テストデータ（tests/fixtures/）

| ファイル | 内容 | 用途 |
|---------|------|------|
| `sample.dbc` | 2メッセージ・5信号程度の最小DBCファイル | DBC パーサーテスト |
| `sample.ldf` | 2フレーム・4信号程度の最小LDFファイル | LDF パーサーテスト |
| `empty.dbc` | 空のDBCファイル | エッジケーステスト |
| `invalid.txt` | 不正なフォーマットファイル | 異常系テスト |

### 5.6 カバレッジ目標

| モジュール | 目標カバレッジ |
|-----------|--------------|
| `src/models/` | 95% 以上 |
| `src/parsers/` | 90% 以上 |
| `src/gui/` | 70% 以上（GUI操作はヘッドレス環境で制限あり） |
| 全体 | 85% 以上 |

---

## 6. 依存ライブラリ

| ライブラリ | バージョン | 用途 | Phase |
|-----------|-----------|------|-------|
| cantools | >= 39.0.0 | DBC (.dbc) ファイル解析 | 1 |
| ldfparser | >= 0.24.0 | LDF (.ldf) ファイル解析 | 1 |
| tkinter | 標準ライブラリ | GUI フレームワーク | 1 |
| pytest | >= 8.0.0 | テストフレームワーク | 1 |
| pytest-cov | >= 4.1.0 | カバレッジ計測 | 1 |
| ruff | >= 0.2.0 | Linter + Formatter | 1 |
| mypy | >= 1.8.0 | 型チェック | 1 |
| openpyxl | >= 3.1.0 | Excel 帳票出力 | 4 |
| pywin32 | >= 306 | CANoe COM API 連携 | 3 |

### GUI フレームワーク選定理由

要件定義書では tkinter / PyQt5 が候補として挙げられている。**tkinter を推奨**する:

| 観点 | tkinter | PyQt5 |
|------|---------|-------|
| ライセンス | PSF License（制約なし） | GPL v3（商用制約あり） |
| 依存性 | Python 標準ライブラリ | 別途インストール必要 |
| インストールサイズ | 0 MB（バンドル済み） | ~100 MB |
| 機能性 | 本プロジェクトに十分 | 高機能だが過剰 |
| 学習コスト | 低い | 中程度 |

Phase 1 の要件（メインウィンドウ、タブ、Treeview、ダイアログ）は tkinter で十分に実現可能。
将来的に高度な UI が必要になった場合は Phase 5 で PyQt5 への移行を検討する。

---

## 7. 実装順序（推奨）

```
Step 1: プロジェクト基盤セットアップ (Issue #6)
        ├── ディレクトリ作成
        ├── pyproject.toml 更新
        ├── CI パイプライン設定
        └── conftest.py + テストフィクスチャ

Step 2: SignalInfo データモデル (Issue #9)
        ├── SignalInfo / MessageInfo dataclass
        ├── SignalRepository クラス
        └── ユニットテスト (test_signal_model.py)

Step 3: (並列実行可能)
        ├── DBC パーサー (Issue #7)
        │   ├── DbcParser 実装
        │   └── ユニットテスト (test_dbc_parser.py)
        │
        └── LDF パーサー (Issue #8)
            ├── LdfParser 実装
            └── ユニットテスト (test_ldf_parser.py)

Step 4: GUI スケルトン (Issue #10)
        ├── MainWindow 実装
        ├── メニューバー・タブ・ステータスバー
        └── エントリーポイント (main.py)

Step 5: ファイル読込 UI・信号一覧表示 (Issue #11)
        ├── SignalTab 実装
        ├── パーサー統合（拡張子判定→自動選択）
        ├── 統合テスト (test_parser_to_gui.py)
        └── 動作確認・スクリーンショット
```

### 並列実行の最適化

足軽3名で実施する場合の最適配分:

```
足軽A: #6 (基盤)     → #9 (モデル) → #10 (GUIスケルトン)
足軽B: (待機)         → #7 (DBC)   → #11 (信号一覧UI, #9,#10完了待ち)
足軽C: (待機)         → #8 (LDF)   → 統合テスト補助
```

**クリティカルパス:** `#6 → #9 → #7/#8 → #11`

> **注意:** #9（データモデル）はパーサー (#7, #8) と GUI (#10, #11) の両方が依存するため、最優先で完了させること。

---

## 8. CI パイプライン（.github/workflows/ci.yml）

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Lint (ruff)
        run: ruff check .

      - name: Type check (mypy)
        run: mypy src/

      - name: Test (pytest)
        run: pytest --cov=src --cov-report=term-missing
```

---

*本文書は Phase 1 設計書 Ver.1.0 です。実装中に判明した設計変更は版管理のうえ更新してください。*

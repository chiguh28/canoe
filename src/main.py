"""CANoe Auto Test Tool - Entry Point

Usage:
    python -m src
    python src/main.py
"""

from src.gui.main_window import MainWindow


def main() -> None:
    """アプリケーション起動"""
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()

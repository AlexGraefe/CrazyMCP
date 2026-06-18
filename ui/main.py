import asyncio
import sys

from PyQt6.QtWidgets import QApplication

from console_llm import create_agent
from ui.main_window import MainWindow


def run() -> None:
    """Entry point for the PyQt6 swarm control UI."""
    agent = create_agent()

    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QWidget {
            background-color: #1e1e1e;
            color: #d4d4d4;
        }
    """)

    window = MainWindow(agent=agent)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    run()
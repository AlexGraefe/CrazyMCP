import sys

from PyQt6.QtWidgets import QApplication

from agent import create_agent
from ui.main_window import MainWindow
from ui.swarm_tool import create_swarm_tool


def run() -> None:
    """Entry point for the PyQt6 swarm control UI."""
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QWidget {
            background-color: #1e1e1e;
            color: #d4d4d4;
        }
    """)

    window = MainWindow()
    window.show()

    agent = create_agent(tools=[create_swarm_tool(window)])
    window.set_agent(agent)

    sys.exit(app.exec())


if __name__ == "__main__":
    run()
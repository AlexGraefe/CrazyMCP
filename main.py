import argparse
import sys

from PyQt6.QtWidgets import QApplication

from agent import create_agent
from ui.main_window import MainWindow
from ui.swarm_tool import create_swarm_tool


def run() -> None:
    """Entry point for the PyQt6 swarm control UI."""
    parser = argparse.ArgumentParser(description="Crazyflie Swarm Control")
    parser.add_argument(
        "--address-offset",
        type=int,
        default=0,
        metavar="N",
        help="Offset added to drone address indices (e.g. 2 → connect to addresses 03, 04, ...)",
    )
    args, qt_args = parser.parse_known_args()

    app = QApplication([sys.argv[0]] + qt_args)
    app.setStyleSheet("""
        QWidget {
            background-color: #1e1e1e;
            color: #d4d4d4;
        }
    """)

    window = MainWindow(address_offset=args.address_offset)
    window.show()

    agent = create_agent(tools=[create_swarm_tool(window)])
    window.set_agent(agent)

    sys.exit(app.exec())


if __name__ == "__main__":
    run()
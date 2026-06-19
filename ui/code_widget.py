from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTextEdit, QWidget, QVBoxLayout


class CodeWidget(QWidget):
    """Right panel containing code display with syntax highlighting."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet("background-color: #001a33;")

        self._code = QTextEdit()
        self._code.setReadOnly(True)
        self._code.setStyleSheet("""
            QTextEdit {
                background-color: #000a1a;
                color: #39ff14;
                font-family: monospace;
                font-size: 12px;
                border: 1px solid #444444;
            }
        """)
        layout.addWidget(self._code)

    def set_code(self, code: str) -> None:
        """Set the code to display."""
        self._code.setPlainText(code)

    def clear(self) -> None:
        """Clear the code display."""
        self._code.clear()

    def get_code(self) -> str:
        """Get the current code content."""
        return self._code.toPlainText()
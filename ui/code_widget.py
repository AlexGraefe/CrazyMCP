from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTextEdit, QWidget, QVBoxLayout, QPushButton, QHBoxLayout


class CodeWidget(QWidget):
    """Right panel containing code display with syntax highlighting."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._code = QTextEdit()
        self._code.setReadOnly(True)
        self._code.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: monospace;
                font-size: 12px;
                border: 1px solid #3e3e3e;
            }
        """)
        layout.addWidget(self._code)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self._clear_button = QPushButton("Clear")
        self._clear_button.setStyleSheet("""
            QPushButton {
                background-color: #3e3e3e;
                color: #d4d4d4;
                font-family: monospace;
                font-size: 12px;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background-color: #4e4e4e;
            }
        """)
        self._clear_button.clicked.connect(self.clear)
        button_layout.addWidget(self._clear_button)
        layout.addLayout(button_layout)

    def set_code(self, code: str) -> None:
        """Set the code to display."""
        self._code.setPlainText(code)

    def clear(self) -> None:
        """Clear the code display."""
        self._code.clear()

    def get_code(self) -> str:
        """Get the current code content."""
        return self._code.toPlainText()
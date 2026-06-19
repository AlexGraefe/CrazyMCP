from datetime import datetime

from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QTextEdit, QWidget, QVBoxLayout


class ChatWidget(QWidget):
    """Left panel containing chat interface for LLM interaction."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet("background-color: #001a33;")

        self._history = QTextEdit()
        self._history.setReadOnly(True)
        self._history.setStyleSheet("""
            QTextEdit {
                background-color: #000a1a;
                color: #39ff14;
                font-family: monospace;
                font-size: 12px;
                border: 1px solid #444444;
            }
        """)
        layout.addWidget(self._history)

    def append_user_message(self, message: str) -> None:
        """Append a user message to the chat history."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._append_text(f"You [{timestamp}]: {message}")

    def append_llm_message(self, message: str) -> None:
        """Append an LLM response to the chat history."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._append_text(f"LLM [{timestamp}]: {message}")

    def append_llm_thinking(self) -> None:
        """Show thinking indicator (initial placeholder)."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._append_text(f"LLM [{timestamp}]: Thinking...")

    def append_system_message(self, message: str) -> None:
        """Append a system/output message to the chat history."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._append_text(f"System [{timestamp}]: {message}")

    def append_output(self, text: str) -> None:
        """Append raw output to the chat history."""
        self._append_text(text)

    def _append_text(self, text: str) -> None:
        """Append text and scroll to bottom."""
        self._history.moveCursor(QTextCursor.MoveOperation.End)
        self._history.insertPlainText(text)
        self._history.moveCursor(QTextCursor.MoveOperation.End)

    def clear_history(self) -> None:
        """Clear the chat history."""
        self._history.clear()
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QSplitter,
    QHBoxLayout,
    QPushButton,
    QStatusBar,
    QMessageBox,
    QVBoxLayout,
    QLabel,
    QTextEdit,
    QSizePolicy,
)

from .chat_widget import ChatWidget
from .code_widget import CodeWidget
from .swarm_executor import SwarmExecutor


class MainWindow(QMainWindow):
    """Main application window with splitter layout for chat and code panels at top, and controls at bottom."""

    _code_received = pyqtSignal(str)

    def _setup_ui(self) -> None:
        """Create main UI components."""
        self.setWindowTitle("Crazyflie Swarm Control")
        self.resize(1000, 600)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #001a33;
            }
            QStatusBar {
                background-color: #001a33;
                color: #39ff14;
                font-family: monospace;
            }
        """)

        central = QWidget()
        central.setStyleSheet("background-color: #001a33;")
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #444444;
            }
            QSplitter::handle:horizontal {
                width: 1px;
            }
        """)

        self._chat = ChatWidget()
        self._code = CodeWidget()
        self._code_received.connect(self._code.set_code)

        splitter.addWidget(self._chat)
        splitter.addWidget(self._code)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)
        main_layout.setStretchFactor(splitter, 1)

        bottom_container = QWidget()
        bottom_container.setStyleSheet("background-color: #001a33;")
        bottom_container.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed))
        bottom_layout = QHBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(10, 2, 10, 2)

        self._input = QTextEdit()
        self._input.setPlaceholderText("Enter prompt...")
        self._input.setMaximumHeight(80)
        self._input.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self._input.setStyleSheet("""
            QTextEdit {
                background-color: #000a1a;
                color: #39ff14;
                font-family: monospace;
                font-size: 12px;
                border: 1px solid #444444;
            }
        """)
        self._input.textChanged.connect(self._on_input_changed)

        button_container = QWidget()
        button_container.setStyleSheet("background-color: #001a33;")
        button_layout = QVBoxLayout(button_container)
        button_layout.setSpacing(1)
        button_layout.setContentsMargins(0, 0, 0, 0)

        self._simulate_button = QPushButton("Simulate")
        self._simulate_button.setCheckable(True)
        self._simulate_button.setStyleSheet(self._button_style())
        self._simulate_button.clicked.connect(self._on_simulate)

        self._experiment_button = QPushButton("Experiment")
        self._experiment_button.setCheckable(True)
        self._experiment_button.setStyleSheet(self._button_style())
        self._experiment_button.clicked.connect(self._on_experiment)

        self._clear_button = QPushButton("Clear")
        self._clear_button.setStyleSheet(self._button_style())
        self._clear_button.clicked.connect(self._on_clear)

        button_layout.addWidget(self._simulate_button)
        button_layout.addWidget(self._experiment_button)
        button_layout.addWidget(self._clear_button)

        bottom_layout.addWidget(self._input, 1)
        bottom_layout.addWidget(button_container)

        main_layout.addWidget(bottom_container)

        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Ready")

    def __init__(self, agent=None, parent=None):
        super().__init__(parent)
        self._agent = agent
        self._executor: SwarmExecutor | None = None
        self._swarm_show_code: str | None = None
        self._setup_ui()
        self._create_loading_overlay()

    def set_agent(self, agent) -> None:
        """Assign the LLM agent after the window has been created."""
        self._agent = agent

    def _create_loading_overlay(self) -> None:
        """Create a semi‑transparent overlay with a loading indicator."""
        overlay = QWidget(self)
        overlay.setObjectName("loadingOverlay")
        overlay.setStyleSheet("""
            QWidget#loadingOverlay {
                background-color: rgba(0, 26, 51, 180);
            }
        """)
        overlay.setGeometry(self.rect())
        overlay.setVisible(False)

        layout = QVBoxLayout(overlay)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        loading_label = QLabel("LLM is thinking...")
        loading_label.setStyleSheet("color: #39ff14; font-size: 16px; font-family: monospace;")
        layout.addWidget(loading_label)

        self._loading_overlay = overlay
        # Ensure overlay is on top of other widgets
        overlay.raise_()
        # Ensure overlay resizes with window
        self.resizeEvent = self._on_resize

    def _on_resize(self, event) -> None:  # type: ignore[override]
        if hasattr(self, "_loading_overlay") and self._loading_overlay:
            self._loading_overlay.setGeometry(self.rect())
        super().resizeEvent(event)

    def _show_loading(self, show: bool) -> None:
        """Show or hide the loading overlay."""
        if hasattr(self, "_loading_overlay") and self._loading_overlay:
            self._loading_overlay.setVisible(show)
            if show:
                QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            else:
                QApplication.restoreOverrideCursor()

    def _on_input_changed(self) -> None:
        """Handle text input changes - detect Enter to submit prompt."""
        text = self._input.toPlainText()
        if '\n' in text:
            lines = text.split('\n')
            prompt = lines[0].strip()
            self._input.setPlainText('')
            if prompt:
                self._on_prompt(prompt)

    def _button_style(self) -> str:
        return """
            QPushButton {
                background-color: #000a1a;
                color: #39ff14;
                font-family: monospace;
                font-size: 12px;
                padding: 2px 12px;
                border: 1px solid #444444;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #002244;
                border: 1px solid #555555;
            }
            QPushButton:disabled {
                background-color: #000511;
                color: #00aa00;
                border: 1px solid #333333;
            }
            QPushButton:checked {
                background-color: #003300;
                border: 1px solid #555555;
            }
        """

    def _on_prompt(self, prompt: str) -> None:
        """Handle prompt submission and get LLM response."""
        if not prompt:
            return

        self._chat.append_user_message(prompt)
        self._chat.append_llm_thinking()
        self._set_buttons_enabled(False)
        # Force UI update so loading overlay becomes visible before blocking call
        QApplication.processEvents()

        self._run_llm(prompt)

    def _run_llm(self, prompt: str) -> None:
        """Run LLM with streaming and handle response live."""
        import asyncio

        async def _stream():
            """Stream events from the agent and update UI token‑by‑token."""
            if self._agent is None:
                self._chat.append_system_message("No agent configured")
                return

            stream = self._agent.stream_events(
                {"messages": [{"role": "user", "content": prompt}]},
                version="v3",
            )
            full_text = ""
            for message in stream.messages:
                for token in message.reasoning:
                    self._chat.append_output(f"[thinking] {token}")
                    QApplication.processEvents()
                for token in message.text:
                    self._chat.append_output(token)
                    full_text += token
                    QApplication.processEvents()
                for tool_call in message.tool_calls:
                    if tool_call and isinstance(tool_call, dict):
                        if tool_call.get("type") == "tool_call":
                            name = tool_call.get("name", "")
                            if name == "swarm_show_execute":
                                args = tool_call.get("args", {})
                                swarm_show_func = args.get("swarm_show_func", "")
                                if swarm_show_func:
                                    self._swarm_show_code = swarm_show_func
                                    self._code.set_code(swarm_show_func)
            if full_text:
                self._chat.append_llm_message(full_text)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_stream())
        except Exception as e:
            self._chat.append_system_message(f"Error: {e}")
        finally:
            loop.close()
            self._set_buttons_enabled(True)

    async def _invoke_agent(self, prompt: str) -> dict:
        """Invoke the agent with the given prompt."""
        if self._agent is None:
            return {"messages": [{"content": "No agent configured"}]}

        async_response = self._agent.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]}
        )
        return await async_response

    def _handle_llm_response(self, response: dict) -> None:
        """Process LLM response and extract swarm_show code."""
        for msg in response.get("messages", []):
            if hasattr(msg, "content") and msg.content:
                content = msg.content
                self._chat.append_llm_message(content)

                code = SwarmExecutor.extract_swarm_show_code(content)
                if code:
                    self._swarm_show_code = code
                    self._code.set_code(code)

        self._set_buttons_enabled(True)

    def set_swarm_show_code(self, code: str) -> None:
        """Receive code from a tool call and update the code widget."""
        self._swarm_show_code = code
        self._code_received.emit(code)

    def _on_simulate(self) -> None:
        """Handle simulate button click."""
        if not self._swarm_show_code:
            QMessageBox.warning(self, "No Code", "No swarm_show code to simulate.")
            self._simulate_button.setChecked(False)
            return

        self._execute_swarm(simulated=True)

    def _on_experiment(self) -> None:
        """Handle experiment button click."""
        if not self._swarm_show_code:
            QMessageBox.warning(self, "No Code", "No swarm_show code to experiment.")
            self._experiment_button.setChecked(False)
            return

        self._execute_swarm(simulated=False)

    def _on_clear(self) -> None:
        """Handle clear button click."""
        self._chat.clear_history()
        self._code.set_code("")
        self._swarm_show_code = None

    def _execute_swarm(self, simulated: bool) -> None:
        """Execute the swarm show script."""
        self._set_buttons_enabled(False)
        self._status.showMessage("Simulating..." if simulated else "Experimenting...")

        self._executor = SwarmExecutor()
        self._executor.output_signal.connect(self._on_output)
        self._executor.finished_signal.connect(self._on_finished)
        self._executor.setup(self._swarm_show_code, num_drones=3, simulated=simulated)
        self._executor.start()

    def _on_output(self, text: str) -> None:
        """Handle output from executor."""
        self._chat.append_output(text)

    def _on_finished(self, exit_code: int, status: str) -> None:
        """Handle executor completion."""
        self._simulate_button.setChecked(False)
        self._experiment_button.setChecked(False)
        self._set_buttons_enabled(True)

        if status == "completed":
            self._status.showMessage("Completed")
            self._chat.append_system_message("Swarm show completed successfully")
        else:
            self._status.showMessage("Error")
            self._chat.append_system_message(f"Swarm show failed with exit code {exit_code}")

    def _set_buttons_enabled(self, enabled: bool) -> None:
        """Enable/disable buttons during execution."""
        self._simulate_button.setEnabled(enabled)
        self._experiment_button.setEnabled(enabled)
        # Update loading overlay visibility
        self._show_loading(not enabled)
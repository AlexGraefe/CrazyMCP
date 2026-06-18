from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QSplitter,
    QHBoxLayout,
    QPushButton,
    QStatusBar,
    QMessageBox,
)

from .chat_widget import ChatWidget
from .code_widget import CodeWidget
from .swarm_executor import SwarmExecutor


class MainWindow(QMainWindow):
    """Main application window with splitter layout for chat and code panels."""

    def __init__(self, agent=None, parent=None):
        super().__init__(parent)
        self._agent = agent
        self._executor: SwarmExecutor | None = None
        self._swarm_show_code: str | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Crazyflie Swarm Control")
        self.resize(1000, 600)

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._chat = ChatWidget()
        self._code = CodeWidget()

        splitter.addWidget(self._chat)
        splitter.addWidget(self._code)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)

        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(10, 5, 10, 5)

        self._simulate_button = QPushButton("Simulate")
        self._simulate_button.setCheckable(True)
        self._simulate_button.setStyleSheet(self._button_style())
        self._simulate_button.clicked.connect(self._on_simulate)

        self._fly_button = QPushButton("Fly")
        self._fly_button.setCheckable(True)
        self._fly_button.setStyleSheet(self._button_style())
        self._fly_button.clicked.connect(self._on_fly)

        button_layout.addWidget(self._simulate_button)
        button_layout.addWidget(self._fly_button)
        button_layout.addStretch()

        bottom_container = QWidget()
        bottom_layout = QHBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.addWidget(button_container)

        main_layout.addWidget(bottom_container)

        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Ready")

        self._chat._input.returnPressed.disconnect()
        self._chat._input.returnPressed.connect(self._on_prompt)

    def _button_style(self) -> str:
        return """
            QPushButton {
                background-color: #3e3e3e;
                color: #d4d4d4;
                font-family: monospace;
                font-size: 12px;
                padding: 6px 16px;
                border: none;
            }
            QPushButton:hover {
                background-color: #4e4e4e;
            }
            QPushButton:disabled {
                background-color: #2e2e2e;
                color: #888888;
            }
        """

    def _on_prompt(self) -> None:
        """Handle prompt submission and get LLM response."""
        prompt = self._chat.get_input_text().strip()
        if not prompt:
            return

        self._chat.append_user_message(prompt)
        self._chat.clear_input()
        self._chat.append_llm_thinking()
        self._set_buttons_enabled(False)

        self._run_llm(prompt)

    def _run_llm(self, prompt: str) -> None:
        """Run LLM in a thread and handle response."""
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            response = loop.run_until_complete(self._invoke_agent(prompt))
            self._handle_llm_response(response)
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

    def _on_simulate(self) -> None:
        """Handle simulate button click."""
        if not self._swarm_show_code:
            QMessageBox.warning(self, "No Code", "No swarm_show code to simulate.")
            self._simulate_button.setChecked(False)
            return

        self._execute_swarm(simulated=True)

    def _on_fly(self) -> None:
        """Handle fly button click."""
        if not self._swarm_show_code:
            QMessageBox.warning(self, "No Code", "No swarm_show code to fly.")
            self._fly_button.setChecked(False)
            return

        self._execute_swarm(simulated=False)

    def _execute_swarm(self, simulated: bool) -> None:
        """Execute the swarm show script."""
        self._set_buttons_enabled(False)
        self._status.showMessage("Running..." if simulated else "Flying...")

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
        self._fly_button.setChecked(False)
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
        self._fly_button.setEnabled(enabled)
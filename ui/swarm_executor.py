import asyncio
import re

from PyQt6.QtCore import QThread, pyqtSignal

from runner.swarm_runner import run_swarm_show


class SwarmExecutor(QThread):
    """Thread-safe executor that runs swarm shows asynchronously.

    Uses QThread with asyncio.run() in the thread's run() method to
    integrate asyncio with Qt's event loop without blocking the UI.
    """

    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._swarm_show_func: str | None = None
        self._num_drones: int = 3
        self._simulated: bool = True
        self._no_wait: bool = False

    def setup(
        self,
        swarm_show_func: str,
        num_drones: int = 3,
        simulated: bool = True,
        no_wait: bool = False,
    ) -> None:
        """Configure the executor with function code and options."""
        self._swarm_show_func = swarm_show_func
        self._num_drones = num_drones
        self._simulated = simulated
        self._no_wait = no_wait

    def run(self) -> None:
        """Execute the script in the thread's event loop."""
        try:
            exit_code, stdout, stderr = asyncio.run(self._execute())
            if stdout:
                self.output_signal.emit(stdout)
            if stderr:
                self.output_signal.emit(stderr)
            self.finished_signal.emit(
                exit_code, "completed" if exit_code == 0 else "error"
            )
        except Exception as e:
            self.output_signal.emit(f"Error: {e}")
            self.finished_signal.emit(1, "error")

    async def _execute(self) -> tuple[int, str, str]:
        """Internal async execution method."""
        if self._swarm_show_func is None:
            return 1, "", "No function configured"
        return await run_swarm_show(
            self._swarm_show_func,
            self._num_drones,
            self._simulated,
            self._no_wait,
        )

    @staticmethod
    def extract_swarm_show_code(response_content: str) -> str | None:
        """Extract the ``swarm_show`` function code from the LLM response.

        Handles responses that may include markdown code fences (```python) and
        extracts the function definition with its body.
        """
        # Remove surrounding markdown fences if present
        content = response_content.strip()
        if content.startswith("```"):
            # Find the first newline after the opening fence
            first_newline = content.find("\n")
            if first_newline != -1:
                content = content[first_newline + 1 :]
            # Remove trailing fence
            if content.rstrip().endswith("```"):
                content = content.rstrip()[: -3]
        lines = content.split("\n")
        start_idx = None
        end_idx = None
        for i, line in enumerate(lines):
            if re.match(r"\s*def\s+swarm_show\s*\(", line):
                start_idx = i
                continue
            if start_idx is not None:
                # End of function when a non-indented line appears (ignoring empty lines)
                if line.strip() and not line.startswith(" " * 4) and not line.startswith("\t"):
                    end_idx = i
                    break
        if start_idx is not None:
            end_idx = end_idx if end_idx is not None else len(lines)
            return "\n".join(lines[start_idx:end_idx]).strip()
        return None

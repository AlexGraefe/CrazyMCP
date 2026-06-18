import asyncio
import os
import re
import sys
import tempfile
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from PyQt6.QtCore import QThread, pyqtSignal


def generate_script(swarm_show_func: str, num_drones: int = 3, simulated: bool = True) -> str:
    """Generate a complete swarm show script from the swarm_show function code."""
    template_dir = Path(__file__).parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("swarm_show_script.py.jinja2")

    project_root = os.path.dirname(os.path.abspath(__file__))
    project_root = str(Path(project_root).parent)

    script_content = template.render(
        project_root=project_root,
        simulated=simulated,
        num_drones=num_drones,
        base_address="radio://0/80/2M/E7E7E7E7E",
        swarm_show_func=swarm_show_func,
    )
    return script_content


async def _run_script(script_path: str) -> tuple[int, str, str]:
    """Run a script and capture output."""
    python_path = sys.executable if sys.executable else "python"
    proc = await asyncio.create_subprocess_exec(
        python_path, script_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    stdout_text = stdout.decode() if stdout else ""
    stderr_text = stderr.decode() if stderr else ""
    return proc.returncode, stdout_text, stderr_text


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
        self._script_path: str | None = None

    def setup(self, swarm_show_func: str, num_drones: int = 3, simulated: bool = True) -> None:
        """Configure the executor with function code and options."""
        self._swarm_show_func = swarm_show_func
        self._num_drones = num_drones
        self._simulated = simulated

        script_content = generate_script(swarm_show_func, num_drones, simulated)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(script_content)
            self._script_path = f.name

    def run(self) -> None:
        """Execute the script in the thread's event loop."""
        try:
            exit_code, stdout, stderr = asyncio.run(self._execute())
            if stdout:
                self.output_signal.emit(stdout)
            if stderr:
                self.output_signal.emit(stderr)
            self.finished_signal.emit(exit_code, "completed" if exit_code == 0 else "error")
        except Exception as e:
            self.output_signal.emit(f"Error: {e}")
            self.finished_signal.emit(1, "error")
        finally:
            if self._script_path:
                try:
                    os.unlink(self._script_path)
                except OSError:
                    pass

    async def _execute(self) -> tuple[int, str, str]:
        """Internal async execution method."""
        if self._script_path is None:
            return 1, "", "No script path configured"
        return await _run_script(self._script_path)

    @staticmethod
    def extract_swarm_show_code(response_content: str) -> str | None:
        """Extract the swarm_show function code from LLM response.

        Args:
            response_content: The raw response content from the LLM

        Returns:
            The extracted function code, or None if not found
        """
        lines = response_content.split("\n")
        start_idx = None
        end_idx = None

        for i, line in enumerate(lines):
            if re.match(r"\s*def\s+swarm_show\s*\(", line):
                start_idx = i
            elif start_idx is not None:
                if line.strip() and not line.startswith(" " * 4) and not line.startswith("\t"):
                    end_idx = i
                    break

        if start_idx is not None:
            end_idx = end_idx if end_idx else len(lines)
            return "\n".join(lines[start_idx:end_idx]).strip()
        return None
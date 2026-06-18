import asyncio
import concurrent.futures
from typing import Callable, Optional, TYPE_CHECKING

from langchain.tools import tool

from runner.swarm_runner import run_swarm_show

if TYPE_CHECKING:
    from .main_window import MainWindow


def _run_sync(coro) -> tuple[int, str, str]:
    """Run an async coroutine from a possibly-async context.

    ``asyncio.run`` cannot be called when an event loop is already running.
    In that case, execute the coroutine in a dedicated worker thread.
    """
    try:
        return asyncio.run(coro)
    except RuntimeError as exc:
        if "cannot be called from a running event loop" not in str(exc):
            raise
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(asyncio.run, coro).result()


def create_swarm_tool(window: Optional["MainWindow"] = None) -> Callable:
    """Create a ``swarm_show_execute`` tool bound to a UI window.

    When invoked, the tool immediately forwards the generated function code to
    the UI window so that it can be displayed in the code widget. It then runs
    the simulation with ``no_wait=True`` for a fast preview.
    """

    @tool(parse_docstring=True)
    def swarm_show_execute(
        swarm_show_func: str,
        num_drones: int = 3,
        simulated: bool = True,
        no_wait: bool = True,
    ) -> str:
        """Execute a swarm show by generating and running a complete script.

        Args:
            swarm_show_func: Python function code for swarm_show(current_time: float).
            num_drones: Number of drones to connect to.
            simulated: Whether to use simulated swarm.
            no_wait: When true, use instant sleep for fast preview.

        Returns:
            Result message with exit code and captured output.
        """
        if window is not None:
            window.set_swarm_show_code(swarm_show_func)
        exit_code, stdout, stderr = _run_sync(
            run_swarm_show(swarm_show_func, num_drones, simulated, no_wait)
        )
        return f"Exit code: {exit_code}\n{stdout}\n{stderr}".strip()

    return swarm_show_execute

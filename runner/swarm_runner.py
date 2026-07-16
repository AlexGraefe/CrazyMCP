import asyncio
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

LOG_DIR = Path(__file__).parent.parent / "logs"


def generate_script(
    swarm_show_func: str,
    num_drones: int = 3,
    simulated: bool = True,
    no_wait: bool = False,
    visualize: bool = False,
    address_offset: int = 0,
    testbed_min: tuple[float, float, float] = (-1.5, -1.5, 0.1),
    testbed_max: tuple[float, float, float] = (1.5, 1.5, 2.0),
) -> str:
    """Generate a complete swarm show script from the function code.

    Args:
        swarm_show_func: Python function code for swarm_show(current_time: float).
        num_drones: Number of drones to connect to.
        simulated: Whether to use simulated swarm.
        no_wait: When true, use instant sleep for fast preview.
        testbed_min: Floor corner (x, y, z) of the flight volume in meters.
        testbed_max: Ceiling corner (x, y, z) of the flight volume in meters.

    Returns:
        Complete script content ready for execution.
    """
    template_dir = Path(__file__).parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("swarm_show_script.py.jinja2")

    project_root = str(Path(__file__).parent.parent)

    script_content = template.render(
        project_root=project_root,
        simulated=simulated,
        num_drones=num_drones,
        base_address="radio://0/84/2M/D91F7001",
        address_offset=address_offset,
        swarm_show_func=swarm_show_func,
        no_wait=no_wait,
        visualize=visualize,
        testbed_min=testbed_min,
        testbed_max=testbed_max,
    )
    return script_content


async def _run_script(script_path: str) -> tuple[int, str, str]:
    """Run a script, piping stdout and stderr to log files.

    The captured output is also read back and returned to the caller.
    """
    python_path = sys.executable if sys.executable else "python"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stdout_path = LOG_DIR / f"{stamp}_stdout.log"
    stderr_path = LOG_DIR / f"{stamp}_stderr.log"

    with open(stdout_path, "w") as stdout_file, open(stderr_path, "w") as stderr_file:
        proc = await asyncio.create_subprocess_exec(
            python_path,
            script_path,
            stdout=stdout_file,
            stderr=stderr_file,
        )
        await proc.wait()

    stdout_text = stdout_path.read_text()
    stderr_text = stderr_path.read_text()
    print(f"Script output (logs: {stdout_path}, {stderr_path}):\n{stdout_text}\n{stderr_text}")
    return proc.returncode, stdout_text, stderr_text


async def run_swarm_show(
    swarm_show_func: str,
    num_drones: int = 3,
    simulated: bool = True,
    no_wait: bool = False,
    address_offset: int = 0,
    testbed_min: tuple[float, float, float] = (-1.5, -1.5, 0.1),
    testbed_max: tuple[float, float, float] = (1.5, 1.5, 2.0),
) -> tuple[int, str, str]:
    """Generate and execute a swarm show script.

    Args:
        swarm_show_func: Python function code for swarm_show(current_time: float).
        num_drones: Number of drones to connect to.
        simulated: Whether to use simulated swarm.
        no_wait: When true, use instant sleep for fast preview.
        testbed_min: Floor corner (x, y, z) of the flight volume in meters.
        testbed_max: Ceiling corner (x, y, z) of the flight volume in meters.

    Returns:
        Tuple of (exit_code, stdout, stderr).
    """
    script_content = generate_script(
        swarm_show_func,
        num_drones,
        simulated,
        no_wait,
        address_offset=address_offset,
        testbed_min=testbed_min,
        testbed_max=testbed_max,
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script_content)
        script_path = f.name

    try:
        return await _run_script(script_path)
    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass

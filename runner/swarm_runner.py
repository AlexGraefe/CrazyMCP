import asyncio
import os
import sys
import tempfile
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


def generate_script(
    swarm_show_func: str,
    num_drones: int = 3,
    simulated: bool = True,
    no_wait: bool = False,
    visualize: bool = False,
) -> str:
    """Generate a complete swarm show script from the function code.

    Args:
        swarm_show_func: Python function code for swarm_show(current_time: float).
        num_drones: Number of drones to connect to.
        simulated: Whether to use simulated swarm.
        no_wait: When true, use instant sleep for fast preview.

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
        base_address="radio://0/80/2M/E7E7E7E7E",
        swarm_show_func=swarm_show_func,
        no_wait=no_wait,
        visualize=visualize,
    )
    return script_content


async def _run_script(script_path: str) -> tuple[int, str, str]:
    """Run a script and capture output."""
    python_path = sys.executable if sys.executable else "python"
    proc = await asyncio.create_subprocess_exec(
        python_path,
        script_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    stdout_text = stdout.decode() if stdout else ""
    stderr_text = stderr.decode() if stderr else ""
    return proc.returncode, stdout_text, stderr_text


async def run_swarm_show(
    swarm_show_func: str,
    num_drones: int = 3,
    simulated: bool = True,
    no_wait: bool = False,
) -> tuple[int, str, str]:
    """Generate and execute a swarm show script.

    Args:
        swarm_show_func: Python function code for swarm_show(current_time: float).
        num_drones: Number of drones to connect to.
        simulated: Whether to use simulated swarm.
        no_wait: When true, use instant sleep for fast preview.

    Returns:
        Tuple of (exit_code, stdout, stderr).
    """
    script_content = generate_script(swarm_show_func, num_drones, simulated, no_wait)

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

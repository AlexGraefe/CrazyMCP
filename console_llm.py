import argparse
import asyncio
import os
import tempfile
from pathlib import Path
from langchain.tools import tool
from jinja2 import Environment, FileSystemLoader
from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI

import sys

SYSTEM_PROMPT = """You control a Crazyflie drone swarm. Write a function `swarm_show(current_time: float)` that returns:
- A list of (x, y, z) setpoints for each drone as tuples
- A boolean indicating if the show is finished

The function receives elapsed time in seconds since takeoff. Return positions for all connected drones.
Return (setpoints, False) to continue the show, (setpoints, True) to end and land.

Example:
def swarm_show(current_time: float):
    import math
    x = 0.5 * math.cos(current_time)
    y = 0.5 * math.sin(current_time)
    setpoints = [(x, y, 1.0), (-x, -y, 1.0), (0, 0, 1.0)]
    finished = current_time > 10.0
    return setpoints, finished

Use the swarm_show_execute tool to run your swarm_show function.
"""

@tool(parse_docstring=True)
def swarm_show_execute(swarm_show_func: str, num_drones: int = 3, simulated: bool = True) -> str:
    """Execute a swarm show by generating and running a complete script.

    Args:
        swarm_show_func: Python function code for swarm_show(current_time: float) -> tuple[list[tuple[float, float, float]], bool]
        num_drones: Number of drones to connect to
        simulated: Whether to use simulated swarm

    Returns:
        str: Result message with exit code
    """
    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("swarm_show_script.py.jinja2")
    
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    script_content = template.render(
        project_root=project_root,
        simulated=simulated,
        num_drones=num_drones,
        base_address="radio://0/80/2M/E7E7E7E7E",
        swarm_show_func=swarm_show_func
    )
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(script_content)
        script_path = f.name
    
    try:
        process = asyncio.run(_run_script(script_path))
        return f"Swarm show completed with exit code: {process}"
    except Exception as e:
        return f"Error executing swarm show: {e}"
    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass

async def _run_script(script_path: str) -> int:
    python_path = sys.executable if sys.executable else "python"
    proc = await asyncio.create_subprocess_exec(
        python_path, script_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if stdout:
        print(stdout.decode())
    if stderr:
        print(stderr.decode())
    return proc.returncode

def create_agent() -> None:
    llm = ChatOpenAI(
        model="Qwen/Qwen3.6-27B",
        base_url="http://localhost:8000/v1",
        api_key="1",
    )

    agent = create_deep_agent(
        model=llm,
        tools=[swarm_show_execute],
        system_prompt=SYSTEM_PROMPT,
    )

    return agent

async def console_loop(agent) -> None:
    loop = asyncio.get_running_loop()

    while True:
        try:
            user_input = await loop.run_in_executor(None, input, "You: ")
        except EOFError:
            break
        if user_input.lower() in ("exit", "quit", "q"):
            break
        if not user_input.strip():
            continue

        print("LLM: Thinking...")
        try:
            async_response = agent.ainvoke({"messages": [{"role": "user", "content": user_input}]})
            response = await async_response
            for msg in response["messages"]:
                if hasattr(msg, "content") and msg.content:
                    print(f"LLM: {msg.content}")
        except Exception as e:
            print(f"LLM Error: {e}")

async def main() -> None:
    parser = argparse.ArgumentParser(description="Crazyflie Swarm LLM Console")
    parser.add_argument("--simulated", action="store_true", help="Use simulated swarm instead of hardware")
    args = parser.parse_args()

    agent = create_agent()

    print("Crazyflie Swarm LLM Console")
    print("Type 'exit', 'quit', or 'q' to quit")

    await console_loop(agent)

if __name__ == "__main__":
    asyncio.run(main())
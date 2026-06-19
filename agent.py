import asyncio

from langchain.tools import tool
from langchain_openai import ChatOpenAI

from runner.swarm_runner import run_swarm_show


SYSTEM_PROMPT = """You control a Crazyflie drone swarm consisting of 3 drones. Write a function `swarm_show(current_time: float)` that returns:
- A list of (x, y, z) setpoints for each drone as tuples
- A boolean indicating if the show is finished

Try to make the make the show interesting by avoiding returning the same setpoints repeatedly. 
You do not need to worry about drone collisions or safety, just focus on creating an interesting show.
The drones also are already launched and will land automatically, you do not need to include takeoff or landing logic in your function.

The function receives elapsed time in seconds since takeoff. Return positions for all connected drones.
Return (setpoints, False) to continue the show, (setpoints, True) to end and land.

Generate setpoints in normalized coordinates in the cube [-1, 1]^3:
- x, y: -1 to 1 maps to the horizontal workspace
- z: -1 is the floor (ground level), 1 is the maximum flight height

Example:
def swarm_show(current_time: float):
    import math
    x = 0.5 * math.cos(current_time)
    y = 0.5 * math.sin(current_time)
    setpoints = [(x, y, 1.0), (-x, -y, 1.0), (0, 0, 1.0)]
    finished = current_time > 10.0
    return setpoints, finished

Use the swarm_show_execute tool to run the show.
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
    exit_code, stdout, stderr = asyncio.run(
        run_swarm_show(swarm_show_func, num_drones, simulated, no_wait)
    )
    return f"Exit code: {exit_code}\n{stdout}\n{stderr}".strip()


def create_agent(
    include_generate_script: bool = False,
    tools: list | None = None,
) -> None:
    """Create a deep agent configured to control the swarm."""
    from deepagents import create_deep_agent

    agent_tools = tools if tools is not None else [swarm_show_execute]

    llm = ChatOpenAI(
        model="Qwen/Qwen3.6-27B",
        base_url="http://localhost:8000/v1",
        api_key="1",
    )

    agent = create_deep_agent(
        model=llm,
        tools=agent_tools,
        system_prompt=SYSTEM_PROMPT,
    )
    return agent

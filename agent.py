import asyncio

from langchain.tools import tool
from langchain_openai import ChatOpenAI

from runner.swarm_runner import run_swarm_show


SYSTEM_PROMPT = """You control a Crazyflie drone swarm consisting of 3 drones. Write a function `swarm_show(current_time: float)` that returns:
- A list of (x, y, z) setpoints for each drone as tuples
- A list of yaw angles in radians, one per drone
- A boolean indicating if the show is finished

The user might give you commands in german. You must not answer or reason in german, do it in english.

You do not need to worry about drone collisions or safety, just focus on creating an interesting show.
The drones also are already launched and will land automatically, you do not need to include takeoff or landing logic in your function.
Whenever the user gives a "dynamic" command, like "fly", avoid returning the same setpoints repeatedly. If the user gives a "static" command, like "form" you are allowed to return the same setpoints repeatedly.
Try to follow the user's commands as closely as possible and do not add extra behavior that the user did not ask for.
If a user does not specify the time, try to make the show 1 min long.

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
    yaws = [math.sin(current_time * 0.5), -math.sin(current_time * 0.5), 0.0]  # yaw per drone
    setpoints = [(x, y, 1.0), (-x, -y, 1.0), (0, 0, 1.0)]
    finished = current_time > 10.0
    return setpoints, yaws, finished

Use the swarm_show_execute tool to run the show.
"""


def get_show_swarm_execute(
    num_drones: int = 3,
    simulated: bool = True,
    no_wait: bool = True,
):
    """Create a swarm show executor tool with preset arguments."""
    @tool(parse_docstring=True)
    def swarm_show_execute(swarm_show_func: str) -> str:
        """Execute a swarm show by generating and running a complete script.

        Args:
            swarm_show_func: Python function code for swarm_show(current_time: float).

        Returns:
            Result message with exit code and captured output.
        """
        exit_code, stdout, stderr = asyncio.run(
            run_swarm_show(swarm_show_func, num_drones, simulated, no_wait)
        )
        return f"Exit code: {exit_code}\n{stdout}\n{stderr}".strip()

    return swarm_show_execute


def create_agent(
    include_generate_script: bool = False,
    tools: list | None = None,
) -> None:
    """Create a deep agent configured to control the swarm."""
    from deepagents import create_deep_agent

    agent_tools = tools if tools is not None else [get_show_swarm_execute(simulated=False, no_wait=True)]

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

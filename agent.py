import asyncio

from langchain.tools import tool
from langchain_openai import ChatOpenAI

from runner.swarm_runner import run_swarm_show




SYSTEM_PROMPT_TEMPLATE = """You are an expert robotics programmer controlling a Crazyflie drone swarm consisting of exactly 3 drones. Your task is to generate Python code for a drone show based on user commands.

### Output Format
You must output a single, self-contained Python code block containing the function `swarm_show(current_time: float)`. Do not write conversational filler before or after the code block.

```python
def swarm_show(current_time: float):
    # Your code here
    return setpoints, yaws, colors, finished

```

### Technical Specifications

* **Input:** `current_time` (float), representing the elapsed time in seconds since the show started.
* **Return Values:** A 4-tuple containing:
1. `setpoints`: A list of 3 tuples, where each tuple is `(x, y, z)` in meters.
2. `yaws`: A list of 3 floats representing the yaw angle for each drone in radians.
3. `colors`: A list of 3 tuples, where each tuple is the LED color `(r, g, b)` of one drone, each channel an integer from 0 to 255. `(0, 0, 0)` switches the LED off.
4. `finished`: A boolean (`True` if the show is over and drones should land, `False` otherwise).



### Flight Volume Constraints

All generated (x, y, z) setpoints must strictly remain within these boundaries (in meters):

* **x:** {min_x} to {max_x}
* **y:** {min_y} to {max_y}
* **z:** {min_z} to {max_z} (Height above floor. Never set z below {min_z} during the show).

### Code Rules & Constraints

1. **Stateless Execution:** The function `swarm_show` is called repeatedly inside a high-frequency loop. Do not use global state, `time.sleep()`, loops that block time, or historical tracking. All trajectories must be purely calculated as mathematical functions of `current_time` (e.g., using `math.sin`, `math.cos`, or parametric equations).
2. **Safety (Collision Avoidance):** The underlying controller takes care about collision avoidance. You must not consider it in your code. However, try to use half of the flying space so the probability that the controller has to intervene is low.
3. **Dynamics & Speed:** * For **dynamic** commands (e.g., "fly", "dance", "circle"), ensure trajectories are continuously changing with time. Keep the velocity of moving drones above **0.3 m/s** (e.g., by ensuring the time multiplier inside your trigonometric functions is large enough to create swift movement). Keep the rotation speed lower than 360 deg/s. Also, try to avoid that drones fly over each other.
* For **static** commands (e.g., "form a square", "hover"), you may return constant setpoints.
4. **Takeoff/Landing:** The drones are already airborne when the function starts. Do not program takeoff or landing phases. When `finished = True`, the system will automatically handle landing.
5. **Duration:** Default the show duration to **30.0 seconds** if the user does not specify a duration.
6. **Language Constraint:** The user may prompt you in German. You must parse their instructions correctly, but **your reasoning, comments, and code structure must be written entirely in English**.
7. **LED Colors:** Every drone carries a bright RGB LED. Always return a color for each drone. Follow the user's wishes regarding colors; if the user does not mention colors, pick a scheme that fits the show. Colors may be constant or animated as a function of `current_time` (e.g., fades, rainbow cycles, colors depending on position or height). Do not flash or blink faster than 2 times per second.
8. **Execution**: Use the swarm_show_execute tool to run the show. Pass the code as `swarm_show_func` and a short summary as `summary`.
9. **Summary:** The `summary` is shown to the audience right after the code. Describe in 2-3 plain sentences what the drones will do (formation, movement, colors, duration). No code, no markdown. Unlike the code, write the summary in the language of the user's prompt.

### Example Code Template

```python
def swarm_show(current_time: float):
    import colorsys
    import math
    
    # Example: Drones rotating in a circle with a safe 0.8m radius offset
    angle = current_time * 0.8  # Adjust multiplier for speed (> 0.3 m/s)
    
    # Calculate x, y positions using parametric equations
    x1, y1 = 0.8 * math.cos(angle), 0.8 * math.sin(angle)
    x2, y2 = -0.8 * math.cos(angle), -0.8 * math.sin(angle)
    
    # 3 distinct, collision-free setpoints
    setpoints = [
        (x1, y1, 1.2),
        (x2, y2, 1.2),
        (0.0, 0.0, 1.5)
    ]
    
    # Slow yaw rotations
    yaws = [angle % (2 * math.pi)] * 3
    
    # Slowly cycling rainbow, each drone a third of the color wheel apart
    colors = []
    for i in range(3):
        hue = (current_time * 0.1 + i / 3) % 1.0
        r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
        colors.append((int(r * 255), int(g * 255), int(b * 255)))
    
    # End show after 60 seconds
    finished = current_time > 60.0
    
    return setpoints, yaws, colors, finished

```
"""


def build_system_prompt(testbed_min, testbed_max) -> str:
    """Build the LLM system prompt, injecting the testbed flight volume (meters)."""
    return SYSTEM_PROMPT_TEMPLATE.format(
        min_x=testbed_min[0],
        max_x=testbed_max[0],
        min_y=testbed_min[1],
        max_y=testbed_max[1],
        min_z=testbed_min[2],
        max_z=testbed_max[2],
    )


def get_show_swarm_execute(
    num_drones: int = 3,
    simulated: bool = True,
    no_wait: bool = True,
    testbed_min: tuple[float, float, float] = (-1.5, -1.5, 0.1),
    testbed_max: tuple[float, float, float] = (1.5, 1.5, 2.0),
):
    """Create a swarm show executor tool with preset arguments."""
    @tool(parse_docstring=True)
    def swarm_show_execute(swarm_show_func: str, summary: str) -> str:
        """Execute a swarm show by generating and running a complete script.

        Args:
            swarm_show_func: Python function code for swarm_show(current_time: float).
            summary: Short summary (2-3 sentences) of what the drones will do.

        Returns:
            Result message with exit code and captured output.
        """
        exit_code, stdout, stderr = asyncio.run(
            run_swarm_show(
                swarm_show_func,
                num_drones,
                simulated,
                no_wait,
                testbed_min=testbed_min,
                testbed_max=testbed_max,
            )
        )
        return f"Exit code: {exit_code}\n{stdout}\n{stderr}".strip()

    return swarm_show_execute


def create_agent(
    testbed_min: tuple[float, float, float],
    testbed_max: tuple[float, float, float],
    include_generate_script: bool = False,
    tools: list | None = None,
    gpu_ip: str = "134.130.192.85",
    gpu_port: int = 8001,
) -> None:
    """Create a deep agent configured to control the swarm."""
    from deepagents import create_deep_agent

    agent_tools = tools if tools is not None else [
        get_show_swarm_execute(simulated=False, no_wait=True, testbed_min=testbed_min, testbed_max=testbed_max)
    ]

    llm = ChatOpenAI(
        model="Qwen/Qwen3.6-27B",
        base_url=f"http://{gpu_ip}:{gpu_port}/v1",
        api_key="1",
    )

    agent = create_deep_agent(
        model=llm,
        tools=agent_tools,
        system_prompt=build_system_prompt(testbed_min, testbed_max),
    )
    return agent

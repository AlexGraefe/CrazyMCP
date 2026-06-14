import asyncio
from langchain.tools import tool
from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI
from hardware import Swarm, SwarmController

SYSTEM_PROMPT = """You are connected to a Crazyflie drone swarm that you can control via Python code.

The swarm has the following states: UNCONNECTED → CONNECTED → FLYING → LANDED/ERROR.

A `swarm` object is available in your execution namespace with these methods:
- swarm.state -> str: Returns current state (UNCONNECTED, CONNECTED, FLYING, LANDED, ERROR)
- swarm.connect(base_address, num_drones) -> str: Connect to drones
- swarm.takeoff() -> str: Start takeoff sequence (must be in CONNECTED state)
- swarm.land() -> str: Land all drones (must be in FLYING state)
- swarm.emergency_stop() -> None: Immediately land all drones
- swarm.disconnect() -> str: Disconnect from drones
- swarm.get_positions() -> list[(x,y,z)] | None: Get current drone positions
- swarm.num_drones() -> int: Get number of connected drones

Use asyncio and numpy (available as np) in your code. Write complete Python code and it will be queued for execution.

Examples:
- To connect to 3 drones: swarm.connect("radio://0/80/2M/E7E7E7E7E", 3)
- To take off: swarm.takeoff()
- To move to (0.5, 0.0, 1.0): swarm.goto([(0.5, 0.0, 1.0)])
- To get positions: positions = swarm.get_positions(); print(positions)
- To land: swarm.land()
"""

_swarm_controller: SwarmController | None = None

@tool(parse_docstring=True)
def swarm_execute(code: str) -> str:
    """Add Python code to the execution queue for the swarm."""
    global _swarm_controller
    if _swarm_controller is None:
        return "Error: Swarm controller not initialized"

    _swarm_controller.queue_code(code)
    return "Code queued for execution."

def create_agent() -> None:
    llm = ChatOpenAI(
        model="Qwen/Qwen3.5-4B",
        base_url="http://localhost:8000/v1",
        api_key="1",
    )

    agent = create_deep_agent(
        model=llm,
        tools=[swarm_execute],
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
    global _swarm_controller

    swarm = Swarm()
    _swarm_controller = SwarmController(swarm)
    _swarm_controller.start_execution_task()

    agent = create_agent()

    print("Crazyflie Swarm LLM Console")
    print("Type 'exit', 'quit', or 'q' to quit")
    print(f"Initial state: {swarm.state.name}")

    await console_loop(agent)

    if _swarm_controller is not None:
        await _swarm_controller.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
import argparse
import asyncio

from langchain.tools import tool

from agent import create_agent
from runner.swarm_runner import run_swarm_show

_captured = {"swarm_show_func": None}

# Testbed dimensions in meters — single source of truth for the flying volume.
# Used for the LLM system prompt (so generated setpoints stay inside the safe
# volume) and as the force-field flight boundary.
TESTBED_MIN: tuple[float, float, float] = (-1.5, -1.5, 0.4)  # floor corner (x, y, z)
TESTBED_MAX: tuple[float, float, float] = (1.5, 1.5, 2.0)    # ceiling corner (x, y, z)


def _valid_port(value: str) -> int:
    port = int(value)
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port


@tool(parse_docstring=True)
def swarm_show_execute(swarm_show_func: str) -> str:
    """Execute a swarm show by generating and running a complete script.

    Args:
        swarm_show_func: Python function code for swarm_show(current_time: float).

    Returns:
        Result message with exit code and captured output.
    """
    _captured["swarm_show_func"] = swarm_show_func
    return "Code captured. Will run after LLM finishes."


def _run_agent(
    prompt: str,
    simulate: bool,
    address_offset: int,
    gpu_ip: str,
    gpu_port: int,
) -> None:
    _captured["swarm_show_func"] = None

    agent = create_agent(
        testbed_min=TESTBED_MIN,
        testbed_max=TESTBED_MAX,
        tools=[swarm_show_execute],
        gpu_ip=gpu_ip,
        gpu_port=gpu_port,
    )

    stream = agent.stream_events(
        {"messages": [{"role": "user", "content": prompt}]},
        version="v3",
    )
    for message in stream.messages:
        for token in message.reasoning:
            print(f"[thinking] {token}", end="", flush=True)
        for token in message.text:
            print(token, end="", flush=True)
    print()

    swarm_show_func = _captured["swarm_show_func"]
    if swarm_show_func is None:
        print("LLM did not generate a swarm show function.")
        return

    print("--- Generated swarm_show function ---")
    print(swarm_show_func)
    print("-------------------------------------")

    print("Running experiment...")
    exit_code, stdout, stderr = asyncio.run(
        run_swarm_show(
            swarm_show_func,
            num_drones=4,
            simulated=simulate,
            no_wait=False,
            address_offset=address_offset,
            testbed_min=TESTBED_MIN,
            testbed_max=TESTBED_MAX,
        )
    )
    if stdout:
        print(stdout)
    if stderr:
        print(stderr)
    print(f"Exit code: {exit_code}")


def run() -> None:
    parser = argparse.ArgumentParser(description="Crazyflie Swarm Control")
    parser.add_argument(
        "--address-offset",
        type=int,
        default=0,
        metavar="N",
        help="Offset added to drone address indices",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Run in simulation mode",
    )
    parser.add_argument(
        "--gpu-ip",
        default="134.130.192.85",
        metavar="IP",
        help="IP address or hostname of the GPU PC (default: %(default)s)",
    )
    parser.add_argument(
        "--gpu-port",
        type=_valid_port,
        default=8001,
        metavar="PORT",
        help="Port of the OpenAI-compatible LLM server (default: %(default)s)",
    )
    args = parser.parse_args()

    while True:
        try:
            prompt = input("Enter prompt (empty to quit): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not prompt:
            break
        _run_agent(
            prompt,
            simulate=args.simulate,
            address_offset=args.address_offset,
            gpu_ip=args.gpu_ip,
            gpu_port=args.gpu_port,
        )


if __name__ == "__main__":
    run()

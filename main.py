import argparse
import asyncio
import sys

from langchain.tools import tool

from agent import create_agent
from runner.swarm_runner import run_swarm_show


def run() -> None:
    """Entry point for the CLI swarm control interface."""
    parser = argparse.ArgumentParser(description="Crazyflie Swarm Control")
    parser.add_argument(
        "--address-offset",
        type=int,
        default=0,
        metavar="N",
        help="Offset added to drone address indices (e.g. 2 → connect to addresses 03, 04, ...)",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Run in simulation mode instead of connecting to real hardware",
    )
    args = parser.parse_args()

    prompt = input("Enter prompt: ").strip()
    if not prompt:
        print("No prompt provided.")
        sys.exit(1)

    # Mutable container to capture the generated code from the tool call
    captured = {"swarm_show_func": None}

    @tool(parse_docstring=True)
    def swarm_show_execute(swarm_show_func: str) -> str:
        """Execute a swarm show by generating and running a complete script.

        Args:
            swarm_show_func: Python function code for swarm_show(current_time: float).

        Returns:
            Result message with exit code and captured output.
        """
        captured["swarm_show_func"] = swarm_show_func
        print("\n--- Generated swarm_show function ---")
        print(swarm_show_func)
        print("-------------------------------------\n")
        return "Code captured. Will run after LLM finishes."

    agent = create_agent(tools=[swarm_show_execute])

    print("Running LLM agent...")
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

    swarm_show_func = captured["swarm_show_func"]
    if swarm_show_func is None:
        print("LLM did not generate a swarm show function. Exiting.")
        sys.exit(1)

    print("Running experiment...")
    exit_code, stdout, stderr = asyncio.run(
        run_swarm_show(
            swarm_show_func,
            num_drones=3,
            simulated=args.simulate,
            no_wait=False,
            address_offset=args.address_offset,
        )
    )
    if stdout:
        print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)
    sys.exit(exit_code)


if __name__ == "__main__":
    run()
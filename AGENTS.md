# Project Name

The CrazyMPC project is a demo that demonstrates how LLMs can control robot swarms. If has access to a swarm of Crazyflie quadcopters that it can control via a Pythoin API. The project is structured as follows:
- `console_llm.py`: Main console interface for the LLM to interact with the swarm
- `hardware/swarm_controller.py`: High-level controller that translates LLM commands into swarm API calls
- `hardware/swarm.py`: Low-level API for direct interaction with the Crazyflie swarm

## Code Style

- Use standard Python conventions (PEP 8)

## Architecture

- The LLM interacts with the `SwarmController` to issue commands to the drone swarm
- The `SwarmController` manages the connection and state of the swarm, and translates high-level commands into low-level API calls to the `Swarm` class
- The `Swarm` class handles direct communication with the Crazyflie drones, including connection management, state tracking, and position logging.
- Everything runs in an asyncio event loop, allowing for concurrent command processing and swarm management.
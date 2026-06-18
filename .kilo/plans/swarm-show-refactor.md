# Swarm Show Refactor Plan

## Overview

Replace the dynamic code execution (`SwarmController` with queued code execution) with a simpler model where the LLM writes a `swarm_show(current_time: float)` function that is wrapped into a complete script via Jinja2 template. The script handles all swarm operations: connect, takeoff, run the show loop, land, and disconnect.

## Current Architecture Problems

- `SwarmController` maintains a code queue that executes arbitrary Python code in the LLM execution context
- LLM needs to know swarm internal state and command sequence (connect → takeoff → goto → land)
- Complex state management across LLM commands
- The `swarm_execute` tool just queues code without proper error handling

## New Architecture

### Flow
1. LLM writes `swarm_show(current_time: float) -> tuple[list[tuple[float, float, float]], bool]`
2. Tool wraps this function into a complete script using Jinja2 template
3. Script is written to a temp file and executed
4. Script: connects → takes off → loops calling `swarm_show` → lands → disconnects
5. Tool waits for script completion and returns exit code

## File Changes

### 1. Delete `hardware/swarm_controller.py`
- Remove the queue-based execution model entirely
- No longer needed with direct script generation approach

### 2. Modify `console_llm.py`
- Remove `_swarm_controller` global and `SwarmController` import
- Replace `swarm_execute` tool with `swarm_show_execute` tool
- New tool takes `swarm_show_func` (the function code as string) and:
  - Uses Jinja2 to render it into a complete script template
  - Writes to temp file
  - Runs subprocess and waits
  - Returns the exit code

### 3. Create Jinja2 template `templates/swarm_show_script.py.jinja2`
```python
#!/usr/bin/env python3
"""Auto-generated swarm show script."""
import asyncio
import sys
import numpy as np

sys.path.insert(0, "{{ project_root }}")

from hardware import Swarm
from simulator import SimulatedSwarm

# {{ swarm_show_func }}

async def main():
    SwarmClass = SimulatedSwarm if {{ simulated }} else Swarm
    swarm = SwarmClass()
    
    # Connect
    await swarm.connect("{{ base_address }}", {{ num_drones }})
    
    # Takeoff
    await swarm.takeoff()
    
    # Run show loop
    start_time = asyncio.get_running_loop().time()
    while True:
        elapsed = asyncio.get_running_loop().time() - start_time
        setpoints, finished = swarm_show(elapsed)
        swarm.goto(setpoints)
        if finished:
            break
        await asyncio.sleep(0.1)
    
    # Land and disconnect
    await swarm.land()
    await swarm.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

### 4. Update `hardware/swarm.py`
- Make `connect()`, `takeoff()`, `land()`, `disconnect()` blocking async methods
- Remove the internal task callbacks - these methods should await internally
- `connect()` becomes `async def connect(...)` and awaits connection completion
- `takeoff()` becomes `async def takeoff()` and awaits takeoff completion
- `land()` becomes `async def land()` and awaits landing completion
- `disconnect()` is already async, keep as is

### 5. Update `simulator/swarm.py`
- Make the same methods blocking async as in `Swarm`
- `connect()` - async, awaits immediately
- `takeoff()` - async, awaits immediately
- `land()` - async, awaits immediately

### 6. Update `hardware/__init__.py`
- Remove `SwarmController` from exports

### 7. Add `goto` method (optional)
- Add `goto(setpoints)` method to both `Swarm` and `SimulatedSwarm` as a simple alias to `safegoto`
- This makes the API cleaner for LLM code: `swarm.goto(positions)` instead of `swarm.safegoto(positions)`

## Tool Interface

### New `swarm_show_execute` tool
```python
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
```

## LLM System Prompt Update

New prompt focusing on `swarm_show` function:
```
You control a Crazyflie drone swarm. Write a function `swarm_show(current_time: float)` that returns:
- A list of (x, y, z) setpoints for each drone
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
```

## Dependencies to Add

Add jinja2 to requirements (check if already present):
```
jinja2
```

## Implementation Order

1. Modify `hardware/swarm.py` to make connect/takeoff/land blocking async methods
2. Modify `simulator/swarm.py` similarly
3. Create the Jinja2 template file at `templates/swarm_show_script.py.jinja2`
4. Create the new `swarm_show_execute` tool in `console_llm.py`
5. Remove `SwarmController` and update imports
6. Update system prompt
7. Clean up `hardware/__init__.py`
8. Add `jinja2` to `pyproject.toml` dependencies
9. Add `goto` method to both swarm implementations
10. Test the flow with simulated swarm

## Integration Notes

- The visualization module will need to be adapted or run as a separate process since the generated script runs independently
- Consider keeping a simple subprocess-based visualization for the demo
- The LLM doesn't need to know about `asyncio` or swarm internals - just write the pure `swarm_show` function

## Error Handling

- The tool should capture stdout/stderr from the subprocess
- Return both exit code and any error output
- Script should have try/except with proper cleanup on errors
# UI Tool Call Refactor Plan

## Problem Statement
The UI does not work as specified. After sending a prompt, the LLM correctly calls the tool with the right code and simulates it, but:
1. The code written by the LLM is not shown in the code widget after the tool response
2. Clicking the "Simulate" button shows an error "code is not available"

## Root Cause Analysis
The `swarm_show_execute` tool in `console_llm.py` generates and executes a script in a subprocess, returning only execution result. The UI has no visibility into tool calls because `stream_events` only iterates over messages, not tool invocation events. The stored `_swarm_show_code` is never properly set when tools are used.

## Solution Architecture

### Core Concept
Create a tool that:
1. Receives code via `swarm_show_func` argument
2. Immediately passes code to UI window (via callback/window reference)
3. Runs simulation with `no_wait=True` for fast preview
4. Uses unified runner for both tool calls and button clicks

### 1. Create `runner/swarm_runner.py` - Unified Runner Module
```python
def generate_script(swarm_show_func: str, num_drones: int = 3, simulated: bool = True, no_wait: bool = False) -> str:
    """Generate script content from swarm_show function code."""

async def run_swarm_show(
    swarm_show_func: str,
    num_drones: int = 3,
    simulated: bool = True,
    no_wait: bool = False
) -> tuple[int, str, str]:
    """Generate and execute script, returning (exit_code, stdout, stderr)."""
```

### 2. Update `templates/swarm_show_script.py.jinja2`
Add `no_wait` flag - when true, uses `asyncio.sleep(0)` for instant execution:
```jinja2
{%- if no_wait -%}
await asyncio.sleep(0)
{%- else -%}
await asyncio.sleep(0.1)
{%- endif -%}
```

### 3. Create `ui/swarm_tool.py` - UI-Aware Tool
A tool factory that creates a tool with window reference:
```python
def create_swarm_tool(window: MainWindow | None = None) -> Callable:
    """Create swarm_show_execute tool bound to a window."""
    @tool(parse_docstring=True)
    def swarm_show_execute(swarm_show_func: str, num_drones: int = 3, simulated: bool = True, no_wait: bool = True) -> str:
        if window:
            window.set_swarm_show_code(swarm_show_func)
        exit_code, stdout, stderr = asyncio.run(run_swarm_show(swarm_show_func, num_drones, simulated, no_wait))
        return f"Exit code: {exit_code}\n{stdout}\n{stderr}".strip()
    return swarm_show_execute
```

### 4. Update `ui/main_window.py` - Add `set_swarm_show_code` method
```python
def set_swarm_show_code(self, code: str) -> None:
    """Receive code from tool call and update UI."""
    self._swarm_show_code = code
    self._code.set_code(code)
```

### 5. Update `ui/main.py` - Use UI-aware tool creation
```python
from ui.swarm_tool import create_swarm_tool
agent = create_agent(include_generate_script=False)
agent.tools = [create_swarm_tool(window)]  # Pass window after creation
```

### 6. Delete `console_llm.py` - Console Interface No Longer Needed

### 7. Simplify `ui/swarm_executor.py`
Remove `generate_script`, import from runner module.

## Implementation Steps

1. **Create `runner/swarm_runner.py`**
   - Move `generate_script` logic, add `run_swarm_show`

2. **Update `templates/swarm_show_script.py.jinja2`**
   - Add `no_wait` variable, conditional sleep

3. **Create `ui/swarm_tool.py`**
   - Tool factory with window callback

4. **Update `ui/main_window.py`**
   - Add `set_swarm_show_code` method

5. **Update `ui/main.py`**
   - Use `create_swarm_tool` with window reference

6. **Delete `console_llm.py`**

7. **Update `ui/__init__.py`** and `ui/swarm_executor.py`**
   - Use runner module

## Testing
1. Run UI with simulated mode
2. Send LLM prompt - verify code appears in widget immediately
3. Verify tool execution with `no_wait=True` is fast
4. Click Simulate button - verify no error
5. Verify output appears in chat
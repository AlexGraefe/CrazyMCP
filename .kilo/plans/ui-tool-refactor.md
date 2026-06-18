# UI Tool Call Refactor Plan

## Problem Statement
The UI does not work as specified. After sending a prompt, the LLM correctly calls the tool with the right code and simulates it, but:
1. The code written by the LLM is not shown in the code widget after the tool response
2. Clicking the "Simulate" button shows an error "code is not available"

## Root Cause Analysis
The current architecture has two separate execution paths:
1. **Console LLM path** (`console_llm.py`): `swarm_show_execute` tool generates and runs a subprocess, returning execution result
2. **UI path** (`ui/main_window.py`): LLM response is parsed to extract `swarm_show` code, which is then passed to `SwarmExecutor`

The tool call happens in a subprocess context, so the code never reaches the UI. The UI tries to extract code from LLM response after the fact, but the timing/state management is broken.

## Solution Architecture

### 1. Create Unified Swarm Runner (`runner/swarm_runner.py`)
A clean wrapper module that encapsulates:
- Script generation from `swarm_show` function code
- Execution of generated scripts with configurable options

```python
# runner/swarm_runner.py
async def run_swarm_show(
    swarm_show_func: str, 
    num_drones: int = 3, 
    simulated: bool = True, 
    no_wait: bool = False
) -> tuple[int, str, str]:
    """Execute swarm_show function, returning (exit_code, stdout, stderr).
    
    Args:
        swarm_show_func: The swarm_show function code
        num_drones: Number of drones to control
        simulated: Use simulated vs hardware swarm
        no_wait: If True, skip delays for fast execution (useful for previews)
    """
```

### 2. Create Swarm Executor Window Wrapper (`ui/swarm_window.py`)
A class that wraps swarm execution for the UI context:
- Holds the current `swarm_show` code
- Provides methods `execute(simulated=True)` and `execute(simulated=False)`
- Used by both UI buttons (Simulate/Fly) and the tool call

### 3. Update Jinja2 Template (`templates/swarm_show_script.py.jinja2`)
- Add `no_wait` flag
- When `no_wait=True`: use `asyncio.sleep(0)` instead of `asyncio.sleep(0.1)` for fast execution
- Remove unnecessary delays in simulated mode

### 4. Replace Tool in `console_llm.py`
- Remove `generate_script` tool (no longer needed)
- Update `swarm_show_execute` to:
  - Accept `no_wait` parameter (default False)
  - Use the unified runner
  - Still run subprocess and return result
  - The UI tool should directly pass code to the window (handled by agent setup)

### 5. Update UI (`ui/main_window.py`)
- Create `SwarmWindow` wrapper at initialization
- Pass `_swarm_show_code` to tool calls (for LLM to preview)
- On tool invocation: update stored code and set it in code widget
- Use runner for simulate/fly button execution

### 6. Clean Up
- Remove `SwarmExecutor.extract_swarm_show_code` (delegated to runner or kept for fallback)
- Consolidate script generation logic into single location
- Ensure both simulated and real modes use the same execution path

## Implementation Steps

### Step 1: Create `runner/swarm_runner.py`
- Move `generate_script` function from `ui/swarm_executor.py` and `console_llm.py` into this module
- Create async `run_swarm_show()` function that handles both simulation and execution
- Add `no_wait` flag support in template rendering

### Step 2: Update `templates/swarm_show_script.py.jinja2`
- Add `no_wait` variable
- Conditional sleep: `{{ asyncio.sleep(0 if no_wait else 0.1) }}`

### Step 3: Create `ui/swarm_window.py`
- `SwarmWindow` class that holds code and swarm state
- `set_code(code: str)` - store the swarm_show function
- `execute(simulated: bool, no_wait: bool = False)` - run the stored code
- `get_code() -> str` - retrieve stored code

### Step 4: Update `ui/swarm_executor.py`
- Remove code extraction logic (keep in SwarmWindow or move to runner)
- Simplify to just run the script file using runner module
- Remove duplicate `generate_script` function

### Step 5: Update `console_llm.py`
- Remove `generate_script` tool
- Update `swarm_show_execute` to use runner module
- Add `no_wait` parameter

### Step 6: Update `ui/main_window.py`
- Initialize `SwarmWindow` with runner reference
- On LLM response: store code in `SwarmWindow` and display in code widget
- Simulate/Fly buttons call `SwarmWindow.execute()` directly

## File Changes Summary

| File | Action |
|------|--------|
| `runner/swarm_runner.py` | Create new unified runner module |
| `ui/swarm_window.py` | Create new window wrapper class |
| `templates/swarm_show_script.py.jinja2` | Add `no_wait` flag |
| `ui/swarm_executor.py` | Simplify, use runner |
| `console_llm.py` | Remove `generate_script`, use runner |
| `ui/main_window.py` | Integrate SwarmWindow, fix code display |

## Testing
1. Run UI with simulated mode
2. Send LLM prompt requesting swarm_show code
3. Verify code appears in code widget
4. Click Simulate button - verify no error
5. Verify output appears in chat
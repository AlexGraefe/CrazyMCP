# CLI Replacement Plan

## Goal
Replace the buggy PyQt6 UI with a simple command-line interface that:
1. Accepts user prompts via console input
2. Sends prompts to LLM and receives generated code
3. Prints the generated `swarm_show` code
4. Asks user to confirm execution (Enter or 'y' to run)
5. Executes the show on hardware (simulated=False)
6. Terminates after completion

## Changes Required

### Delete UI Files
- `ui/main_window.py` - Main window with splitter layout and buttons
- `ui/chat_widget.py` - Chat interface widget
- `ui/code_widget.py` - Code display widget
- `ui/swarm_executor.py` - QThread executor for async swarm runs
- `ui/swarm_tool.py` - UI-bound tool wrapper
- `ui/__init__.py` - UI package init (empty)

### Modify Files

#### `main.py` - Replace with CLI entry point
- Remove all PyQt6 imports and QApplication setup
- Add `--simulated` flag (default False for hardware mode)
- Add `--address-offset` argument (keep existing)
- Create simple async loop:
  1. Prompt user for input
  2. Invoke agent and stream response
  3. Extract code from response
  4. Print code to console
  5. Prompt for confirmation
  6. Run swarm show on hardware if confirmed
  7. Exit on completion

#### `agent.py` - Simplify for CLI
- Remove UI-specific tool wrapper (`get_show_swarm_execute`)
- Add helper to extract code from LLM response (reuse logic from `SwarmExecutor.extract_swarm_show_code`)
- Create a single `invoke_agent` function that returns the generated code

## Implementation Steps

1. Create new `main.py` with CLI logic
2. Modify `agent.py` to add code extraction and simplify tool creation
3. Delete `ui/` directory
4. Test with simulated mode first

## CLI Flow

```
$ python main.py --address-offset 0
> Enter prompt: make the drones fly in a circle
[LLM thinking...]
Generated swarm_show code:
------------------------
def swarm_show(current_time: float):
    import math
    x = 0.5 * math.cos(current_time)
    y = 0.5 * math.sin(current_time)
    yaws = [math.sin(current_time * 0.5), -math.sin(current_time * 0.5), 0.0]
    setpoints = [(x, y, 1.0), (-x, -y, 1.0), (0, 0, 1.0)]
    finished = current_time > 10.0
    return setpoints, yaws, finished
------------------------
Run on hardware? [y/N]: y
[Running swarm show...]
[Swarm show completed]
$
```
# PyQt6 Swarm Control UI Implementation Plan

## Overview
Create a PyQt6 desktop application with a chat interface for LLM interaction and code display, plus buttons to simulate or fly the drone swarm.

## File Structure
```
ui/
├── __init__.py
├── main.py              # Entry point, QApplication setup
├── main_window.py       # Main window with splitter layout
├── chat_widget.py       # Chat interface (left panel)
├── code_widget.py       # Code display (right panel)
└── swarm_executor.py     # Thread-safe swarm script execution
```

## Components

### 1. SwarmExecutor (`ui/swarm_executor.py`)
A thread-safe executor that runs swarm shows asynchronously:
- `execute_simulate(func_code, num_drones)` - Runs simulation, returns when complete
- `execute_fly(func_code, num_drones)` - Runs on real hardware, returns when complete
- Uses QThread + asyncio integration to not block UI
- Emits signals for output and completion

### 2. ChatWidget (`ui/chat_widget.py`)
Left panel containing:
- QTextEdit/QPlainTextEdit for message history (read-only, dark theme)
- QLineEdit for user input with Enter to send
- Timestamps and LLM/spinner indicators
- Appends user messages (You:) and LLM responses

### 3. CodeWidget (`ui/code_widget.py`)
Right panel containing:
- QTextEdit/QPlainTextEdit for code display (read-only)
- Shows the generated `swarm_show` function from LLM
- Syntax highlighting via QTextEdit (optional)

### 4. MainWindow (`ui/main_window.py`)
Main application window with:
- Horizontal QSplitter dividing chat (left) and code (right)
- "Simulate" button - runs generated code with `simulated=True`
- "Fly" button - runs generated code with `simulated=False`
- Status bar showing connection state
- Button state management (disabled during execution)

Layout:
```
+---------------------------------------------------------------+
| Menu Bar                                                      |
+--------+------------------------------------------------------+
| Chat   | Code Display                                           |
|        |                                                      |
| You:   | def swarm_show(current_time: float):                   |
| prompt |     ...                                                |
|        |                                                      |
| LLM:   |                                                      |
| respon |                                                      |
| se     |                                                      |
+--------+------------------------------------------------------+
| [Simulate] [Fly] [Clear]                                     |
+---------------------------------------------------------------+
```

## Integration with Existing Code

### LLM Integration
- Reuse `console_llm.py`'s `create_agent()` and `SYSTEM_PROMPT`
- Modify `swarm_show_execute` to be callable without running subprocess (return script content)
- Or create a new tool function that returns code without execution

### Execution Flow
1. User enters prompt in chat widget
2. UI calls agent.ainvoke() (in thread)
3. Extract `swarm_show` function from LLM response
4. Display code in CodeWidget
5. User clicks "Simulate" or "Fly"
6. UI generates complete script via template
7. Executes in QThread with asyncio
8. Output streamed to chat widget
9. Button re-enabled when complete

## Key Implementation Details

### Async Integration
```python
# In SwarmExecutor
async def run_script(self, script_content, simulated):
    # Create temporary file
    # Run asyncio subprocess
    # Capture output
    # Emit signals for progress
```

### Tool Modification
Create `generate_script()` tool that returns script content without running:
```python
@tool
def generate_script(swarm_show_func: str, num_drones: int = 3, simulated: bool = True) -> str:
    # Render template and return script content
```

### UI Threading
- Use QThread for long-running operations
- Use signals/slots to communicate with main thread
- Keep UI responsive during simulation/flight

## Dependencies
- PyQt6 (primary UI framework)
- asyncio (existing)
- jinja2 (existing, for templates)
- langchain/deepagents (existing)

## Implementation Steps

1. **Create ui/ directory and __init__.py**
2. **Create swarm_executor.py** - Thread-safe script runner
3. **Create chat_widget.py** - Chat interface component
4. **Create code_widget.py** - Code display component
5. **Create main_window.py** - Main window with layout
6. **Create main.py** - Entry point with QApplication
7. **Modify console_llm.py** - Add script generation function
8. **Test simulate button** - Verify simulation runs correctly
9. **Test fly button** - Verify hardware execution (when available)
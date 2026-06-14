# Plan: Swarm-LLM Console Integration

## Goal
Create a console-based interface where a user can control the Crazyflie swarm via natural language, with an LLM generating and executing Python code to control the swarm in real-time.

## Current Architecture Analysis

### Swarm Class (`hardware/swarm.py`)
- **Async State Machine** with states: `UNCONNECTED` → `CONNECTED` → `FLYING` → `LANDED`/`ERROR`
- **Key methods**:
  - `connect(base_address: str, num_drones: int)` - Non-blocking, starts async connection
  - `start()` - Non-blocking, begins takeoff sequence
  - `safegoto(positions: list[tuple[float, float, float] | None])` - Updates target positions (non-blocking)
  - `land()` - Non-blocking, navigates to pads then lands
  - `emergency_land()` - Async, immediate landing
  - `disconnect()` - Async, disconnects all drones
- **Background task**: `_ff_task` runs `_ff_loop_impl()` continuously during flight

### Existing LLM Integration (`crazy_llm.py`)
- Uses `langchain` and `deepagents` libraries
- Demonstrates basic tool integration with `swarm_execute`
- Shows conversation flow with `agent.invoke()`

## Proposed Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Console    │────▶│    LLM       │────▶│  Exec Sandbox   │
│  (asyncio)  │     │  (LangChain) │     │  (exec())       │
└─────────────┘     └──────────────┘     └────────┬────────┘
                                                  │
                                                  ▼
                                        ┌─────────────────┐
                                        │  Swarm Instance │
                                        │  (background)   │
                                        └─────────────────┘
```

## Implementation Plan

### 1. Create `SwarmController` wrapper (`hardware/swarm_controller.py`)

A thread-safe wrapper that provides a stable API for the LLM to control the swarm:

```python
class SwarmController:
    def __init__(self, swarm: Swarm): ...
    
    # Synchronous wrappers for async methods (using asyncio.run_coroutine_threadsafe)
    def connect(self, base_address: str, num_drones: int) -> str:
        """Connect to drones. Returns status string."""
    
    def takeoff(self) -> str:
        """Start the takeoff sequence."""
    
    def land(self) -> str:
        """Land all drones."""
    
    def goto(self, x: float, y: float, z: float) -> str:
        """Navigate all drones to a position."""
    
    def emergency_stop(self) -> str:
        """Immediately land all drones."""
    
    def disconnect(self) -> str:
        """Disconnect all drones."""
    
    def get_state(self) -> str:
        """Return current swarm state."""
    
    def get_positions(self) -> list[tuple[float, float, float]] | None:
        """Return current virtual positions."""
```

### 2. Create Console Interface (`console_llm.py`)

Main entry point that:
- Initializes and runs the Swarm in a background asyncio task
- Creates an asyncio event loop for console input (non-blocking)
- Sets up the LLM agent with `swarm_controller` as a tool
- Handles user input and routes to LLM

```python
async def main():
    # Create swarm and controller
    swarm = Swarm()
    controller = SwarmController(swarm)
    
    # Start event loop for console
    loop = asyncio.get_running_loop()
    
    # Create LLM agent with swarm_execute tool
    # Tool has access to controller in closure
    
    # Main console loop:
    # - Read user input (non-blocking via run_in_executor)
    # - Send to LLM
    # - LLM generates code
    # - Execute code with exec() with controller in namespace
    # - Display result
```

### 3. LLM Tool Integration

Modify the exec approach to:
- Provide the `swarm_controller` in the execution namespace
- Validate generated code before execution
- Return execution results and errors to LLM

```python
@tool
def swarm_execute(code: str) -> str:
    """Execute Python code to control the swarm."""
    namespace = {
        "swarm": swarm_controller,
        "asyncio": asyncio,
        "np": np,
    }
    try:
        exec(code, namespace)
        return "Code executed successfully."
    except Exception as e:
        return f"Error: {e}"
```

### 4. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Run Swarm in background task** | Allows continuous force-field loop while accepting user commands |
| **Synchronous controller API** | Simplifies LLM tool integration; wraps async methods internally |
| **Code generation vs direct tool calls** | More flexible for complex multi-step swarm operations |
| **exec() for execution** | Allows LLM to write full scripts, not just single commands |

### 5. Security Considerations

Since exec() is used:
- The code only has access to the `controller` and safe modules (`asyncio`, `numpy`)
- No filesystem or network access exposed to execution namespace
- Errors are caught and reported, not allowed to crash the system

### 6. Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `hardware/swarm_controller.py` | Create | Thread-safe wrapper for Swarm |
| `console_llm.py` | Create | Console interface + LLM integration |
| `crazy_llm.py` | Modify | Consolidate or keep as reference |

### 7. Implementation Steps

1. **Create SwarmController class** (`hardware/swarm_controller.py`)
   - Wrap Swarm async methods with synchronous-safe versions
   - Add convenience methods for common operations (takeoff, goto, etc.)
   - Handle state validation (e.g., can't takeoff if already flying)

2. **Create console interface** (`console_llm.py`)
   - Set up asyncio event loop
   - Initialize Swarm in background
   - Configure LLM agent with tools
   - Main input loop with proper async handling

3. **Integration testing**
   - Test connection flow
   - Test while-drone-is-flying control
   - Test emergency stop
   - Test error handling

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| **Thread safety with asyncio** | Use `asyncio.run_coroutine_threadsafe()` for cross-thread calls |
| **LLM generates invalid code** | Catch exceptions, return to LLM for correction |
| **Blocking exec() call** | Run in executor or separate thread |
| **State desynchronization** | Controller reads directly from Swarm state property |
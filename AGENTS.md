# CrazyMCP

A demo project demonstrating how LLMs can control a swarm of Crazyflie quadcopters via a Python API. The system provides a PyQt6 UI where users can describe desired drone formations and the LLM generates and executes flight control code.

## Code Style

- Use standard Python conventions (PEP 8)

## Architecture

- **main.py** - Entry point: creates QApplication, MainWindow, and LLM agent
- **ui/** - PyQt6 UI components
  - **main_window.py** - Main window with horizontal splitter for chat/code panels and Simulate/Fly buttons
  - **chat_widget.py** - Left panel for LLM conversation interface
  - **code_widget.py** - Right panel for displaying generated swarm_show code
  - **swarm_executor.py** - QThread executor for running swarm scripts without blocking UI
  - **swarm_tool.py** - Tool wrapper that bridges UI window with swarm execution
- **agent.py** - Creates deep agent with swarm_show_execute tool, uses Qwen LLM via LangChain/OpenAI-compatible API
- **runner/swarm_runner.py** - Generates scripts from Jinja2 template and runs in subprocess
- **templates/swarm_show_script.py.jinja2** - Template for auto-generated execution scripts
- **hardware/** - Real drone control implementation
  - **swarm.py** - Real Swarm - controls actual Crazyflie drones via cflib2
  - **swarm_base.py** - Abstract SwarmBase class and SwarmState enum defining the swarm interface
  - **swarm_force_field_control.py** - Force-field navigation controller for collision avoidance
  - **swarm_logger.py** - Position logging task for real drones
- **simulator/swarm.py** - SimulatedSwarm - mock implementation for testing without hardware
- **visualization.py** - SwarmVisualizer for optional 3D visualization
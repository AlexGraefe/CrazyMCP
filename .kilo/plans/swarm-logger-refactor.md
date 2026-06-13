# Plan: Extract LoggingTask to swarm_logger.py

## Goal
Create `LoggingTask` class in `swarm_logger.py` to encapsulate live logging functionality, enabling parallel log stream reading without skipping measurements.

## Analysis

### Current Logging Implementation in swarm.py
1. **Properties used**:
   - `_live_log_streams: list[object]` - list of active log streams
   - `_latest_positions: list[dict[str, Any]]` - latest log data per drone

2. **Key methods to extract**:
   - `_start_live_position_logging()` (lines 482-493) - creates and starts log streams
   - `_stop_live_position_logging()` (lines 495-502) - stops all streams
   - `_read_pad_position()` (lines 464-480) - pattern for single-read logging

3. **Current issue**: The `_ff_loop_impl` method doesn't actively read from `_live_log_streams` - it only initializes them. The data flow for live logging during flight is incomplete.

## Design

### LoggingTask Class

```python
class LoggingTask:
    def __init__(self, crazyflies: list, variables: list[str], interval_ms: int)
    async def start() -> None  # continuous background logging
    async def read_once() -> list[dict | None]  # one-shot parallel read
    def get_log(cf_index: int) -> dict | None
    async def stop() -> None
    def __del__() -> None  # calls stop()
```

### Key Implementation Details

1. **Parallel next() calls**: Use `asyncio.gather()` to call `log_stream.next()` on all streams simultaneously, avoiding sequential waiting that would cause measurement skips.

2. **Continuous logging loop**: Each stream needs an async task that:
   - Calls `await log_stream.next()` 
   - Extracts `data` property
   - Stores in internal `_latest_logs` list at the correct index

3. **Data storage**: `_latest_logs: list[dict | None]` - one entry per Crazyflie, updated atomically.

4. **Stop mechanism**: Cancel all logging tasks, stop all streams, clear internal state.

## Changes to swarm.py

### Remove/Replace
- Remove `_start_live_position_logging()` method
- Remove `_stop_live_position_logging()` method
- Remove `_live_log_streams` and `_latest_positions` attributes
- Modify `_read_pad_position()` to use `LoggingTask.read_once()`

### Add
- Import `LoggingTask` from `.swarm_logger`
- Add `_position_logger: LoggingTask` attribute for live position logging
- Modify `_takeoff_impl()` to use `LoggingTask` for position logging
- Modify `_land_impl()` and error handlers to call `await self._position_logger.stop()`
- Update initial virtual position setup to use `read_once()` pattern

## Implementation Steps

1. Create `LoggingTask` class in `swarm_logger.py`:
   - `__init__` with crazyflies list, variables list, interval
   - `_tasks: list[asyncio.Task]` for parallel log readers
   - `_latest_logs: list[dict | None]` for data access
   - `_running: bool` flag for stop detection

2. Implement `start()`:
   - Initialize `_latest_logs` list
   - Create log block for each Crazyflie with specified variables
   - Start each log stream with given interval
   - Spawn async task per stream that loops: `next_data = (await stream.next()).data; _latest_logs[i] = next_data`

3. Implement `read_once()`:
   - Create temporary log blocks/streams
   - Use `asyncio.gather()` to read all streams in parallel
   - Extract and return data from each stream
   - Clean up temporary streams

4. Implement `get_log(cf_index)`:
   - Return `_latest_logs[cf_index]` or `None`

5. Implement `stop()`:
   - Set `_running = False`
   - Cancel all tasks, wait for completion
   - Stop all streams (handle sync vs async stop methods)

6. Implement `__del__()`:
   - Synchronously stop if running (create sync wrappers)

## User Answers

1. **One-shot logging**: Yes, but ensure it's reusable - can call `start()` multiple times, and one-shot read returns value from previous `start()` call.

2. **FF loop integration**: No - keep as separate concern.

3. **get_log() return**: Direct reference (not a copy).

4. **Reusability**: LoggingTask should be reusable after `stop()`.
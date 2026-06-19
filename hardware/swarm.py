"""Swarm hardware controller with an async state machine.

The :class:`Swarm` class owns all Crazyflie connection and flight logic.
It reports progress back to whatever object implements :class:`SwarmGUI`
(normally :class:`gui.gui.MainWindow`).
"""

import asyncio

import numpy as np
from .swarm_base import SwarmBase, SwarmState, scale_setpoint
from .swarm_logger import LoggingTask
from .swarm_force_field_control import ForceFieldController

from cflib2 import Crazyflie, LinkContext
from cflib2.toc_cache import FileTocCache


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TAKEOFF_HEIGHT = 1.0
TAKEOFF_DURATION = 2.0
LOG_INTERVAL = 100  # ms
STAGGER_STRIDE = 5   # launch/land every Nth drone per round (round 0: idx 0,4,8…; round 1: 1,5,9…)
STAGGER_DELAY  = TAKEOFF_DURATION + 0.5  # seconds between stagger groups
LED_COLORS = [0x00FF0000, 0x0000FF00, 0x000000FF]  # Red, Green, Blue (WRGB8888, cycles for >3 drones)

# -- Force-field navigation constants ----------------------------------------
FF_LOG_INTERVAL             = 50     # ms – position-logger rate during goto
FF_D_MIN                    = 0.5    # minimum effective distance for repulsion
FF_D_MAX                    = 0.4    # distance threshold for repulsive force onset
FF_K_REPULSIVE              = 1.5    # repulsive force gain
FF_K_ATTRACTIVE             = 2.0    # attractive force gain
FF_K_BOUNDARY               = 3.0    # boundary repulsive force gain
FF_WAYPOINT_INTERVAL        = 0.1    # seconds between go_to commands
FF_VIRTUAL_UPDATES_PER_GOTO = 10     # force-field steps per go_to command
FF_VIRTUAL_UPDATE_INTERVAL  = FF_WAYPOINT_INTERVAL / FF_VIRTUAL_UPDATES_PER_GOTO
FF_MAX_VELOCITY             = 0.5    # m/s cap on the virtual velocity
FF_POSITION_TOLERANCE       = 0.05   # m – considered "reached"
FF_BOUNDARY_MIN             = np.array([-1.5, -1.5, 0.1])
FF_BOUNDARY_MAX             = np.array([ 1.5,  1.5, 2.0])


# ---------------------------------------------------------------------------
# Swarm
# ---------------------------------------------------------------------------

class Swarm(SwarmBase):
    """Async state machine that controls a Crazyflie swarm.

    Public API::

        swarm = Swarm(gui)
        swarm.connect("radio://0/80/2M/E7E7E7E7E7", 3)
        swarm.start()                          # arm + take off; starts FF loop
        swarm.safegoto([(x, y, z), ...])       # update targets (non-blocking)
        swarm.land()                           # navigate home, then land
        await swarm.emergency_land()
        await swarm.disconnect()

    Once :meth:`start` completes the take-off sequence a background
    force-field loop runs indefinitely.  :meth:`safegoto` merely updates the
    target positions consumed by that loop.  :meth:`land` redirects the loop
    toward the pad positions, waits until the virtual model is within
    tolerance, stops the loop, and issues the land command.
    """

    def __init__(self) -> None:
        self._state = SwarmState.UNCONNECTED
        self._connected_cfs: list[object] = []
        self._link_context: object | None = None
        self._position_logger: LoggingTask | None = None
        self._ff_task: asyncio.Task | None = None
        self._pad_positions: list[tuple[float, float, float]] = []
        self._virtual_positions: list[np.ndarray] = []
        self._target_positions: list[np.ndarray | None] = []

    # -- State ---------------------------------------------------------------

    @property
    def state(self) -> SwarmState:
        return self._state

    def _set_state(self, state: SwarmState) -> None:
        print(f"[Swarm] {self._state.name} -> {state.name}")
        self._state = state

    # -- Public API ----------------------------------------------------------

    def get_positions(self) -> list[tuple[float, float, float]] | None:
        if not self._position_logger:
            return None
        positions = []
        for i in range(len(self._connected_cfs)):
            log = self._position_logger.get_log(i)
            if log:
                positions.append((
                    float(log.get("stateEstimate.x", 0.0)),
                    float(log.get("stateEstimate.y", 0.0)),
                    float(log.get("stateEstimate.z", 0.0))
                ))
            else:
                positions.append((0.0, 0.0, 0.0))
        return positions

    async def connect(self, base_address: str, num_drones: int) -> None:
        """Start connecting to *num_drones* drones derived from *base_address*.

        Returns when connection is complete.
        """
        if self._state != SwarmState.UNCONNECTED:
            return
        await self._connect_impl(base_address, num_drones)

    async def _connect_impl(self, base_address: str, num_drones: int) -> None:
        """Internal coroutine that performs the actual connection sequence."""
        if self._connected_cfs:
            await self._disconnect_all()

        self._link_context = LinkContext()
        uris = [f"{base_address}{index:02X}" for index in range(1, num_drones + 1)]

        try:
            self._connected_cfs = list(
                await asyncio.gather(
                    *[
                        Crazyflie.connect_from_uri(
                            self._link_context,
                            uri,
                            FileTocCache("cache"),
                        )
                        for uri in uris
                    ]
                )
            )
        except Exception as exc:
            await self._disconnect_all()
            self._set_state(SwarmState.ERROR)
            return

        print(f"Connected to {len(self._connected_cfs)} drone(s): {', '.join(uris)}")
        self._set_state(SwarmState.CONNECTED)

    async def disconnect(self) -> None:
        """Disconnect all drones.

        Cancels the force-field loop first.
        Transitions: * → UNCONNECTED.
        """
        await self._cancel_ff_loop()
        await self._disconnect_all()
        self._set_state(SwarmState.UNCONNECTED)

    async def emergency_land(self) -> None:
        """Immediately land all connected drones regardless of current state.

        Cancels the force-field loop first.
        Transitions: * → CONNECTED (so the operator can reconnect and retry).
        """
        await self._cancel_ff_loop()
        if not self._connected_cfs:
            return

        self._set_state(SwarmState.LANDED)
        print("Emergency land: commanding all drones to land...")
        try:
            await asyncio.gather(
                *[
                    cf.high_level_commander().land(0.0, None, 2.0, None)
                    for cf in self._connected_cfs
                ],
                return_exceptions=True,
            )
            await asyncio.sleep(3.0)
            await asyncio.gather(
                *[cf.high_level_commander().stop(None) for cf in self._connected_cfs],
                return_exceptions=True,
            )
            await asyncio.gather(
                *[cf.platform().send_arming_request(False) for cf in self._connected_cfs],
                return_exceptions=True,
            )
        except Exception as exc:
            print(f"Emergency land error: {exc}")
        finally:
            if self._position_logger:
                await self._position_logger.stop()
            self._set_state(SwarmState.CONNECTED)

    async def land(self) -> None:
        """Redirect drones to their pad positions and land.

        Redirects the force-field loop toward the pad positions + 1 m, waits
        until the virtual model is within tolerance, stops the loop, and issues
        the land command.
        """
        if self._state != SwarmState.FLYING:
            return
        await self._land_impl()

    async def _land_impl(self) -> None:
        """Redirect FF loop toward pads, wait until there, stop loop, land."""
        try:
            print(f"landing: redirecting toward pad positions...: {self._pad_positions}")
            if self._pad_positions:
                # Point the running FF loop toward above-pad positions.
                self._target_positions = [
                    np.array([x, y, z + 1.0]) for x, y, z in self._pad_positions
                ]
                # Block until the virtual model says all drones are close enough.
                await self._wait_for_targets(timeout=30.0)

            # Stop the FF loop before issuing the firmware land command.
            await self._cancel_ff_loop()

            for i, cf in enumerate(self._connected_cfs):
                param = cf.param()
                param.set("stabilizer.controller", 2)
            await asyncio.sleep(0.5)

            await asyncio.gather(
                *[
                    self._connected_cfs[i].high_level_commander().go_to(
                        x,
                        y,
                        z + 1.0,
                        0.0,
                        2.0,
                        relative=False,
                        linear=True,
                        group_mask=None,
                    )
                    for i, (x, y, z) in enumerate(self._pad_positions)
                ],
                return_exceptions=True,
            )

            await asyncio.sleep(2.0 + 0.5)

            print("Landing drones...")
            await asyncio.gather(
                *[
                    cf.high_level_commander().land(0.0, None, 4.0, None)
                    for cf in self._connected_cfs
                ]
            )
            await asyncio.sleep(4.0 + 0.5)

            await asyncio.sleep(1.0)
            await asyncio.gather(
                *[cf.high_level_commander().stop(None) for cf in self._connected_cfs],
                return_exceptions=True,
            )
            await asyncio.gather(
                *[cf.platform().send_arming_request(False) for cf in self._connected_cfs],
                return_exceptions=True,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._set_state(SwarmState.ERROR)
            return
        finally:
            if self._position_logger:
                await self._position_logger.stop()
        self._set_state(SwarmState.CONNECTED)

    async def takeoff(self) -> None:
        """Arm all connected drones, take off, and start the force-field loop.

        After the take-off sequence completes the force-field background loop
        runs until :meth:`land`, :meth:`emergency_land`, or :meth:`disconnect`
        is called.
        """
        if self._state != SwarmState.CONNECTED:
            return
        await self._takeoff_impl()

    async def _takeoff_impl(self) -> None:
        """Arm drones, lift to hover height, then spawn the FF background loop."""
        self._set_state(SwarmState.FLYING)
        try:
            print("Applying controller parameters for takeoff...")
            for i, cf in enumerate(self._connected_cfs):
                param = cf.param()
                param.set("colorLedBot.wrgb8888", LED_COLORS[i % len(LED_COLORS)])
                param.set("stabilizer.controller", 1)

            print("Reading pad positions...")
            temp_logger = LoggingTask(
                self._connected_cfs, ["stateEstimate.x", "stateEstimate.y", "stateEstimate.z"], LOG_INTERVAL
            )
            pos_data = await temp_logger.read_once()
            self._pad_positions = [
                (
                    float(d["stateEstimate.x"]),
                    float(d["stateEstimate.y"]),
                    float(d["stateEstimate.z"]),
                ) if d else (0.0, 0.0, 0.0)
                for d in pos_data
            ]

            print("Starting live position logger...")
            self._position_logger = LoggingTask(
                self._connected_cfs, ["stateEstimate.x", "stateEstimate.y", "stateEstimate.z"], LOG_INTERVAL
            )
            await self._position_logger.start()

            print("Arming drones...")
            await asyncio.gather(
                *[cf.platform().send_arming_request(True) for cf in self._connected_cfs]
            )
            await asyncio.sleep(1.0)

            print("Taking off...")
            await asyncio.gather(
                *[
                    cf.high_level_commander().take_off(
                        TAKEOFF_HEIGHT, None, TAKEOFF_DURATION, None
                    )
                    for cf in self._connected_cfs
                ]
            )
            await asyncio.sleep(TAKEOFF_DURATION + 0.5)

            # Initialise virtual setpoints from measured positions after takeoff.
            self._virtual_positions = []
            for i in range(len(self._connected_cfs)):
                data = self._position_logger.get_log(i)
                if data:
                    self._virtual_positions.append(np.array([
                        float(data["stateEstimate.x"]),
                        float(data["stateEstimate.y"]),
                        float(data["stateEstimate.z"]),
                    ]))
                else:
                    self._virtual_positions.append(np.array([0.0, 0.0, TAKEOFF_HEIGHT]))

            # Initialise targets to current hover positions so drones hold still.
            self._target_positions = [np.array(p) for p in self._virtual_positions]

            print("Starting force-field background loop...")
            self._ff_task = asyncio.create_task(self._ff_loop_impl())

            print("Hovering...")
            self._set_state(SwarmState.FLYING)
        except Exception as exc:
            self._set_state(SwarmState.ERROR)
            if self._position_logger:
                await self._position_logger.stop()

    def safegoto(self, positions: list) -> None:
        """Update target positions consumed by the force-field loop.

        *positions* is a list of ``(x, y, z)`` tuples (or ``None`` to keep a
        drone at its current virtual position), one entry per connected drone.
        Returns immediately; the background loop will navigate toward the new
        targets continuously.  Ignored if not currently flying.
        
        LLM setpoints in [-1,1]^3 are automatically scaled to real-world coordinates.
        """
        if self._state != SwarmState.FLYING:
            return
        # Scale LLM normalized coordinates to real-world coordinates
        scaled_positions = [scale_setpoint(*p) if p is not None else None for p in positions]
        n = len(self._connected_cfs)
        self._target_positions = [
            np.array(scaled_positions[i], dtype=float) if i < len(scaled_positions) and scaled_positions[i] is not None
            else (self._virtual_positions[i].copy() if i < len(self._virtual_positions) else None)
            for i in range(n)
        ]

    def goto(self, positions: list) -> None:
        """Alias for safegoto - update target positions using simpler name."""
        return self.safegoto(positions)

    # -- Force-field background loop -----------------------------------------

    async def _ff_loop_impl(self) -> None:
        """Continuously navigate toward *_target_positions* using the force field.

        Runs indefinitely until cancelled.  Every *FF_VIRTUAL_UPDATES_PER_GOTO*
        steps the virtual setpoints are sent to the firmware via go_to and the
        latest live positions are polled for the GUI.
        """
        # Initialise controller with current virtual and target positions.
        controller = ForceFieldController(self._virtual_positions)
        steps = 0
        try:
            while True:
                print(f"FF loop: step {steps}, virtual positions: {self._virtual_positions}, targets: {self._target_positions}")
                n = len(self._connected_cfs)
                if not self._virtual_positions or len(self._virtual_positions) != n:
                    await asyncio.sleep(FF_VIRTUAL_UPDATE_INTERVAL)
                    continue

                # Advance virtual positions via the controller.
                next_positions = controller.step(self._target_positions)
                # Keep Swarm's attribute in sync for external access.
                self._virtual_positions = next_positions

                steps += 1
                if steps >= FF_VIRTUAL_UPDATES_PER_GOTO:
                    steps = 0
                    active = [
                        i for i in range(n)
                        if i < len(self._target_positions) and self._target_positions[i] is not None
                    ]
                    if active:
                        await asyncio.gather(
                            *[
                                self._connected_cfs[i].high_level_commander().go_to(
                                    float(next_positions[i][0]),
                                    float(next_positions[i][1]),
                                    float(next_positions[i][2]),
                                    0.0,
                                    FF_WAYPOINT_INTERVAL,
                                    relative=False,
                                    linear=True,
                                    group_mask=None,
                                )
                                for i in active
                            ],
                            return_exceptions=True,
                        )

                    await asyncio.sleep(FF_WAYPOINT_INTERVAL)
        except asyncio.CancelledError:
            print("Force-field loop cancelled.")
            pass

    async def _cancel_ff_loop(self) -> None:
        """Cancel and await the force-field background task if running."""
        if self._ff_task is not None and not self._ff_task.done():
            self._ff_task.cancel()
            await asyncio.gather(self._ff_task, return_exceptions=True)
        self._ff_task = None

    async def _wait_for_targets(self, timeout: float = 30.0) -> None:
        """Return once all virtual positions are within *FF_POSITION_TOLERANCE* of their targets."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while loop.time() < deadline:
            all_reached = True
            for i, target in enumerate(self._target_positions):
                if target is None:
                    continue
                if i >= len(self._virtual_positions):
                    all_reached = False
                    break
                if np.linalg.norm(target - self._virtual_positions[i]) > FF_POSITION_TOLERANCE:
                    all_reached = False
                    break
            if all_reached:
                return
            await asyncio.sleep(0.1)

    # -- Private helpers -----------------------------------------------------

    async def _disconnect_all(self) -> None:
        if not self._connected_cfs:
            return
        for cf in self._connected_cfs:
            param = cf.param()
            param.set("colorLedBot.wrgb8888", 0x00000000)
        await asyncio.gather(
            *[cf.disconnect() for cf in self._connected_cfs],
            return_exceptions=True,
        )
        self._connected_cfs = []
        self._link_context = None
#!/usr/bin/env python3
"""Debug script for real drone swarm - fly circle for 5s then land."""
import asyncio
import sys
import numpy as np

sys.path.insert(0, "/home/alex/Documents/CrazyMCP")

from hardware import Swarm


def swarm_show(elapsed: float, num_drones: int = 3) -> tuple[list[tuple[float, float, float]], bool]:
    """Generate circle setpoints for multiple drones. Returns (setpoints, finished).
    
    Each drone flies on a circle with a different phase offset, all at height 1.0m.
    Finishes after 5 seconds.
    """
    radius = 0.5
    height = 1.0
    duration = 5.0
    
    angle = (elapsed / duration) * 2 * np.pi
    
    setpoints = []
    for i in range(num_drones):
        phase_offset = (2 * np.pi * i) / num_drones
        x = radius * np.cos(angle + phase_offset)
        y = radius * np.sin(angle + phase_offset)
        z = height
        setpoints.append((x, y, z))
    
    finished = elapsed >= duration
    
    return setpoints, finished


async def main():
    swarm = Swarm()
    
    try:
        await swarm.connect("radio://0/84/2M/D91F7001", 3)
        await swarm.takeoff()
        
        start_time = asyncio.get_running_loop().time()
        while True:
            elapsed = asyncio.get_running_loop().time() - start_time
            setpoints, finished = swarm_show(elapsed, num_drones=3)
            swarm.goto(setpoints)
            if finished:
                break
            await asyncio.sleep(0.1)
                    
        await swarm.land()
    except Exception as e:
        print(f"Error during swarm show: {e}")
        try:
            await swarm.land()
        except Exception:
            pass
    finally:
        await swarm.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
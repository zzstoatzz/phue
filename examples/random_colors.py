"""
This script will have all lights change to a random color.

WARNING: If you have not previously connected to the bridge, run connect_bridge.py first.
"""

import random

from phue import Bridge

b = Bridge()

if __name__ == "__main__":
    lights = b.get_light_objects()

    for light in lights:
        light.brightness = 254
        light.xy = (random.random(), random.random())

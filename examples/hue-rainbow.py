#!/usr/bin/env python3
"""
This script creates a rainbow effect by cycling through hue values for all active lights.

WARNING: If you have not previously connected to the bridge, run connect_bridge.py first.
"""

from time import sleep

from phue import Bridge, Light

b = Bridge()  # Enter bridge IP here.

# Get all the lights as a dictionary by ID
lights: dict[int, Light] = b.get_light_objects("id")

totalTime = 30  # in seconds
transitionTime = 1  # in seconds

maxHue = 65535  # Maximum value for hue
hueIncrement = int(maxHue / totalTime)

# Configure initial light settings
for light_id, light in lights.items():
    light.transitiontime = int(
        transitionTime * 10
    )  # Convert to deciseconds and ensure int
    light.brightness = 254
    light.saturation = 254
    # light.on = True  # Uncomment to turn all lights on

# Main loop to cycle through colors
hue = 0
while True:
    for light_id, light in lights.items():
        light.hue = int(hue)  # Ensure hue is always an integer

    hue = (hue + hueIncrement) % maxHue

    sleep(transitionTime)

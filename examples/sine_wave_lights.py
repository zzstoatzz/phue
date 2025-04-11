"""
This script will have a selected light cycle through a sine wave of hue and brightness.

WARNING: If you have not previously connected to the bridge, run connect_bridge.py first.
"""

import math
import time

from phue import Bridge

# --- Configuration ---
BRIDGE_IP = None  # Replace with your bridge's IP address
UPDATE_INTERVAL = 0.5  # Seconds between updates
HUE_FREQUENCY = 0.1  # Controls how fast the hue cycles (lower is slower)
BRIGHTNESS_FREQUENCY = 0.2  # Controls how fast the brightness pulses (lower is slower)
SATURATION = 254  # Max saturation (0-254)
TRANSITION_TIME = int(UPDATE_INTERVAL * 10)  # Transition time in deciseconds


# --- Helper Function ---
def select_light(bridge: Bridge) -> tuple[int, str]:
    """Gets available lights and prompts user to select one"""
    try:
        available_lights = bridge.get_light_objects("list")
    except Exception as e:
        print(f"Error retrieving lights from bridge: {e}")
        exit(1)

    if not available_lights:
        print("No lights found on the bridge.")
        exit(1)

    print("Available lights:")
    for i, light in enumerate(available_lights):
        print(f"  {i}: {light.name}")

    while True:
        try:
            selection = input("Enter the number of the light to control: ")
            light_index = int(selection)
            if 0 <= light_index < len(available_lights):
                selected_light_name = available_lights[light_index].name
                light_id = bridge.get_light_id_by_name(selected_light_name)
                if light_id is None:
                    # This shouldn't happen if we just got the list, but check anyway
                    print(
                        f"Error: Could not get ID for selected light '{selected_light_name}'."
                    )
                    exit(1)
                print(f"Selected light: {selected_light_name} (ID: {light_id})")
                return light_id, selected_light_name
            else:
                print("Invalid selection. Please enter a number from the list.")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except (EOFError, KeyboardInterrupt):
            print("\nSelection cancelled.")
            exit(0)


# --- Main Script ---
try:
    b = Bridge(BRIDGE_IP)
except Exception as e:
    print(f"Error connecting to bridge at {BRIDGE_IP}: {e}")
    print(
        "Please check the IP address and ensure the bridge button wasn't pressed recently."
    )
    exit(1)

# Select the light to control
light_id, light_name = select_light(b)

# Get the light name for display purposes (optional, id is sufficient)
# light_name = b.get_light_name(light_id) # Or retrieve from the select_light selection

print(f"Connected to bridge. Controlling light: {light_name} (ID: {light_id})")
print("Press Ctrl+C to exit.")

# Ensure the light is on initially
b.set_light(light_id, "on", True)
# Set constant saturation
b.set_light(light_id, {"sat": SATURATION})


start_time = time.time()

while True:
    try:
        current_time = time.time()
        elapsed_time = current_time - start_time

        # Calculate hue (0-65535) using a sine wave
        # math.sin ranges from -1 to 1. We shift and scale it.
        hue_raw = math.sin(elapsed_time * 2 * math.pi * HUE_FREQUENCY)  # -1 to 1
        hue = int(((hue_raw + 1) / 2) * 65535)  # Scale to 0-65535

        # Calculate brightness (1-254) using a sine wave
        # We add a small offset phase to brightness relative to hue
        brightness_raw = math.sin(
            elapsed_time * 2 * math.pi * BRIGHTNESS_FREQUENCY + math.pi / 4
        )  # -1 to 1
        brightness = 1 + int(((brightness_raw + 1) / 2) * 253)  # Scale to 1-254

        # Create command dictionary
        command = {
            "hue": hue,
            "bri": brightness,
            "transitiontime": TRANSITION_TIME,
        }

        b.set_light(light_id, command)

        print(f"Time: {elapsed_time:.1f}s, Hue: {hue}, Brightness: {brightness}")

        time.sleep(UPDATE_INTERVAL)

    except KeyboardInterrupt:
        print("\nExiting...")
        # Optional: Turn the light off or reset it when exiting
        # b.set_light(light_id, 'on', False)
        break
    except Exception as e:
        print(f"An error occurred: {e}")
        # Add more specific error handling if needed (e.g., connection errors)
        time.sleep(5)  # Wait before retrying after an error

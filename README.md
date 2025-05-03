# phue

modern Python library to control the Philips Hue lighting system

This is a fork of the original [phue library](https://github.com/studioimaginaire/phue) by Nathanaël Lécaudé, modernized with type annotations, improved error handling, and a fully-featured CLI. The library remains MIT licensed.

> [!IMPORTANT]

> I appreciate the original authors work and if there's any interest in merging these (substantial) changes back into the original library, I'm happy to do so.

## Installation

### Using uv

```bash
uv add phue

uv pip install phue
```

### Using pip

```bash
pip install phue
```

## Repository Structure

```
.
├── LICENSE
├── README.md
├── examples/
├── src/
│   └── phue/
│       ├── __init__.py
│       ├── __main__.py      # CLI interface
│       ├── bridge.py        # Bridge connection handling
│       ├── exceptions.py    # Custom exceptions
│       ├── group.py         # Group controls
│       ├── light.py         # Light controls
│       ├── scene.py         # Scene handling
│       └── sensor.py        # Sensor controls
└── tests/              # Tests
```

## Requirements

- Python 3.10 or higher (not compatible with Python 2.x)
- httpx (for network requests)

## Features

- Fully typed with Python type annotations
- Robust error handling with custom exceptions
- Comprehensive test suite
- Colorful, user-friendly command-line interface
- Support for Lights, Groups, Scenes, and Sensors
- Auto-discovery of Hue bridges on the network
- Simple and intuitive API for controlling Hue devices



## Command Line Usage

The library includes a command-line interface for controlling your Hue lights:

```bash
# List all lights
phue ls

# Get details about a specific light
phue get light "Living Room"

# Turn on a light and set brightness
phue set light "Kitchen" --on --bri 200

# List all groups
phue ls groups

# Turn off lights in a group
phue set group "Downstairs" --off
```

## Basic Usage

Using the set_light and get_light methods you can control pretty much all the parameters:

```python
from phue import Bridge

# Connect to the bridge
b = Bridge('192.168.1.100')

# If the app is not registered and the button is not pressed, press the button and call connect()
# This only needs to be run a single time
b.connect()

# Get the bridge state (This returns the full dictionary that you can explore)
b.get_api()

# Prints if light 1 is on or not
b.get_light(1, 'on')

# Set brightness of lamp 1 to max
b.set_light(1, 'bri', 254)

# Turn lamp 2 on
b.set_light(2, 'on', True)

# You can also control multiple lamps by sending a list as lamp_id
b.set_light([1, 2], 'on', True)

# You can also use light names instead of the id
b.get_light('Kitchen')
b.set_light('Kitchen', 'bri', 254)

# Also works with lists
b.set_light(['Bathroom', 'Garage'], 'on', False)
```

### Light Objects

If you want to work in a more object-oriented way, you can get Light objects:

```python
# Get a flat list of light objects
lights = b.lights

# Print light names
for light in lights:
    print(light.name)

# Set brightness of each light to 127
for light in lights:
    light.brightness = 127

# Get a dictionary with the light name as the key
light_names = b.get_light_objects('name')

# Set lights using name as key
for light_name in ['Kitchen', 'Bedroom', 'Garage']:
    light = light_names.get(light_name)
    if light:
        light.on = True
        light.hue = 15000
        light.saturation = 120
```

## Error Handling

The library provides custom exceptions for better error handling:

```python
from phue import Bridge, PhueRegistrationException, PhueRequestTimeout

try:
    b = Bridge('192.168.1.100')
    b.connect()
except PhueRegistrationException:
    print("Press the button on the bridge and try again")
except PhueRequestTimeout:
    print("Could not connect to the bridge - check your network")
```

## Acknowledgments

This project is a fork of the original [phue](https://github.com/studioimaginaire/phue) library created by Nathanaël Lécaudé.

The modernized version was created by [zzstoatzz](https://github.com/zzstoatzz) to add type annotations and a more opinionated CLI.

## License

MIT - http://opensource.org/licenses/MIT

"Hue Personal Wireless Lighting" is a trademark owned by Koninklijke Philips Electronics N.V., see www.meethue.com for more information.
I am in no way affiliated with the Philips organization.

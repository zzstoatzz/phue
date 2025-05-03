#!/usr/bin/env python3
"""
Example showing how to connect to a Philips Hue bridge.
This is a good first script to run when setting up phue.
"""

import json
import logging
import os
import sys

from phue import Bridge, Light, PhueRegistrationException, console

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")


def light_formatter(light: Light) -> str:
    """Format a light for display in a table."""
    status = "ON" if light.on else "OFF"
    return f"{light.name:<25} - Status: {status}"


def main():
    """Connect to the Hue bridge and save credentials."""
    console.header("Philips Hue Bridge Setup")

    config_path = os.path.expanduser("~/.python_hue")

    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                config = json.loads(f.read())
                if config:
                    console.info("Found existing Hue bridge configuration.")

                    for ip_address in config:
                        if "username" in config[ip_address]:
                            console.info(f"Trying saved bridge at {ip_address}...")
                            try:
                                bridge = Bridge(ip=ip_address)
                                lights = bridge.lights
                                console.success(f"Connected to bridge at {ip_address}")
                                console.table(lights, light_formatter)
                                return
                            except Exception as e:
                                console.error(f"Couldn't connect to {ip_address}")
                                console.info(f"Error details: {e}")

                    console.warning("Couldn't connect with any saved bridges.")
        except (json.JSONDecodeError, FileNotFoundError):
            console.error("Config file exists but is invalid.")

    console.section("Bridge Connection Setup")
    console.info("You'll need to provide your bridge IP address.")
    console.info(
        "You can find it in the Hue app (Settings > My Bridge) or your router."
    )

    ip_address = input("\nEnter your bridge IP address: ")
    if not ip_address:
        console.error("No IP address provided. Exiting.")
        sys.exit(1)

    while True:
        console.section("Link Button Authentication")
        console.warning("You need to press the link button on your Hue bridge.")
        console.box(
            "IMPORTANT",
            [
                "You only have 30 seconds to press the button!",
                "Get ready to walk over to your bridge...",
            ],
        )

        input("\nPress Enter when you're ready to go press the button...")

        try:
            console.info("Attempting to register with the bridge...")
            bridge = Bridge(ip=ip_address)
            console.success("Connected and saved credentials!")

            console.section("Your Hue Lights")
            console.table(bridge.lights, light_formatter)

            console.success("Setup complete! You can now control your Hue lights.")
            break

        except PhueRegistrationException:
            console.error("Link button was not pressed in time.")
            console.warning("Let's try again. Remember, you only have 30 seconds!")

        except Exception as e:
            console.error(f"Connection failed: {e}")
            retry = input("\nTry again? (y/n): ")
            if retry.lower() != "y":
                console.error("Exiting. Please try again later.")
                sys.exit(1)


if __name__ == "__main__":
    main()

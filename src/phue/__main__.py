"""Command-line interface for the phue library."""

import argparse
import json
import logging
import os
import sys

from phue import Bridge, PhueRegistrationException
from phue._internal.console import (
    BLUE,
    BOLD,
    CYAN,
    GREEN,
    MAGENTA,
    RED,
    YELLOW,
    console,
    styled_text,
)

DISABLE_STYLING = False


def styled_for_cli(text: str, style: str) -> str:
    """Apply styling if enabled, otherwise return plain text.

    This helper makes tests less brittle by allowing them to match
    on the plain text content.

    Args:
        text: Text to style
        style: Style to apply

    Returns:
        Styled text if styling is enabled, otherwise plain text
    """
    if DISABLE_STYLING:
        return text
    return styled_text(text, style)


def parse_args(
    argv: list[str] | None = None,
) -> tuple[argparse.ArgumentParser, argparse.Namespace]:
    """Parse command line arguments.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:])

    Returns:
        Tuple of (parser, parsed_args)
    """
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Control Philips Hue lights from the command line"
    )
    parser.add_argument(
        "--host", help="IP address of the Hue bridge (auto-detected if not provided)"
    )
    parser.add_argument("--config-file-path", help="Path to the config file")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--no-save-config",
        action="store_false",
        dest="save_config",
        help="Do not save connection details to the config file",
    )

    # Command subparsers
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # List command (with ls alias)
    list_parser = subparsers.add_parser(
        "list", aliases=["ls"], help="List available resources"
    )
    list_parser.add_argument(
        "resource",
        nargs="?",
        choices=["lights", "groups", "scenes"],
        default="lights",
        help="Resource type to list",
    )

    # Get command
    get_parser = subparsers.add_parser("get", help="Get resource details")
    get_parser.add_argument(
        "resource", choices=["light", "group", "scene"], help="Resource type"
    )
    get_parser.add_argument("name", help="Resource name or ID")

    # Set command
    set_parser = subparsers.add_parser("set", help="Set resource state")
    set_parser.add_argument(
        "resource", choices=["light", "group"], help="Resource type"
    )
    set_parser.add_argument("name", help="Resource name or ID")
    set_parser.add_argument("--on", action="store_true", help="Turn on")
    set_parser.add_argument("--off", action="store_true", help="Turn off")
    set_parser.add_argument("--bri", type=int, help="Set brightness (0-254)")
    set_parser.add_argument("--hue", type=int, help="Set hue (0-65535)")
    set_parser.add_argument("--sat", type=int, help="Set saturation (0-254)")

    # Parse arguments
    return parser, parser.parse_args(argv)


def get_bridge_from_config(config_path: str | None = None) -> Bridge | None:
    """Attempt to create a Bridge using existing config.

    Args:
        config_path: Path to config file (uses default if None)

    Returns:
        Bridge instance if successful, None otherwise
    """
    if not config_path:
        config_path = os.path.expanduser("~/.python_hue")

    if not os.path.exists(config_path):
        return None

    try:
        with open(config_path) as f:
            config = json.loads(f.read())

        # Try each bridge in the config
        for ip in config:
            if "username" in config[ip]:
                try:
                    bridge = Bridge(ip=ip, config_file_path=config_path)
                    console.info(
                        f"{styled_for_cli('Using saved connection to bridge at', MAGENTA)} {styled_for_cli(ip, YELLOW)}"
                    )
                    return bridge
                except Exception:
                    continue
    except Exception:
        pass

    return None


def main(argv: list[str] | None = None) -> int:
    """Run the phue command-line interface.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code
    """
    # Parse arguments
    parser, args = parse_args(argv)

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.WARNING
    logging.basicConfig(level=log_level)

    # Get bridge - first try config if no host specified
    bridge = None
    if not args.host:
        bridge = get_bridge_from_config(args.config_file_path)

    # If not connected and host provided, connect to specified host
    if not bridge and args.host:
        console.info(f"Connecting to bridge at {args.host}...")
        while True:
            try:
                bridge = Bridge(
                    args.host,
                    config_file_path=args.config_file_path,
                    save_config=args.save_config,
                )
                console.success("Successfully connected to the bridge!")
                break
            except PhueRegistrationException:
                console.warning(
                    "Link button not pressed. Press the link button on your bridge."
                )
                input("Press Enter to try again...")
            except Exception as e:
                console.error(f"Failed to connect to the bridge: {e}")
                return 1

    # If we still don't have a bridge but command specified, error out
    if not bridge and args.command:
        console.error(
            "No bridge connection available. Please specify --host or ensure config file exists."
        )
        return 1

    # If we still don't have a bridge and no command specified, show general help
    if not bridge and not args.command:
        console.error(
            "No bridge connection available. Please specify --host or ensure config file exists."
        )
        args_parser = argparse.ArgumentParser(
            description="Control Philips Hue lights from the command line"
        )
        args_parser.print_help()
        return 1

    # If no command specified but we have a bridge, show command help
    if bridge and not args.command:
        console.info(
            f"{styled_for_cli('Connected to bridge.', GREEN)} {styled_for_cli('Use a command to continue.', CYAN)}"
        )
        parser.print_help()
        return 0

    # Process commands

    # Handle list/ls command
    if args.command in ["list", "ls"]:
        if not bridge:
            console.error("No bridge connection available")
            return 1

        if args.resource == "lights":
            lights = bridge.lights
            console.info(styled_for_cli(f"LIGHTS ({len(lights)}):", YELLOW + BOLD))
            for light in lights:
                status = "ON" if light.on else "OFF"
                status_styled = styled_for_cli(status, GREEN if light.on else RED)
                name = str(light.name)
                name_styled = styled_for_cli(name, CYAN)
                console.info(f"  {name_styled:<25} {status_styled}")

        elif args.resource == "groups":
            groups = bridge.groups
            console.info(styled_for_cli(f"GROUPS ({len(groups)}):", YELLOW + BOLD))
            for group in groups:
                name = str(group.name)
                name_styled = styled_for_cli(name, CYAN)
                console.info(f"  {name_styled}")

        elif args.resource == "scenes":
            scenes = bridge.scenes
            console.info(styled_for_cli(f"SCENES ({len(scenes)}):", YELLOW + BOLD))
            for scene in scenes:
                name = str(scene.name)
                name_styled = styled_for_cli(name, CYAN)
                console.info(f"  {name_styled}")

    # Handle get command
    elif args.command == "get":
        if not bridge:
            console.error("No bridge connection available")
            return 1

        resource = args.resource
        name = args.name

        if resource == "light":
            try:
                light = bridge.get_light(name)
                assert light["name"]
            except KeyError:
                console.error(f"Light '{name}' not found")
                return 1

            console.info(styled_for_cli(f"LIGHT: {light['name']}", YELLOW + BOLD))
            console.info(
                f"  {styled_for_cli('Status:', BLUE)}      {styled_for_cli('ON' if light['state']['on'] else 'OFF', GREEN if light['state']['on'] else RED)}"
            )
            console.info(f"  {styled_for_cli('Type:', BLUE)}        {light['type']}")
            console.info(
                f"  {styled_for_cli('Brightness:', BLUE)}  {light['state']['bri']}/254"
            )
            console.info(
                f"  {styled_for_cli('Hue:', BLUE)}         {light['state']['hue']}/65535"
            )
            console.info(
                f"  {styled_for_cli('Saturation:', BLUE)}  {light['state']['sat']}/254"
            )
            console.info(
                f"  {styled_for_cli('Reachable:', BLUE)}   {light['state']['reachable']}"
            )

        elif resource == "group":
            # Try to find group by name
            group_id = None
            try:
                group_id = bridge.get_group_id_by_name(name)
            except Exception:
                pass

            if group_id is None:
                try:
                    group_id = int(name)
                except ValueError:
                    group_id = None

            if group_id is None:
                console.error(f"Group '{name}' not found")
                return 1

            group = bridge.get_group(group_id)

            console.info(styled_for_cli(f"GROUP: {group['name']}", YELLOW + BOLD))
            console.info(f"  {styled_for_cli('Type:', BLUE)}    {group['type']}")
            console.info(
                f"  {styled_for_cli('Lights:', BLUE)}  {', '.join(group['lights'])}"
            )

        elif resource == "scene":
            # This needs bridge.get_scene() implementation which isn't shown
            console.error("Scene details not yet implemented")
            return 1

    # Handle set command
    elif args.command == "set":
        if not bridge:
            console.error("No bridge connection available")
            return 1

        resource = args.resource
        name = args.name
        changed = False
        state_changes: dict[str, object] = {}

        if args.on:
            state_changes["on"] = True
            changed = True
        elif args.off:
            state_changes["on"] = False
            changed = True

        if args.bri is not None:
            state_changes["bri"] = args.bri
            changed = True

        if args.hue is not None:
            state_changes["hue"] = args.hue
            changed = True

        if args.sat is not None:
            state_changes["sat"] = args.sat
            changed = True

        if resource == "light":
            light = None
            if not light:
                light = bridge.get_light(name)

            if not light:
                console.error(f"Light '{name}' not found")
                return 1

            if changed:
                bridge.set_light(name, state_changes)
                console.success(f"Updated light '{light['name']}'")
            else:
                console.warning("No changes specified")

        elif resource == "group":
            # Try to find group by name
            group_id = None
            try:
                group_id = bridge.get_group_id_by_name(name)
            except Exception:
                pass

            if group_id is None:
                try:
                    group_id = int(name)
                except ValueError:
                    group_id = None

            if group_id is None:
                console.error(f"Group '{name}' not found")
                return 1

            if changed:
                bridge.set_group(group_id, state_changes)
                console.success(f"Updated group {name}")
            else:
                console.warning("No changes specified")

    return 0


if __name__ == "__main__":
    sys.exit(main())

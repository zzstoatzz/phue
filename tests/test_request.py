# Published under the MIT license - See LICENSE file for more detail
#
# This is a basic test file which just tests that things import, which
# means that this is even vaguely python code.

import os
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

import phue


@pytest.fixture
def temp_home(tmp_path: Path) -> Generator[Path, None, None]:
    """Fixture that provides a temporary home directory."""
    old_home = os.environ.get("HOME")
    os.environ["HOME"] = str(tmp_path)
    yield tmp_path
    if old_home is not None:
        os.environ["HOME"] = old_home


def test_register(temp_home: Path):
    """test that registration happens automatically during setup."""
    confname = os.path.join(temp_home, ".python_hue")
    with mock.patch("phue.Bridge.request") as req:
        req.return_value = [{"success": {"username": "fooo"}}]
        bridge = phue.Bridge(ip="10.0.0.0")
        assert bridge.config_file_path == confname

    # check contents of file
    with open(confname) as f:
        contents = f.read()
        assert contents == '{"10.0.0.0": {"username": "fooo"}}'

    # make sure we can open under a different file
    bridge2 = phue.Bridge(ip="10.0.0.0")
    assert bridge2.username == "fooo"

    # and that we can even open without an ip address
    bridge3 = phue.Bridge()
    assert bridge3.username == "fooo"
    assert bridge3.ip == "10.0.0.0"


def test_register_fail():
    """Test that registration fails in the expected way for timeout"""
    with mock.patch("phue.Bridge.request") as req:
        req.return_value = [{"error": {"type": 101}}]
        with pytest.raises(phue.PhueRegistrationException):
            phue.Bridge(ip="10.0.0.0")


def test_register_unknown_user():
    """Test that registration for unknown user works."""
    with mock.patch("phue.Bridge.request") as req:
        req.return_value = [{"error": {"type": 7}}]
        with pytest.raises(phue.PhueException):
            phue.Bridge(ip="10.0.0.0")


@pytest.fixture
def mock_bridge():
    """Fixture that provides a bridge with mocked request method."""
    with mock.patch("phue.Bridge.request") as mock_request:
        # Mock the lights collection endpoint

        def mock_request_side_effect(
            method: str, address: str, data: dict[str, Any] | None = None
        ) -> dict[str, Any]:
            if address == "/api/username/lights/":
                return {
                    "1": {
                        "name": "Living Room Bulb",
                        "state": {"on": True, "bri": 254, "hue": 10000, "sat": 254},
                        "type": "Extended color light",
                        "modelid": "LCT001",
                    }
                }
            elif address == "/api/username/lights/1":
                return {
                    "name": "Living Room Bulb",
                    "state": {"on": True, "bri": 254, "hue": 10000, "sat": 254},
                    "type": "Extended color light",
                    "modelid": "LCT001",
                }
            else:
                raise ValueError(f"Unexpected API call: {method} {address} {data}")

        mock_request.side_effect = mock_request_side_effect

        bridge = phue.Bridge(ip="10.0.0.0", username="username")
        yield bridge


def test_get_lights(mock_bridge: phue.Bridge):
    """Test getting light objects by ID."""
    lights = mock_bridge.get_light_objects("id")
    assert lights[1].name == "Living Room Bulb"

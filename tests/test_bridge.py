from pathlib import Path

import httpx
import pytest
import respx

import phue


@pytest.fixture
def tmp_config_path(tmp_path: Path) -> str:
    """Provide a temporary config file path for tests."""
    return str(tmp_path / ".python_hue")


def test_bridge_discovery_and_registration(tmp_config_path: str) -> None:
    with respx.mock(assert_all_called=True) as mock:
        # Add route to test IP discovery
        mock.get("https://www.meethue.com/api/nupnp", name="discover").mock(
            return_value=httpx.Response(
                200, json=[{"internalipaddress": "192.168.1.100"}]
            )
        )

        # Create a bridge directly with IP and username, but use temp config
        bridge = phue.Bridge(
            ip="192.168.1.100", username="testuser", config_file_path=tmp_config_path
        )

        # Test that get_ip_address works independently
        discovered_ip = bridge.get_ip_address()
        assert discovered_ip == "192.168.1.100"

        # Verify bridge properties
        assert bridge.ip == "192.168.1.100"
        assert bridge.username == "testuser"


def test_light_control(tmp_config_path: str) -> None:
    with respx.mock(assert_all_called=True) as mock:
        mock.get("http://192.168.1.100/api/testuser/lights/", name="get_lights").mock(
            return_value=httpx.Response(
                200, json={"1": {"name": "Test Light", "state": {"on": False}}}
            )
        )
        mock.put(
            "http://192.168.1.100/api/testuser/lights/1/state", name="set_state"
        ).mock(
            return_value=httpx.Response(
                200, json=[{"success": {"/lights/1/state/on": True}}]
            )
        )

        bridge = phue.Bridge(
            ip="192.168.1.100", username="testuser", config_file_path=tmp_config_path
        )
        light = bridge.lights[0]
        light.on = True


def test_error_handling(tmp_config_path: str) -> None:
    with respx.mock(assert_all_called=True) as mock:
        mock.get("http://192.168.1.100/api/testuser/lights/", name="timeout").mock(
            side_effect=httpx.TimeoutException("Connection timed out")
        )

        bridge = phue.Bridge(
            ip="192.168.1.100", username="testuser", config_file_path=tmp_config_path
        )

        with pytest.raises(phue.PhueRequestTimeout):
            bridge.get_light()


def test_config_file(tmp_path: Path) -> None:
    config_file = tmp_path / ".python_hue"

    with respx.mock(assert_all_called=True) as mock:
        mock.post("http://192.168.1.100/api", name="create_user").mock(
            return_value=httpx.Response(
                200, json=[{"success": {"username": "testuser"}}]
            )
        )

        # Create a bridge and verify config file is created
        bridge1 = phue.Bridge(ip="192.168.1.100", config_file_path=str(config_file))
        assert config_file.exists()
        assert bridge1.username == "testuser"

        # Test loading from config
        bridge2 = phue.Bridge(config_file_path=str(config_file))
        assert bridge2.username == "testuser"


def test_no_save_config(tmp_path: Path) -> None:
    """Test that the config file is not saved when save_config is False."""
    config_file = tmp_path / ".python_hue"

    with respx.mock(assert_all_called=True) as mock:
        mock.post("http://192.168.1.100/api", name="create_user").mock(
            return_value=httpx.Response(
                200, json=[{"success": {"username": "nosavetest"}}]
            )
        )

        # Create a bridge with save_config=False
        bridge = phue.Bridge(
            ip="192.168.1.100",
            config_file_path=str(config_file),
            save_config=False,
        )

        # Verify config file was NOT created and username is set
        assert not config_file.exists()
        assert bridge.username == "nosavetest"

        # Verify that trying to connect again without IP fails (as config wasn't saved)
        with pytest.raises(phue.PhueException):
            phue.Bridge(config_file_path=str(config_file))

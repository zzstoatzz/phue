"""Test the CLI functionality in the __main__ module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
import respx

from phue import Bridge
from phue.__main__ import main


@pytest.fixture(autouse=True)
def disable_styling(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("phue.__main__.DISABLE_STYLING", True)


def test_cli_help() -> None:
    """Test that the CLI can display help."""
    # --help will cause the parser to print help and exit
    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])
    # It should exit with a success code
    assert excinfo.value.code == 0


def test_cli_missing_args() -> None:
    """Test that the CLI errors when no host or command is provided but no config exists."""
    with patch("phue.__main__.get_bridge_from_config", return_value=None):
        with patch("phue._internal.console.console.error") as mock_error:
            result = main([])
            assert result == 1
            mock_error.assert_called_once()


@respx.mock
def test_cli_successful_connection(tmp_path: Path) -> None:
    """Test that the CLI connects successfully when the bridge is available."""
    # Create a temporary config file path
    config_path = tmp_path / ".python_hue"

    # Mock the bridge API responses
    respx.post("http://192.168.1.100/api").mock(
        return_value=httpx.Response(200, json=[{"success": {"username": "testuser"}}])
    )

    # Run the CLI with mocked input for the link button prompt
    with patch("phue._internal.console.console.success") as mock_success:
        result = main(
            ["--host", "192.168.1.100", "--config-file-path", str(config_path)]
        )
        assert result == 0
        mock_success.assert_called_with("Successfully connected to the bridge!")


@respx.mock
def test_cli_retry_on_registration_exception(tmp_path: Path) -> None:
    """Test that the CLI retries when the link button is not pressed."""
    # Create a temporary config file path
    config_path = tmp_path / ".python_hue"

    # First request fails, second succeeds after button press
    route = respx.post("http://192.168.1.100/api")

    # Setup the route to return error first time (button not pressed)
    route.side_effect = [
        httpx.Response(
            200,
            json=[{"error": {"type": 101, "description": "link button not pressed"}}],
        ),
        httpx.Response(200, json=[{"success": {"username": "testuser"}}]),
    ]

    # Mock the input function to simulate pressing the button
    with (
        patch("builtins.input", return_value=""),
        patch("phue._internal.console.console.warning") as mock_warning,
        patch("phue._internal.console.console.success") as mock_success,
    ):
        result = main(
            ["--host", "192.168.1.100", "--config-file-path", str(config_path)]
        )

        assert result == 0
        mock_warning.assert_called_with(
            "Link button not pressed. Press the link button on your bridge."
        )
        mock_success.assert_called_with("Successfully connected to the bridge!")


@pytest.mark.parametrize(
    "resource,attribute",
    [
        ("lights", "lights"),
        ("groups", "groups"),
        ("scenes", "scenes"),
    ],
)
def test_cli_list_command(resource: str, attribute: str) -> None:
    """Test that the list command shows the correct items."""
    # Create mock Bridge and items
    mock_bridge = MagicMock(spec=Bridge)
    mock_items = [MagicMock(name=f"Item{i}") for i in range(3)]
    setattr(mock_bridge, attribute, mock_items)

    with (
        patch("phue.__main__.Bridge", return_value=mock_bridge),
        patch("phue.__main__.get_bridge_from_config", return_value=None),
        patch("phue._internal.console.console.info") as mock_info,
    ):
        result = main(["--host", "192.168.1.100", "list", resource])

        assert result == 0
        # Check that it reported the resource type
        mock_info.assert_any_call(f"{resource.upper()} ({len(mock_items)}):")


def test_cli_get_command() -> None:
    """Test retrieving the details of a light."""
    mock_bridge = MagicMock(spec=Bridge)

    with (
        patch("phue.__main__.Bridge", return_value=mock_bridge),
        patch("phue._internal.console.console.info") as mock_info,
    ):
        result = main(["--host", "192.168.1.100", "get", "light", "Test Light"])

        assert result == 0
        mock_info.assert_called()


def test_cli_set_command() -> None:
    """Test setting the state of a light."""
    mock_bridge = MagicMock(spec=Bridge)

    with (
        patch("phue.__main__.Bridge", return_value=mock_bridge),
        patch("phue._internal.console.console.success") as mock_success,
    ):
        result = main(
            ["--host", "192.168.1.100", "set", "light", "1", "--on", "--bri", "200"]
        )

        assert result == 0
        mock_success.assert_called()

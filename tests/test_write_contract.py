from typing import Any
from unittest.mock import patch

import httpx
import pytest
import respx

from phue import Bridge, PhueAPIError, PhueException


@pytest.fixture
def bridge() -> Bridge:
    return Bridge(ip="bridge", username="test-key", save_config=False)


def test_partial_response_is_preserved(bridge: Bridge) -> None:
    response = [
        {"success": {"/lights/1/state/on": True}},
        {
            "error": {
                "type": 201,
                "address": "/lights/1/state/ct",
                "description": "not modifiable",
            }
        },
        {
            "error": {
                "type": 7,
                "address": "/lights/1/state/bri",
                "description": "invalid value",
            }
        },
    ]
    with respx.mock as router:
        router.put("http://bridge/api/test-key/lights/1/state").mock(
            return_value=httpx.Response(200, json=response)
        )
        with pytest.raises(PhueAPIError) as caught:
            bridge.set_light(1, {"on": True, "ct": 300, "bri": 999})
    assert isinstance(caught.value, PhueException)
    assert caught.value.id == 201
    assert caught.value.response == response


@pytest.mark.parametrize("kind", ["light", "group"])
def test_batches_stop_after_failed_target(bridge: Bridge, kind: str) -> None:
    collection, endpoint = (
        ("lights", "state") if kind == "light" else ("groups", "action")
    )
    with respx.mock(assert_all_called=False) as router:
        first = router.put(
            f"http://bridge/api/test-key/{collection}/1/{endpoint}"
        ).mock(return_value=httpx.Response(200, json=[{"success": {"on": True}}]))
        failed = router.put(
            f"http://bridge/api/test-key/{collection}/2/{endpoint}"
        ).mock(
            return_value=httpx.Response(
                200, json=[{"error": {"type": 201, "description": "unavailable"}}]
            )
        )
        last = router.put(f"http://bridge/api/test-key/{collection}/3/{endpoint}").mock(
            return_value=httpx.Response(200, json=[])
        )
        with pytest.raises(PhueAPIError):
            if kind == "light":
                bridge.set_light([1, 2, 3], "on", True)
            else:
                bridge.set_group([1, 2, 3], "on", True)
        assert first.called and failed.called and not last.called


@pytest.mark.parametrize("kind", ["light", "group"])
def test_unknown_names_raise_without_writing(bridge: Bridge, kind: str) -> None:
    with patch.object(bridge, f"get_{kind}_id_by_name", return_value=None):
        with patch.object(bridge, "request") as request:
            with pytest.raises(KeyError, match="not found"):
                if kind == "light":
                    bridge.set_light("missing", "on", True)
                else:
                    bridge.set_group("missing", "on", True)
            request.assert_not_called()


@pytest.mark.parametrize("kind", ["light", "group"])
def test_transition_does_not_mutate_callers_state(bridge: Bridge, kind: str) -> None:
    state: dict[str, Any] = {"on": True}
    with patch.object(bridge, "request", return_value=[]) as request:
        if kind == "light":
            bridge.set_light(1, state, transitiontime=10)
        else:
            bridge.set_group(1, state, transitiontime=10)
        assert request.call_args.args[2] == {"on": True, "transitiontime": 10}
    assert state == {"on": True}


def test_borrowed_client_remains_open_and_is_used_for_requests() -> None:
    paths: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return httpx.Response(200, json={})

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        bridge = Bridge(
            ip="bridge", username="test-key", save_config=False, http_client=client
        )
        bridge.get_light()
        bridge.get_group()
        assert not client.is_closed
    assert client.is_closed
    assert paths == ["/api/test-key/lights/", "/api/test-key/groups/"]

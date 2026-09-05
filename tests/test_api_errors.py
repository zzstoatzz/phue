import httpx
import pytest
import respx

from phue import Bridge, PhueException, PhueRegistrationException


@pytest.mark.parametrize("method", ["GET", "PUT", "POST", "DELETE"])
@pytest.mark.parametrize("partial", [False, True])
def test_http_success_with_hue_error_raises(method: str, partial: bool) -> None:
    body = [{"error": {"type": 201, "description": "parameter not modifiable"}}]
    if partial:
        body.insert(0, {"success": {"/lights/1/state/on": True}})
    with respx.mock as router:
        router.route(
            method=method, url="http://bridge/api/private-key/lights/1/state"
        ).mock(return_value=httpx.Response(200, json=body))
        bridge = Bridge(ip="bridge", username="private-key", save_config=False)
        with pytest.raises(PhueException, match="parameter not modifiable") as caught:
            bridge.request(method, "/api/private-key/lights/1/state")
        assert caught.value.id == 201


def test_registration_button_error_retains_specific_exception() -> None:
    with respx.mock as router:
        router.post("http://bridge/api").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"error": {"type": 101, "description": "link button not pressed"}}
                ],
            )
        )
        with pytest.raises(PhueRegistrationException):
            Bridge(ip="bridge", save_config=False)


def test_request_failure_does_not_expose_username() -> None:
    with respx.mock as router:
        router.get("http://bridge/api/private-key/lights/").mock(
            return_value=httpx.Response(403)
        )
        bridge = Bridge(ip="bridge", username="private-key", save_config=False)
        with pytest.raises(PhueException) as caught:
            bridge.get_light()
        assert "private-key" not in str(caught.value)

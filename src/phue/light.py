"""Light class for controlling Philips Hue lights."""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from phue.bridge import Bridge

logger = logging.getLogger("phue_modern")


class Light:
    """Hue Light object

    Light settings can be accessed or set via the properties of this object.
    """

    def __init__(self, bridge: "Bridge", light_id: int):
        self.bridge = bridge
        self.light_id = light_id

        self._name: str | None = None
        self._on: bool | None = None
        self._brightness: int | None = None
        self._colormode: str | None = None
        self._hue: int | None = None
        self._saturation: int | None = None
        self._xy: tuple[float, float] | None = None
        self._colortemp: int | None = None
        self._effect: str | None = None
        self._alert: str | None = None
        self.transitiontime: int | None = None  # default
        self._reset_bri_after_on: bool | None = None
        self._reachable: bool | None = None
        self._type: str | None = None

    def __repr__(self) -> str:
        # like default python repr function, but add light name
        return f'<{self.__class__.__module__}.{self.__class__.__name__} object "{self.name}" at {hex(id(self))}>'

    # Wrapper functions for get/set through the bridge, adding support for
    # remembering the transitiontime parameter if the user has set it
    def _get(self, *args: Any, **kwargs: Any) -> Any:
        return self.bridge.get_light(self.light_id, *args, **kwargs)

    def _set(self, *args: Any, **kwargs: Any) -> Any:
        if self.transitiontime is not None:
            kwargs["transitiontime"] = self.transitiontime
            logger.debug(
                f"Setting with transitiontime = {self.transitiontime} ds = {float(self.transitiontime) / 10} s"
            )

            if (args[0] == "on" and args[1] is False) or (
                kwargs.get("on", True) is False
            ):
                self._reset_bri_after_on = True
        return self.bridge.set_light(self.light_id, *args, **kwargs)

    @property
    def name(self) -> str:
        """Get or set the name of the light [string]"""
        fetched_name = self._get("name")
        assert isinstance(fetched_name, str), (
            f"Expected str for name, got {type(fetched_name)}"
        )
        self._name = fetched_name
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        old_name = self.name
        self._name = value
        self._set("name", self._name)

        logger.debug(f"Renaming light from '{old_name}' to '{value}'")

        self.bridge.lights_by_name[self.name] = self
        del self.bridge.lights_by_name[old_name]

    @property
    def on(self) -> bool:
        """Get or set the state of the light [True|False]"""
        self._on = self._get("on")
        assert self._on is not None, "Failed to get 'on' state from bridge."
        assert isinstance(self._on, bool), (
            f"Expected bool for 'on' state, got {type(self._on)}"
        )
        return self._on

    @on.setter
    def on(self, value: bool) -> None:
        # Some added code here to work around known bug where
        # turning off with transitiontime set makes it restart on brightness = 1
        if self._on and value is False:
            self._reset_bri_after_on = self.transitiontime is not None
            if self._reset_bri_after_on:
                logger.warning(
                    "Turned off light with transitiontime specified, brightness will be reset on power on"
                )

        self._set("on", value)

        # work around bug by resetting brightness after a power on
        if self._on is False and value is True:
            if isinstance(self._reset_bri_after_on, bool) and self._reset_bri_after_on:
                logger.warning(
                    "Light was turned off with transitiontime specified, brightness needs to be reset now."
                )
                if self._brightness is not None:
                    self.brightness = self._brightness
                else:
                    logger.warning(
                        "Cannot reset brightness, initial brightness value not available."
                    )
                self._reset_bri_after_on = False

        self._on = value

    @property
    def colormode(self) -> str:
        """Get the color mode of the light [hs|xy|ct]"""
        self._colormode = self._get("colormode")
        assert self._colormode is not None, "Failed to get 'colormode' from bridge."
        assert isinstance(self._colormode, str), (
            f"Expected str for colormode, got {type(self._colormode)}"
        )
        return self._colormode

    @property
    def brightness(self) -> int:
        """Get or set the brightness of the light [0-254].

        0 is not off"""
        self._brightness = self._get("bri")
        assert self._brightness is not None, (
            "Failed to get brightness ('bri') from bridge."
        )
        assert isinstance(self._brightness, int), (
            f"Expected int for brightness, got {type(self._brightness)}"
        )
        return self._brightness

    @brightness.setter
    def brightness(self, value: int) -> None:
        self._brightness = value
        self._set("bri", self._brightness)

    @property
    def hue(self) -> int:
        """Get or set the hue of the light [0-65535]"""
        self._hue = self._get("hue")
        assert self._hue is not None, "Failed to get hue from bridge."
        assert isinstance(self._hue, int), (
            f"Expected int for hue, got {type(self._hue)}"
        )
        return self._hue

    @hue.setter
    def hue(self, value: int) -> None:
        self._hue = int(value)
        self._set("hue", self._hue)

    @property
    def saturation(self) -> int:
        """Get or set the saturation of the light [0-254]

        0 = white
        254 = most saturated
        """
        self._saturation = self._get("sat")
        assert self._saturation is not None, (
            "Failed to get saturation ('sat') from bridge."
        )
        assert isinstance(self._saturation, int), (
            f"Expected int for saturation, got {type(self._saturation)}"
        )
        return self._saturation

    @saturation.setter
    def saturation(self, value: int) -> None:
        self._saturation = value
        self._set("sat", self._saturation)

    @property
    def xy(self) -> tuple[float, float]:
        """Get or set the color coordinates of the light [ [0.0-1.0, 0.0-1.0] ]

        This is in a color space similar to CIE 1931 (but not quite identical)
        """
        self._xy = self._get("xy")
        assert self._xy is not None, (
            "Failed to get color coordinates ('xy') from bridge."
        )
        assert isinstance(self._xy, tuple | list) and len(self._xy) == 2, (
            f"Expected tuple/list of 2 floats for xy, got {self._xy}"
        )
        try:
            xy_tuple = (float(self._xy[0]), float(self._xy[1]))
            self._xy = xy_tuple
            return xy_tuple
        except (ValueError, TypeError, IndexError):
            raise AssertionError(
                f"Could not parse xy coordinates as tuple[float, float]: {self._xy}"
            )

    @xy.setter
    def xy(self, value: tuple[float, float]) -> None:
        self._xy = value
        self._set("xy", self._xy)

    @property
    def colortemp(self) -> int:
        """Get or set the color temperature of the light, in units of mireds [154-500]"""
        self._colortemp = self._get("ct")
        assert self._colortemp is not None, (
            "Failed to get color temperature ('ct') from bridge."
        )
        assert isinstance(self._colortemp, int), (
            f"Expected int for color temperature, got {type(self._colortemp)}"
        )
        return self._colortemp

    @colortemp.setter
    def colortemp(self, value: int) -> None:
        if value < 154:
            logger.warning("154 mireds is coolest allowed color temp")
        elif value > 500:
            logger.warning("500 mireds is warmest allowed color temp")
        self._colortemp = value
        self._set("ct", self._colortemp)

    @property
    def colortemp_k(self) -> int:
        """Get or set the color temperature of the light, in units of Kelvin [2000-6500]"""
        ct_mired = self.colortemp
        return int(round(1e6 / ct_mired))

    @colortemp_k.setter
    def colortemp_k(self, value: int) -> None:
        if value > 6500:
            logger.warning("6500 K is max allowed color temp")
            value = 6500
        elif value < 2000:
            logger.warning("2000 K is min allowed color temp")
            value = 2000

        colortemp_mireds = int(round(1e6 / value))
        logger.debug(f"{value:d} K is {colortemp_mireds} mireds")
        self.colortemp = colortemp_mireds

    @property
    def effect(self) -> str:
        """Check the effect setting of the light. [none|colorloop]"""
        self._effect = self._get("effect")
        assert self._effect is not None, "Failed to get effect from bridge."
        assert isinstance(self._effect, str), (
            f"Expected str for effect, got {type(self._effect)}"
        )
        return self._effect

    @effect.setter
    def effect(self, value: str) -> None:
        self._effect = value
        self._set("effect", self._effect)

    @property
    def alert(self) -> str:
        """Get or set the alert state of the light [select|lselect|none]"""
        self._alert = self._get("alert")
        assert self._alert is not None, "Failed to get alert state from bridge."
        assert isinstance(self._alert, str), (
            f"Expected str for alert state, got {type(self._alert)}"
        )
        return self._alert

    @alert.setter
    def alert(self, value: str | None) -> None:
        if value is None:
            value = "none"
        self._alert = value
        self._set("alert", self._alert)

    @property
    def reachable(self) -> bool:
        """Get the reachable state of the light [boolean]"""
        self._reachable = self._get("reachable")
        assert self._reachable is not None, "Failed to get reachable state from bridge."
        assert isinstance(self._reachable, bool), (
            f"Expected bool for reachable state, got {type(self._reachable)}"
        )
        return self._reachable

    @property
    def type(self) -> str:
        """Get the type of the light [string]"""
        self._type = self._get("type")
        assert self._type is not None, "Failed to get type from bridge."
        assert isinstance(self._type, str), (
            f"Expected str for type, got {type(self._type)}"
        )
        return self._type

"""Group classes for controlling groups of Philips Hue lights."""

import logging
from typing import TYPE_CHECKING, Any

from phue.light import Light

logger = logging.getLogger("phue_modern")

if TYPE_CHECKING:
    from phue.bridge import Bridge


class Group(Light):
    """A group of Hue lights, tracked as a group on the bridge

    Example:

        >>> b = Bridge()
        >>> g1 = Group(b, 1)
        >>> g1.hue = 50000 # all lights in that group turn blue
        >>> g1.on = False # all will turn off

        >>> g2 = Group(b, 'Kitchen')  # you can also look up groups by name
        >>> # will raise a LookupError if the name doesn't match
    """

    def __init__(self, bridge: "Bridge", group_id: int | str):
        Light.__init__(self, bridge, 0)  # Light ID will be overridden
        self.light_id = None  # not relevant for a group
        self._any_on: bool | None = None
        self._all_on: bool | None = None
        self.group_id: int

        try:
            self.group_id = int(group_id)
        except ValueError:
            name = str(group_id)
            groups = bridge.get_group()
            for idnumber, info in groups.items():
                if info["name"] == name:
                    self.group_id = int(idnumber)
                    break
            else:
                raise LookupError("Could not find a group by that name.")

    # Wrapper functions for get/set through the bridge, adding support for
    # remembering the transitiontime parameter if the user has set it
    def _get(self, *args: Any, **kwargs: Any) -> Any:
        return self.bridge.get_group(self.group_id, *args, **kwargs)

    def _set(self, *args: Any, **kwargs: Any) -> Any:
        # let's get basic group functionality working first before adding
        # transition time...
        if self.transitiontime is not None:
            kwargs["transitiontime"] = self.transitiontime
            logger.debug(
                f"Setting with transitiontime = {self.transitiontime} ds = {float(self.transitiontime) / 10} s"
            )

            if (args[0] == "on" and args[1] is False) or (
                kwargs.get("on", True) is False
            ):
                self._reset_bri_after_on = True
        return self.bridge.set_group(self.group_id, *args, **kwargs)

    @property
    def name(self) -> str:
        """Get or set the name of the light group [string]"""
        return self._get("name")

    @name.setter
    def name(self, value: str) -> None:
        old_name = self.name
        self._name = value
        logger.debug(f"Renaming light group from '{old_name}' to '{value}'")
        self._set("name", self._name)

    @property
    def any_on(self) -> bool:
        """If true at least one light in the group is on"""
        self._any_on = self._get("any_on")
        return self._any_on or False

    @property
    def all_on(self) -> bool:
        """If true all lights in the group are on"""
        self._all_on = self._get("all_on")
        return self._all_on or False

    @property
    def lights(self) -> list[Light]:
        """Return a list of all lights in this group"""
        return [Light(self.bridge, int(light_id)) for light_id in self._get("lights")]

    @lights.setter
    def lights(self, value: list[int]) -> None:
        """Change the lights that are in this group"""
        logger.debug(f"Setting lights in group {self.group_id} to {str(value)}")
        self._set("lights", value)


class AllLights(Group):
    """All the Hue lights connected to your bridge

    This makes use of the semi-documented feature that
    "Group 0" of lights appears to be a group automatically
    consisting of all lights.  This is not returned by
    listing the groups, but is accessible if you explicitly
    ask for group 0.
    """

    def __init__(self, bridge: "Bridge | None" = None):
        if bridge is None:
            from .bridge import Bridge

            bridge = Bridge()
        Group.__init__(self, bridge, 0)

"""
phue - A modernized Philips Hue Python library
Based on the original phue by Nathanaël Lécaudé
Original protocol hacking by rsmck: http://rsmck.co.uk/hue

Published under the MIT license

"Hue Personal Wireless Lighting" is a trademark owned by Koninklijke Philips Electronics N.V.
"""

from .exceptions import PhueException, PhueRegistrationException, PhueRequestTimeout
from .light import Light
from .sensor import Sensor, SensorState, SensorConfig
from .group import Group, AllLights
from .scene import Scene
from .bridge import Bridge
from ._internal.console import console

import logging

logger = logging.getLogger("phue")


__all__ = [
    "Bridge",
    "PhueException",
    "PhueRegistrationException",
    "PhueRequestTimeout",
    "Light",
    "Group",
    "AllLights",
    "Scene",
    "Sensor",
    "SensorState",
    "SensorConfig",
    "console",
]

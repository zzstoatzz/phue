"""Scene class for Philips Hue scenes."""

from typing import Any


class Scene:
    """Container for Scene"""

    def __init__(
        self,
        sid: str,
        appdata: dict[str, Any] | None = None,
        lastupdated: str | None = None,
        lights: list[str] | None = None,
        locked: bool = False,
        name: str = "",
        owner: str = "",
        picture: str = "",
        recycle: bool = False,
        version: int = 0,
        type: str = "",
        group: str = "",
        **kwargs: Any,  # Accept additional parameters from API
    ):
        """Initialize a Scene object.

        Args:
            sid: Scene ID
            appdata: Application data associated with the scene
            lastupdated: Last time the scene was updated
            lights: List of light IDs in the scene
            locked: Whether the scene is locked
            name: Name of the scene
            owner: Owner of the scene
            picture: Picture associated with the scene
            recycle: Whether the scene can be recycled
            version: Version of the scene
            type: Type of the scene
            group: Group associated with the scene
            **kwargs: Additional parameters from the API (e.g., 'image')
        """
        self.scene_id = sid
        self.appdata = appdata or {}
        self.lastupdated = lastupdated
        if lights is not None:
            self.lights = sorted([int(x) for x in lights])
        else:
            self.lights = []
        self.locked = locked
        self.name = name
        self.owner = owner
        self.picture = picture
        self.recycle = recycle
        self.version = version
        self.type = type
        self.group = group

    def __repr__(self) -> str:
        # like default python repr function, but add scene name
        return f'<{self.__class__.__module__}.{self.__class__.__name__} id="{self.scene_id}" name="{self.name}" lights={self.lights}>'

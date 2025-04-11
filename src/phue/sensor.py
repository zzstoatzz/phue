"""Sensor classes for interacting with Philips Hue sensors."""

import logging
from collections import UserDict
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeAlias

if TYPE_CHECKING:
    from phue import Bridge

logger = logging.getLogger("phue_modern")

SensorData: TypeAlias = dict[str, Any]


class _SensorDataWrapper(UserDict[str, Any]):
    """
    Base class for Sensor State/Config wrappers using UserDict.
    Updates the bridge when an item is set.
    Holds a cached view of the state/config.
    """

    # UserDict stores data in the 'data' attribute (which is a dict)
    data: SensorData

    def __init__(
        self, bridge: "Bridge", sensor_id: int, initial_data: SensorData | None = None
    ):
        super().__init__(initial_data or {})
        self._bridge = bridge
        self._sensor_id = sensor_id
        # Store the method responsible for updating the bridge (state or config)
        self._update_bridge_method: Callable[[int, SensorData], Any] = (
            self._get_bridge_update_method()
        )

    def _get_bridge_update_method(self) -> Callable[[int, SensorData], Any]:
        # This method should be implemented by subclasses
        raise NotImplementedError

    def __setitem__(self, key: str, value: Any) -> None:
        """Sets an item locally and updates the bridge."""
        # Optional: Check if the value is actually changing to avoid unnecessary API calls
        if key in self.data and self.data[key] == value:
            logger.debug(
                f"Skipping bridge update for sensor {self._sensor_id}: key '{key}' value unchanged."
            )
            return

        # Update local cache *before* calling the bridge
        # If the bridge call fails, the local cache reflects the intended state.
        # Alternatively, update after bridge call succeeds if you want cache
        # to always reflect confirmed bridge state. Let's update before for responsiveness.
        super().__setitem__(key, value)

        # Update the bridge with *only the changed key/value pair*
        update_payload = {key: value}
        try:
            logger.debug(
                f"Updating bridge for sensor {self._sensor_id}: {update_payload}"
            )
            self._update_bridge_method(self._sensor_id, update_payload)
        except Exception as e:
            # Handle potential API errors (e.g., network issues, invalid key/value)
            logger.error(
                f"Failed to update bridge for sensor {self._sensor_id} with {update_payload}: {e}"
            )
            # Optional: Revert local change if bridge update fails?
            # Depends on desired behavior. For now, keep local change.
            # Consider raising the exception or providing feedback.
            # For simplicity here, we just log the error.

    def update(self, *args: Any, **kwargs: Any) -> None:
        """
        Updates the dictionary with multiple items.
        Calls the bridge update method for each changed item individually.
        Note: This may result in multiple API calls. If the bridge API supports
        updating multiple keys in one call, this could be optimized.
        """
        # UserDict.update handles merging args and kwargs into self.data
        # We need to intercept this to call the bridge for each change.
        temp_dict = dict(*args, **kwargs)
        for key, value in temp_dict.items():
            # This will call our overridden __setitem__, which handles bridge update
            self[key] = value

    def sync_from_bridge_data(self, data: SensorData) -> None:
        """
        Updates the local cache directly from data fetched from the bridge,
        bypassing the bridge update mechanism (__setitem__).
        """
        # Use super().update to modify self.data directly without triggering __setitem__
        self.data.clear()
        self.data.update(data)
        # Alternatively: super().update(data) if you want to merge instead of replace.
        # Clearing first ensures the cache exactly matches the fetched data.


class SensorState(_SensorDataWrapper):
    """
    State of a Hue sensor. Updates bridge state on item set.
    Provides a dictionary-like interface to a cached view of the sensor state.
    """

    def _get_bridge_update_method(self):
        return self._bridge.set_sensor_state


class SensorConfig(_SensorDataWrapper):
    """
    Configuration of a Hue sensor. Updates bridge config on item set.
    Provides a dictionary-like interface to a cached view of the sensor config.
    """

    def _get_bridge_update_method(self):
        return self._bridge.set_sensor_config


class Sensor:
    """
    Hue Sensor object.

    Provides access to sensor properties, state, and configuration.
    State and config are cached locally. Modifying `sensor.state['key'] = value`
    or `sensor.config['key'] = value` will update the bridge.
    Call `sensor.refresh()` to update the local cache from the bridge.
    """

    # Type hint for the bridge reference
    bridge: "Bridge"
    sensor_id: int

    # Private attributes for caching
    # Use Optional[T] and initialize to None to indicate they haven't been fetched yet.
    _raw_data: SensorData | None = None
    _state: SensorState
    _config: SensorConfig
    # Cache basic attributes to avoid repeated parsing/dict access
    _name: str | None = None
    _modelid: str | None = None
    _swversion: str | None = None
    _type: str | None = None
    _uniqueid: str | None = None
    _manufacturername: str | None = None
    _recycle: bool | None = None

    def __init__(self, bridge: "Bridge", sensor_id: int):
        self.bridge = bridge
        self.sensor_id = sensor_id

        # Initialize state and config wrappers without initial data.
        # Data will be populated by refresh() or on first access.
        self._state = SensorState(bridge, sensor_id)
        self._config = SensorConfig(bridge, sensor_id)  # Use SensorConfig

    def __repr__(self) -> str:
        # Fetch name for repr if not already cached. Handle potential errors.
        try:
            name = self.name  # Use the property to ensure data is loaded
        except Exception:
            name = f"ID {self.sensor_id}"  # Fallback if name fetch fails
        return f'<{self.__class__.__module__}.{self.__class__.__name__} object "{name}" at {hex(id(self))}>'

    def refresh(self) -> None:
        """Fetches the latest data from the bridge and updates the local cache."""
        logger.debug(f"Refreshing data for sensor {self.sensor_id}")
        try:
            # Assume bridge.get_sensor(id) returns the full sensor dictionary
            self._raw_data = self.bridge.get_sensor(self.sensor_id)
            if not isinstance(self._raw_data, dict):
                raise TypeError(
                    f"Expected dict from bridge.get_sensor, got {type(self._raw_data)}"
                )
        except Exception as e:
            logger.error(f"Failed to refresh data for sensor {self.sensor_id}: {e}")
            # Keep stale data or clear it? Let's keep stale data and log error.
            # self._raw_data = None # Option: clear cache on failure
            raise  # Re-raise the exception so the caller knows refresh failed

        # Update cached attributes directly from raw data
        self._name = self._raw_data.get("name")
        self._modelid = self._raw_data.get("modelid")
        self._swversion = self._raw_data.get("swversion")
        self._type = self._raw_data.get("type")
        self._uniqueid = self._raw_data.get("uniqueid")
        self._manufacturername = self._raw_data.get("manufacturername")
        self._recycle = self._raw_data.get("recycle")

        # Update state and config caches using the sync method (avoids bridge writes)
        self._state.sync_from_bridge_data(self._raw_data.get("state", {}))
        self._config.sync_from_bridge_data(self._raw_data.get("config", {}))
        logger.debug(f"Sensor {self.sensor_id} data refreshed successfully.")

    def _ensure_data(self) -> None:
        """Ensures sensor data has been fetched at least once, calling refresh() if needed."""
        if self._raw_data is None:
            logger.debug(f"Initial data fetch for sensor {self.sensor_id}")
            self.refresh()  # This will fetch and populate everything

    # --- Properties ---

    @property
    def name(self) -> str:
        """Get or set the name of the sensor [string]. Fetches data on first access."""
        self._ensure_data()
        # Provide a default/fallback if name is somehow missing after refresh
        return self._name or f"Sensor {self.sensor_id}"

    @name.setter
    def name(self, value: str) -> None:
        if not isinstance(value, str):  # type: ignore[unnecessary-isinstance]
            raise TypeError("Sensor name must be a string")

        # Get the current name (ensures data is loaded if it wasn't already)
        old_name = self.name
        if old_name == value:
            return  # No change needed

        logger.debug(
            f"Attempting to rename sensor {self.sensor_id} from '{old_name}' to '{value}'"
        )
        try:
            # Use bridge.set_sensor for top-level attributes like name
            self.bridge.set_sensor(self.sensor_id, {"name": value})
        except Exception as e:
            logger.error(
                f"Failed to set name for sensor {self.sensor_id} via bridge: {e}"
            )
            raise  # Re-raise exception

        # Update local cache only after successful bridge call
        self._name = value
        if self._raw_data:  # Update raw data cache if it exists
            self._raw_data["name"] = value

        # Update bridge's name lookup cache (if it exists and is used)
        if hasattr(self.bridge, "sensors_by_name"):
            # Be careful modifying another object's state directly
            # Ensure this is the intended interaction pattern with the Bridge class
            if old_name in self.bridge.sensors_by_name:
                del self.bridge.sensors_by_name[old_name]
            self.bridge.sensors_by_name[value] = self
        logger.info(f"Sensor {self.sensor_id} renamed to '{value}'")

    # Read-only properties using the cache
    @property
    def modelid(self) -> str | None:
        """Get hardware model ID [string, read-only]. Fetches data on first access."""
        self._ensure_data()
        return self._modelid

    @property
    def swversion(self) -> str | None:
        """Get firmware version [string, read-only]. Fetches data on first access."""
        self._ensure_data()
        return self._swversion

    @property
    def type(self) -> str | None:
        """Get sensor type [string, read-only]. Fetches data on first access."""
        self._ensure_data()
        return self._type

    @property
    def uniqueid(self) -> str | None:
        """Get unique device ID [string, read-only]. Fetches data on first access."""
        self._ensure_data()
        return self._uniqueid

    @property
    def manufacturername(self) -> str | None:
        """Get manufacturer name [string, read-only]. Fetches data on first access."""
        self._ensure_data()
        return self._manufacturername

    @property
    def recycle(self) -> bool | None:
        """Check if resource should be auto-removed [bool, read-only]. Fetches data on first access."""
        self._ensure_data()
        return self._recycle

    # State and Config properties return the cached wrapper objects
    @property
    def state(self) -> SensorState:
        """
        Get the cached state of the sensor [SensorState].
        Modifying items (e.g., `sensor.state['on'] = True`) updates the bridge.
        Call `sensor.refresh()` to sync cache from the bridge.
        Fetches data on first access.
        """
        self._ensure_data()
        return self._state

    # Removed state.setter - modifications happen via the returned object

    @property
    def config(self) -> SensorConfig:
        """
        Get the cached config of the sensor [SensorConfig].
        Modifying items (e.g., `sensor.config['on'] = True`) updates the bridge.
        Call `sensor.refresh()` to sync cache from the bridge.
        Fetches data on first access.
        """
        self._ensure_data()
        return self._config

    # Removed config.setter - modifications happen via the returned object

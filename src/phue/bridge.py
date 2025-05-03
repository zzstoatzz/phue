"""Bridge class for controlling Philips Hue bridges."""

import json
import logging
import os
import platform
from collections.abc import Hashable, Iterable
from typing import TYPE_CHECKING, Any, Literal, cast, overload

import httpx

from phue.exceptions import (
    PhueException,
    PhueRegistrationException,
    PhueRequestTimeout,
)
from phue.group import Group
from phue.light import Light
from phue.scene import Scene
from phue.sensor import Sensor

logger = logging.getLogger("phue_modern")


class Bridge:
    """Interface to the Hue ZigBee bridge

    You can obtain Light objects by calling the get_light_objects method:

        >>> b = Bridge(ip='192.168.1.100')
        >>> b.get_light_objects()
        [<phue_modern.Light at 0x10473d750>,
         <phue_modern.Light at 0x1046ce110>]

    Or more succinctly just by accessing this Bridge object as a list or dict:

        >>> b[1]
        <phue_modern.Light at 0x10473d750>
        >>> b['Kitchen']
        <phue_modern.Light at 0x10473d750>
    """

    def __init__(
        self,
        ip: str | None = None,
        username: str | None = None,
        config_file_path: str | None = None,
        timeout: int = 10,
        save_config: bool = True,
    ):
        """Initialization function.

        Args:
            ip: IP address as dotted quad
            username: Optional username for the bridge
            config_file_path: Optional path to the configuration file
            timeout: Request timeout in seconds (default: 10)
            save_config: If False, don't save the config file (default: True)
        """
        # Determine config file path
        if config_file_path is not None:
            self.config_file_path = config_file_path
        else:
            # Define the home environment variable name based on platform
            if platform.system() == "Windows":
                user_home_env_var = "USERPROFILE"
            else:
                user_home_env_var = "HOME"

            # Get the actual home path using the correct env var name
            user_home_path = os.getenv(user_home_env_var)
            if user_home_path is not None and os.access(user_home_path, os.W_OK):
                # Use user home path if writable
                self.config_file_path = os.path.join(user_home_path, ".python_hue")
            elif (
                (
                    "iPad" in platform.machine()
                    or "iPhone" in platform.machine()
                    or "iPod" in platform.machine()
                )
                and user_home_path is not None  # Check user_home_path exists here too
            ):
                # Use Documents directory on iOS-like platforms
                self.config_file_path = os.path.join(
                    user_home_path, "Documents", ".python_hue"
                )
            else:
                # Fallback to current working directory
                self.config_file_path = os.path.join(os.getcwd(), ".python_hue")

        self.ip = ip
        self._username = username
        self.timeout = timeout
        self.save_config = save_config
        self.lights_by_id: dict[int, Light] = {}
        self.lights_by_name: dict[str, Light] = {}
        self.sensors_by_id: dict[int, Sensor] = {}
        self.sensors_by_name: dict[str, Sensor] = {}
        self._name: str | None = None

        self.connect()

    @property
    def username(self) -> str:
        assert self._username is not None
        return self._username

    @property
    def name(self) -> str:
        """Get or set the name of the bridge [string]"""
        name = self.request("GET", "/api/" + self.username + "/config")["name"]
        self._name = name
        return name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value
        data = {"name": self._name}
        self.request("PUT", "/api/" + self.username + "/config", data)

    def request(
        self,
        method: str = "GET",
        address: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> Any:
        """Utility function for HTTP requests for the API.

        Args:
            method: HTTP method (GET, PUT, POST, DELETE)
            address: API endpoint address
            data: Optional data to send with the request

        Returns:
            The parsed JSON response from the API

        Raises:
            PhueRequestTimeout: If the request times out
            PhueException: If the request fails
        """
        url = f"http://{self.ip}{address}"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                if method == "GET" or method == "DELETE":
                    response = client.request(method, url)
                elif method == "PUT" or method == "POST":
                    response = client.request(method, url, json=data)
                else:
                    raise ValueError(f"Unsupported method: {method}")

                logger.debug(f"{method} {address} {str(data)}")
                response.raise_for_status()
                return response.json()

        except httpx.TimeoutException:
            error = f"{method} Request to {url} timed out."
            logger.exception(error)
            raise PhueRequestTimeout(-1, error)
        except httpx.HTTPStatusError as e:
            error = f"{method} Request to {url} failed with status code {e.response.status_code}"
            logger.exception(error)
            raise PhueException(e.response.status_code, error)
        except Exception as e:
            error = f"{method} Request to {url} failed: {str(e)}"
            logger.exception(error)
            raise PhueException(-1, error)

    def get_ip_address(self, set_result: bool = False) -> str | None:
        """Get the bridge ip address from the meethue.com nupnp api.

        Args:
            set_result: If True, set the IP address of this Bridge object

        Returns:
            The IP address if found, otherwise None
        """
        try:
            with httpx.Client() as client:
                response = client.get("https://www.meethue.com/api/nupnp")
                response.raise_for_status()
                data = response.json()

                logger.info("Connected to meethue.com/api/nupnp")

                if not data:
                    logger.warning(
                        "No bridges found via meethue.com API. Your bridge may not be connected to the internet "
                        "or registered with the Hue cloud service. Try specifying the IP address manually."
                    )
                    return None

                ip = str(data[0]["internalipaddress"])

                if ip and set_result:
                    self.ip = ip

                return ip
        except Exception as e:
            logger.error(
                f"Error getting IP address: {str(e)}. "
                "Unable to discover bridge IP automatically. Consider the following steps:\n"
                "1. Find your bridge IP in the Hue app (Settings > My Bridge)\n"
                "2. Check your router's connected devices list\n"
                "3. Use network scanning tools like 'nmap'\n"
                "Then initialize the Bridge with explicit IP: phue.Bridge(ip='192.168.x.x')"
            )
            return None

    def register_app(self) -> None:
        """Register this computer with the Hue bridge hardware and save the resulting access token.

        Raises:
            PhueRegistrationException: If the link button has not been pressed
            PhueException: If registration fails for other reasons
        """
        if self.ip is None:
            raise PhueException(
                -1,
                "Cannot register without an IP address. Specify the bridge IP: "
                "bridge = phue.Bridge(ip='192.168.x.x')",
            )

        registration_request = {"devicetype": "python_hue_modern"}
        try:
            response = self.request("POST", "/api", registration_request)
        except PhueException as e:
            if "Failed to connect" in str(e) or "Connection refused" in str(e):
                raise PhueException(
                    -1,
                    f"Failed to connect to bridge at {self.ip}. Verify the IP address is correct "
                    "and that the bridge is powered on and connected to your network.",
                )
            raise

        for line in response:
            for key in line:
                if "success" in key:
                    if self.save_config:
                        with open(self.config_file_path, "w") as f:
                            logger.info(
                                "Writing configuration file to " + self.config_file_path
                            )
                            f.write(json.dumps({self.ip: line["success"]}))
                            logger.info("Reconnecting to the bridge")
                    self._username = line["success"]["username"]
                    return
                if "error" in key:
                    error_type = line["error"]["type"]
                    if error_type == 101:
                        raise PhueRegistrationException(
                            error_type,
                            "The link button has not been pressed in the last 30 seconds. "
                            "Please press the button on the bridge and try again.",
                        )
                    if error_type == 7:
                        raise PhueException(error_type, "Unknown username")

    def connect(self) -> None:
        """Connect to the Hue bridge.

        Attempts to connect to the bridge using the provided IP and username,
        or tries to load them from the config file. If that fails, it will
        attempt to register with the bridge.
        """
        logger.info("Attempting to connect to the bridge...")
        # If the ip and username were provided at class init
        if self.ip is not None and self._username is not None:
            logger.info("Using ip: " + self.ip)
            logger.info("Using username: " + self._username)
            return

        if self.ip is None or self._username is None:
            try:
                with open(self.config_file_path) as f:
                    config = json.loads(f.read())
                    if self.ip is None:
                        self.ip = list(config.keys())[0]
                        logger.info("Using ip from config: " + self.ip)
                    else:
                        logger.info("Using ip: " + self.ip)
                    if self._username is None:
                        self._username = config[self.ip]["username"]
                        logger.info("Using username from config: " + self._username)
                    else:
                        logger.info("Using username: " + self._username)
            except FileNotFoundError:
                logger.info("Config file not found, will attempt bridge registration")
                if self.ip is None:
                    ip = self.get_ip_address(set_result=True)
                    if ip is None:
                        error_msg = (
                            "Could not find bridge IP address. Please specify it manually:\n"
                            "bridge = phue.Bridge(ip='192.168.x.x')"
                        )
                        logger.error(error_msg)
                        raise PhueException(-1, error_msg)

                self.register_app()
            except json.JSONDecodeError:
                logger.error(
                    "Config file is not valid JSON, will attempt bridge registration"
                )
                self.register_app()
            except Exception as e:
                logger.error(f"Error opening config file: {str(e)}")
                if self.ip is None:
                    error_msg = (
                        "Could not load config and no IP address specified. "
                        "Please initialize with an IP address: phue.Bridge(ip='192.168.x.x')"
                    )
                    logger.error(error_msg)
                    raise PhueException(-1, error_msg)
                self.register_app()

    def get_light_id_by_name(self, name: str) -> int | None:
        """Lookup a light id based on string name. Case-sensitive.

        Args:
            name: The name of the light to look up

        Returns:
            The light ID if found, otherwise None
        """
        lights = self.get_light()
        for light_id in lights:
            if name == lights[light_id]["name"]:
                return int(light_id)
        return None

    @overload
    def get_light_objects(self) -> list[Light]: ...
    @overload
    def get_light_objects(self, mode: Literal["id"]) -> dict[int, Light]: ...

    @overload
    def get_light_objects(self, mode: Literal["name"]) -> dict[str, Light]: ...

    @overload
    def get_light_objects(self, mode: Literal["list"]) -> list[Light]: ...

    def get_light_objects(
        self, mode: str = "list"
    ) -> list[Light] | dict[int, Light] | dict[str, Light]:
        """Returns a collection containing the lights, either by name or id.

        Args:
            mode: The return format - 'list' (default), 'id', or 'name'
                'list': return a list of Light objects in order by ID
                'id': return a dict of Light objects by light ID
                'name': return a dict of Light objects by light name

        Returns:
            A collection of Light objects in the requested format
        """
        if not self.lights_by_id:
            lights = self.request("GET", "/api/" + self.username + "/lights/")
            for light in lights:
                light_id = int(light)
                self.lights_by_id[light_id] = Light(self, light_id)
                self.lights_by_name[lights[light]["name"]] = self.lights_by_id[light_id]

        if mode == "id":
            return self.lights_by_id
        if mode == "name":
            return self.lights_by_name
        if mode == "list":
            # return lights in sorted id order, dicts have no natural order
            return [self.lights_by_id[id] for id in sorted(self.lights_by_id)]
        raise ValueError(f"Invalid mode: {mode}")

    def get_sensor_id_by_name(self, name: str) -> int | None:
        """Lookup a sensor id based on string name. Case-sensitive.

        Args:
            name: The name of the sensor to look up

        Returns:
            The sensor ID if found, otherwise None
        """
        sensors = self.get_sensor()
        for sensor_id in sensors:
            if name == sensors[sensor_id]["name"]:
                return int(sensor_id)
        return None

    @overload
    def get_sensor_objects(self) -> list[Sensor]: ...
    @overload
    def get_sensor_objects(self, mode: Literal["list"]) -> list[Sensor]: ...

    @overload
    def get_sensor_objects(self, mode: Literal["id"]) -> dict[int, Sensor]: ...

    @overload
    def get_sensor_objects(self, mode: Literal["name"]) -> dict[str, Sensor]: ...

    def get_sensor_objects(
        self, mode: Literal["list", "id", "name"] = "list"
    ) -> list[Sensor] | dict[int, Sensor] | dict[str, Sensor]:
        """Returns a collection containing the sensors, either by name or id.

        Args:
            mode: The return format - 'list' (default), 'id', or 'name'
                'list': return a list of Sensor objects
                'id': return a dict of Sensor objects by sensor ID
                'name': return a dict of Sensor objects by sensor name

        Returns:
            A collection of Sensor objects in the requested format
        """
        if not self.sensors_by_id:
            sensors = self.request("GET", "/api/" + self.username + "/sensors/")
            for sensor in sensors:
                sensor_id = int(sensor)
                self.sensors_by_id[sensor_id] = Sensor(self, sensor_id)
                self.sensors_by_name[sensors[sensor]["name"]] = self.sensors_by_id[
                    sensor_id
                ]

        if mode == "id":
            return self.sensors_by_id
        if mode == "name":
            return self.sensors_by_name
        if mode == "list":
            return list(self.sensors_by_id.values())

    def __getitem__(self, key: int | str) -> Light:
        """Lights are accessible by indexing the bridge either with
        an integer index or string name.

        Args:
            key: Either a light ID (int) or a light name (str)

        Returns:
            The Light object corresponding to the key

        Raises:
            KeyError: If the key is not a valid light ID or name
        """
        if not self.lights_by_id:
            self.get_light_objects("id")

        try:
            if isinstance(key, int):
                return self.lights_by_id[key]
            else:
                return self.lights_by_name[key]
        except KeyError:
            raise KeyError(
                "Not a valid key (integer index starting with 1, or light name): "
                + str(key)
            )

    @property
    def lights(self) -> list[Light]:
        """Access lights as a list"""
        return self.get_light_objects("list")

    def get_api(self) -> dict[str, Any]:
        """Returns the full api dictionary"""
        return self.request("GET", "/api/" + self.username)

    def get_light(
        self, light_id: int | str | None = None, parameter: str | None = None
    ) -> Any:
        """Gets state by light_id and parameter.

        Args:
            light_id: The ID of the light, or the name of the light, or None to get all lights
            parameter: The parameter to get, or None to get all parameters

        Returns:
            The requested parameter value, or a dict of all parameters if parameter is None

        Raises:
            KeyError: If the parameter is not valid for the light
        """
        if isinstance(light_id, str) and not light_id.isdigit():
            light_id = self.get_light_id_by_name(light_id)

        if light_id is None:
            return self.request("GET", "/api/" + self.username + "/lights/")

        state = self.request(
            "GET", "/api/" + self.username + "/lights/" + str(light_id)
        )

        if parameter is None:
            return state
        if parameter in ["name", "type", "uniqueid", "swversion"]:
            return state[parameter]
        else:
            try:
                return state["state"][parameter]
            except KeyError:
                raise KeyError(
                    f"Not a valid key, parameter {parameter} is not associated with light {light_id}"
                )

    def set_light(
        self,
        light_id: int | str | list[int] | list[str],
        parameter: str | dict[str, Any],
        value: Any = None,
        transitiontime: int | None = None,
    ) -> list[dict[Hashable, Any]]:
        """Adjust properties of one or more lights.

        Args:
            light_id: A single light ID/name or a list of light IDs/names
            parameter: Either a parameter name or a dict of parameters to set
            value: The value to set if parameter is a string
            transitiontime: Time for this transition to take place (in deciseconds)
                            Note that transitiontime only applies to this light command,
                            it is not saved as a setting for future use.

        Returns:
            A list of responses from the API
        """
        if isinstance(parameter, dict):
            data = parameter
        else:
            data = {parameter: value}

        if transitiontime is not None:
            data["transitiontime"] = int(
                round(transitiontime)
            )  # must be int for request format

        light_id_array: list[Any] = []
        if isinstance(light_id, int | str):
            light_id_array = [light_id]
        else:
            light_id_array = light_id

        result: list[dict[Hashable, Any]] = []
        for light in light_id_array:
            logger.debug(str(data))
            if parameter == "name":
                result.append(
                    self.request(
                        "PUT",
                        "/api/" + self.username + "/lights/" + str(light),
                        data,
                    )
                )
            else:
                if isinstance(light, str) and not light.isdigit():
                    converted_light = self.get_light_id_by_name(light)
                    if converted_light is None:
                        logger.warning(f"Could not find light with name: {light}")
                        continue
                else:
                    converted_light = light
                result.append(
                    self.request(
                        "PUT",
                        "/api/"
                        + self.username
                        + "/lights/"
                        + str(converted_light)
                        + "/state",
                        data,
                    )
                )
            if (
                result
                and isinstance(result[-1], list)
                and result[-1]
                and "error" in result[-1][0]
            ):
                logger.warning(
                    f"ERROR: {result[-1][0]['error']['description']} for light {light}"
                )

        logger.debug(result)
        return result

    # Sensors #####
    @property
    def sensors(self) -> list[Sensor]:
        """Access sensors as a list"""
        return self.get_sensor_objects()

    def create_sensor(
        self,
        name: str,
        modelid: str,
        swversion: str,
        sensor_type: str,
        uniqueid: str,
        manufacturername: str,
        state: dict[str, Any] = {},
        config: dict[str, Any] = {},
        recycle: bool = False,
    ) -> tuple[int | None, dict[str, Any] | None]:
        """Create a new sensor in the bridge.

        Args:
            name: Name for the sensor
            modelid: Model ID of the sensor
            swversion: Software version of the sensor
            sensor_type: Type of the sensor
            uniqueid: Unique ID of the sensor
            manufacturername: Manufacturer name
            state: Optional state dictionary
            config: Optional config dictionary
            recycle: Whether the sensor should be automatically removed when last reference is gone

        Returns:
            A tuple of (new_id, None) if created successfully, or (None, error) if failed
        """
        data: dict[str, Any] = {
            "name": name,
            "modelid": modelid,
            "swversion": swversion,
            "type": sensor_type,
            "uniqueid": uniqueid,
            "manufacturername": manufacturername,
            "recycle": recycle,
        }

        if state:
            data["state"] = state

        if config:
            data["config"] = config

        result = self.request("POST", "/api/" + self.username + "/sensors/", data)

        if "success" in result[0]:
            new_id = int(result[0]["success"]["id"])
            logger.debug(f"Created sensor with ID {new_id}")
            new_sensor = Sensor(self, new_id)
            self.sensors_by_id[new_id] = new_sensor
            self.sensors_by_name[name] = new_sensor
            return new_id, None
        else:
            logger.debug(f"Failed to create sensor: {result[0]}")
            return None, result[0]

    def get_sensor(
        self, sensor_id: int | str | None = None, parameter: str | None = None
    ) -> Any:
        """Gets state by sensor_id and parameter.

        Args:
            sensor_id: The ID of the sensor, or the name of the sensor, or None to get all sensors
            parameter: The parameter to get, or None to get all parameters

        Returns:
            The requested parameter value, or a dict of all parameters if parameter is None,
            or None if the sensor could not be found
        """
        if isinstance(sensor_id, str) and not sensor_id.isdigit():
            sensor_id = self.get_sensor_id_by_name(sensor_id)

        if sensor_id is None:
            return self.request("GET", "/api/" + self.username + "/sensors/")

        data = self.request(
            "GET", "/api/" + self.username + "/sensors/" + str(sensor_id)
        )

        if isinstance(data, list):
            logger.debug(f"Unable to read sensor with ID {sensor_id}: {data}")
            return None

        if parameter is None:
            return data
        return data[parameter]

    def set_sensor(
        self, sensor_id: int, parameter: str | dict[str, Any], value: Any = None
    ) -> Any:
        """Adjust properties of a sensor.

        Args:
            sensor_id: The ID of the sensor
            parameter: Either a parameter name or a dict of parameters to set
            value: The value to set if parameter is a string

        Returns:
            The response from the API
        """
        if isinstance(parameter, dict):
            data = parameter
        else:
            data = {parameter: value}

        logger.debug(str(data))
        result = self.request(
            "PUT", "/api/" + self.username + "/sensors/" + str(sensor_id), data
        )

        if isinstance(result, list) and result and "error" in result[0]:
            logger.warning(
                f"ERROR: {result[0]['error']['description']} for sensor {sensor_id}"
            )

        if TYPE_CHECKING:
            result = cast(list[dict[str, Any]], result)

        logger.debug(result)
        return result

    def set_sensor_state(
        self, sensor_id: int, parameter: str | dict[str, Any], value: Any = None
    ) -> Any:
        """Adjust the "state" object of a sensor.

        Args:
            sensor_id: The ID of the sensor
            parameter: Either a parameter name or a dict of parameters to set
            value: The value to set if parameter is a string

        Returns:
            The response from the API
        """
        return self.set_sensor_content(sensor_id, parameter, value, "state")

    def set_sensor_config(
        self, sensor_id: int, parameter: str | dict[str, Any], value: Any = None
    ) -> Any:
        """Adjust the "config" object of a sensor.

        Args:
            sensor_id: The ID of the sensor
            parameter: Either a parameter name or a dict of parameters to set
            value: The value to set if parameter is a string

        Returns:
            The response from the API
        """
        return self.set_sensor_content(sensor_id, parameter, value, "config")

    def set_sensor_content(
        self,
        sensor_id: int,
        parameter: str | dict[str, Any],
        value: Any = None,
        structure: str = "state",
    ) -> Any:
        """Adjust the "state" or "config" structures of a sensor.

        Args:
            sensor_id: The ID of the sensor
            parameter: Either a parameter name or a dict of parameters to set
            value: The value to set if parameter is a string
            structure: Either "state" or "config"

        Returns:
            The response from the API, or False if the structure is invalid
        """
        if structure != "state" and structure != "config":
            logger.debug("set_sensor_content expects structure 'state' or 'config'.")
            return False

        if isinstance(parameter, dict):
            data = parameter.copy()
        else:
            data = {parameter: value}

        # Attempting to set this causes an error.
        if "lastupdated" in data:
            del data["lastupdated"]

        logger.debug(str(data))
        result = self.request(
            "PUT",
            "/api/" + self.username + "/sensors/" + str(sensor_id) + "/" + structure,
            data,
        )

        if isinstance(result, list) and result and "error" in result[0]:
            logger.warning(
                f"ERROR: {result[0]['error']['description']} for sensor {sensor_id}"
            )

        if TYPE_CHECKING:
            result = cast(list[dict[str, Any]], result)

        logger.debug(result)
        return result

    def delete_sensor(self, sensor_id: int) -> Any:
        """Delete a sensor from the bridge.

        Args:
            sensor_id: The ID of the sensor to delete

        Returns:
            The response from the API, or None if the sensor doesn't exist
        """
        try:
            name = self.sensors_by_id[sensor_id].name
            del self.sensors_by_name[name]
            del self.sensors_by_id[sensor_id]
            return self.request(
                "DELETE", "/api/" + self.username + "/sensors/" + str(sensor_id)
            )
        except KeyError:
            logger.debug(f"Unable to delete nonexistent sensor with ID {sensor_id}")
            return None

    # Groups of lights #####
    @property
    def groups(self) -> list[Group]:
        """Access groups as a list"""
        return [Group(self, int(groupid)) for groupid in self.get_group().keys()]

    def get_group_id_by_name(self, name: str) -> int | None:
        """Lookup a group id based on string name. Case-sensitive.

        Args:
            name: The name of the group to look up

        Returns:
            The group ID if found, otherwise None
        """
        groups = self.get_group()
        for group_id in groups:
            if name == groups[group_id]["name"]:
                return int(group_id)
        return None

    def get_group(
        self, group_id: int | str | None = None, parameter: str | None = None
    ) -> Any:
        """Gets state by group_id and parameter.

        Args:
            group_id: The ID of the group, or the name of the group, or None to get all groups
            parameter: The parameter to get, or None to get all parameters

        Returns:
            The requested parameter value, or a dict of all parameters if parameter is None,
            or None if the group could not be found
        """
        if isinstance(group_id, str) and not group_id.isdigit():
            group_id = self.get_group_id_by_name(group_id)
            if group_id is None:
                logger.error("Group name does not exist")
                return None

        if group_id is None:
            return self.request("GET", "/api/" + self.username + "/groups/")

        if parameter is None:
            return self.request(
                "GET", "/api/" + self.username + "/groups/" + str(group_id)
            )
        elif parameter in ("name", "lights"):
            return self.request(
                "GET", "/api/" + self.username + "/groups/" + str(group_id)
            )[parameter]
        elif parameter in ("any_on", "all_on"):
            return self.request(
                "GET", "/api/" + self.username + "/groups/" + str(group_id)
            )["state"][parameter]
        else:
            return self.request(
                "GET", "/api/" + self.username + "/groups/" + str(group_id)
            )["action"][parameter]

    def set_group(
        self,
        group_id: int | str | list[int | str],
        parameter: str | dict[str, Any],
        value: Any = None,
        transitiontime: int | None = None,
    ) -> list[Any]:
        """Change light settings for a group.

        Args:
            group_id: A single group ID/name or a list of group IDs/names
            parameter: Either a parameter name or a dict of parameters to set
            value: The value to set if parameter is a string
            transitiontime: Time for this transition to take place (in deciseconds)

        Returns:
            A list of responses from the API
        """
        data: dict[str, Any] = {}
        username = self.username

        if isinstance(parameter, dict):
            data = parameter
        elif parameter == "lights" and (
            isinstance(value, list) or isinstance(value, int)
        ):
            if isinstance(value, int):
                value = [value]

            if TYPE_CHECKING:
                value = cast(Iterable[int | str], value)

            data = {parameter: [str(x) for x in value]}
        else:
            data = {parameter: value}

        if transitiontime is not None:
            data["transitiontime"] = int(
                round(transitiontime)
            )  # must be int for request format

        group_id_array: list[int | str] = []
        if isinstance(group_id, int | str):
            group_id_array = [group_id]
        else:
            group_id_array = group_id

        result: list[Any] = []
        for group in group_id_array:
            logger.debug(str(data))
            if isinstance(group, str) and not group.isdigit():
                converted_group = self.get_group_id_by_name(group)
                if converted_group is None:
                    logger.error("Group name does not exist")
                    continue
            else:
                converted_group = group

            if parameter in ("name", "lights"):
                result.append(
                    self.request(
                        "PUT",
                        "/api/" + username + "/groups/" + str(converted_group),
                        data,
                    )
                )
            else:
                result.append(
                    self.request(
                        "PUT",
                        "/api/"
                        + username
                        + "/groups/"
                        + str(converted_group)
                        + "/action",
                        data,
                    )
                )

            if (
                result
                and isinstance(result[-1], list)
                and result[-1]
                and "error" in result[-1][0]
            ):
                logger.warning(
                    f"ERROR: {result[-1][0]['error']['description']} for group {group}"
                )

        logger.debug(result)
        return result

    def create_group(self, name: str, lights: list[int] | None = None) -> Any:
        """Create a group of lights

        Args:
            name: Name for this group of lights
            lights: List of lights to be in the group

        Returns:
            The response from the API
        """
        if lights is None:
            lights = []

        data = {"lights": [str(x) for x in lights], "name": name}
        return self.request("POST", "/api/" + self.username + "/groups/", data)

    def delete_group(self, group_id: int) -> Any:
        """Delete a group from the bridge.

        Args:
            group_id: The ID of the group to delete

        Returns:
            The response from the API
        """
        return self.request(
            "DELETE", "/api/" + self.username + "/groups/" + str(group_id)
        )

    # Scenes #####
    @property
    def scenes(self) -> list[Scene]:
        """Access scenes as a list"""
        return [Scene(k, **v) for k, v in self.get_scene().items()]

    def create_group_scene(self, name: str, group: str) -> Any:
        """Create a Group Scene

        Group scenes are based on the definition of groups and contain always all
        lights from the selected group. No other lights from other rooms can be
        added to a group scene and the group scene can not contain less lights
        as available in the selected group. If a group is extended with new lights,
        the new lights are added with default color to all group scenes based on
        the corresponding group. This app has no influence on this behavior, it
        was defined by Philips.

        Args:
            name: The name of the scene to be created
            group: The group id of where the scene will be added

        Returns:
            The response from the API
        """
        data = {"name": name, "group": group, "recycle": True, "type": "GroupScene"}
        return self.request("POST", "/api/" + self.username + "/scenes", data)

    def modify_scene(self, scene_id: str, data: dict[str, Any]) -> Any:
        """Modify a scene with the given data.

        Args:
            scene_id: The ID of the scene to modify
            data: Data to update in the scene

        Returns:
            The response from the API
        """
        return self.request(
            "PUT", "/api/" + self.username + "/scenes/" + scene_id, data
        )

    def get_scene(self) -> dict[str, Any]:
        """Get all scenes from the bridge.

        Returns:
            A dictionary of scenes
        """
        return self.request("GET", "/api/" + self.username + "/scenes")

    def activate_scene(
        self, group_id: int, scene_id: str, transition_time: int = 4
    ) -> Any:
        """Activate a scene for a given group.

        Args:
            group_id: The ID of the group
            scene_id: The ID of the scene to activate
            transition_time: Time for the transition to take place (in deciseconds)

        Returns:
            The response from the API
        """
        return self.request(
            "PUT",
            "/api/" + self.username + "/groups/" + str(group_id) + "/action",
            {"scene": scene_id, "transitiontime": transition_time},
        )

    def run_scene(
        self, group_name: str, scene_name: str, transition_time: int = 4
    ) -> bool:
        """Run a scene by group and scene name.

        As of 1.11 of the Hue API the scenes are accessible in the
        API. With the gen 2 of the official HUE app everything is
        organized by room groups.

        This provides a convenience way of activating scenes by group
        name and scene name. If we find exactly 1 group and 1 scene
        with the matching names, we run them.

        If we find more than one we run the first scene who has
        exactly the same lights defined as the group. This is far from
        perfect, but is convenient for setting lights symbolically (and
        can be improved later).

        Args:
            group_name: The name of the group
            scene_name: The name of the scene
            transition_time: The duration of the transition in deciseconds

        Returns:
            True if a scene was run, False otherwise
        """
        groups = [x for x in self.groups if x.name == group_name]
        scenes = [x for x in self.scenes if x.name == scene_name]

        if len(groups) != 1:
            logger.warning(f"run_scene: More than 1 group found by name {group_name}")
            return False

        group = groups[0]

        if len(scenes) == 0:
            logger.warning(f"run_scene: No scene found {scene_name}")
            return False

        if len(scenes) == 1:
            self.activate_scene(group.group_id, scenes[0].scene_id, transition_time)
            return True

        # otherwise, lets figure out if one of the named scenes uses
        # all the lights of the group
        group_lights = sorted([x.light_id for x in group.lights])
        for scene in scenes:
            if group_lights == scene.lights:
                self.activate_scene(group.group_id, scene.scene_id, transition_time)
                return True

        logger.warning(
            f"run_scene: did not find a scene: {scene_name} "
            f"that shared lights with group {group_name}"
        )
        return False

    def delete_scene(self, scene_id: str) -> Any:
        """Delete a scene from the bridge.

        Args:
            scene_id: The ID of the scene to delete

        Returns:
            The response from the API, or None if there was an error
        """
        try:
            return self.request(
                "DELETE", "/api/" + self.username + "/scenes/" + str(scene_id)
            )
        except Exception as e:
            logger.debug(f"Unable to delete scene with ID {scene_id}: {str(e)}")
            return None

    # Schedules #####
    def get_schedule(
        self, schedule_id: int | None = None, parameter: str | None = None
    ) -> Any:
        """Get schedules from the bridge.

        Args:
            schedule_id: The ID of the schedule, or None to get all schedules
            parameter: The parameter to get, or None to get all parameters

        Returns:
            The requested parameter value, or a dict of all parameters if parameter is None
        """
        if schedule_id is None:
            return self.request("GET", "/api/" + self.username + "/schedules")
        if parameter is None:
            return self.request(
                "GET", "/api/" + self.username + "/schedules/" + str(schedule_id)
            )
        return self.request(
            "GET", "/api/" + self.username + "/schedules/" + str(schedule_id)
        )[parameter]

    def create_schedule(
        self,
        name: str,
        time: str,
        light_id: int,
        data: dict[str, Any],
        description: str = " ",
    ) -> Any:
        """Create a schedule to control lights at a specific time.

        Args:
            name: Name for the schedule
            time: Time for the schedule in the format specified by the Hue API
            light_id: The ID of the light to control
            data: Data containing the light state to set
            description: Optional description for the schedule

        Returns:
            The response from the API
        """
        schedule: dict[str, Any] = {
            "name": name,
            "localtime": time,
            "description": description,
            "command": {
                "method": "PUT",
                "address": (
                    "/api/" + self.username + "/lights/" + str(light_id) + "/state"
                ),
                "body": data,
            },
        }
        return self.request("POST", "/api/" + self.username + "/schedules", schedule)

    def set_schedule_attributes(
        self, schedule_id: int, attributes: dict[str, Any]
    ) -> Any:
        """Update schedule attributes.

        Args:
            schedule_id: The ID of the schedule
            attributes: Dictionary with attributes and their new values

        Returns:
            The response from the API
        """
        return self.request(
            "PUT",
            "/api/" + self.username + "/schedules/" + str(schedule_id),
            data=attributes,
        )

    def create_group_schedule(
        self,
        name: str,
        time: str,
        group_id: int,
        data: dict[str, Any],
        description: str = " ",
    ) -> Any:
        """Create a schedule to control a group at a specific time.

        Args:
            name: Name for the schedule
            time: Time for the schedule in the format specified by the Hue API
            group_id: The ID of the group to control
            data: Data containing the group state to set
            description: Optional description for the schedule

        Returns:
            The response from the API
        """
        schedule = {
            "name": name,
            "localtime": time,
            "description": description,
            "command": {
                "method": "PUT",
                "address": (
                    "/api/" + self.username + "/groups/" + str(group_id) + "/action"
                ),
                "body": data,
            },
        }
        return self.request("POST", "/api/" + self.username + "/schedules", schedule)

    def delete_schedule(self, schedule_id: int) -> Any:
        """Delete a schedule from the bridge.

        Args:
            schedule_id: The ID of the schedule to delete

        Returns:
            The response from the API
        """
        return self.request(
            "DELETE", "/api/" + self.username + "/schedules/" + str(schedule_id)
        )

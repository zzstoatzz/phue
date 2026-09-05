"""Exceptions for Philips Hue requests."""

from typing import Any


class PhueException(Exception):
    """Base exception for all Philips Hue related errors."""

    def __init__(self, id: int, message: str):
        self.id = id
        self.message = message
        super().__init__(f"Error {id}: {message}")


class PhueRegistrationException(PhueException):
    """Exception raised when registration with the bridge fails."""

    pass


class PhueRequestTimeout(PhueException):
    """Exception raised when a request to the bridge times out."""

    pass


class PhueAPIError(PhueException):
    """A Hue error response, possibly containing successful property updates too."""

    def __init__(self, id: int, message: str, response: list[dict[str, Any]]):
        super().__init__(id, message)
        self.response = response

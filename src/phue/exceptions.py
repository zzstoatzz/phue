"""Exceptions for the phue_modern library."""


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

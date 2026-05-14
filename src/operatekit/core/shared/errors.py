class OperateKitError(Exception):
    """Base exception for OperateKit."""


class ConfigurationError(OperateKitError):
    """Raised when SDK configuration is invalid."""


class DriverUnavailableError(OperateKitError):
    """Raised when an optional platform dependency is missing or unavailable."""


class StepExecutionError(OperateKitError):
    """Raised when a workflow step cannot complete."""

    def __init__(self, message: str, *, step_result: object | None = None):
        super().__init__(message)
        self.step_result = step_result


class ObservationTimeoutError(OperateKitError):
    """Raised when an observation cannot be found in time."""


class LocatorError(OperateKitError):
    """Raised when a locator cannot be translated for a driver."""

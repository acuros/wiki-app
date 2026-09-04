class ApplicationError(Exception):
    """Base class for errors safe to classify at the HTTP boundary."""


class InvalidThreadQuery(ApplicationError):
    pass


class InvalidMessage(ApplicationError):
    pass


class ThreadNotFound(ApplicationError):
    pass


class ThreadBusy(ApplicationError):
    pass


class DependencyUnavailable(ApplicationError):
    pass


class DependencyTimeout(ApplicationError):
    pass


class DependencyRateLimited(ApplicationError):
    pass


class DependencyProtocolError(ApplicationError):
    pass

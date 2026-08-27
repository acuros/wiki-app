class ApplicationError(Exception):
    """Base class for errors safe to classify at the HTTP boundary."""


class InvalidThreadQuery(ApplicationError):
    pass


class ThreadNotFound(ApplicationError):
    pass


class DependencyUnavailable(ApplicationError):
    pass


class DependencyTimeout(ApplicationError):
    pass


class DependencyProtocolError(ApplicationError):
    pass

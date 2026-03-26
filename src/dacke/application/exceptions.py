class ApplicationError(Exception):
    """Base class for all application-specific errors."""

    pass


class UseCaseError(ApplicationError):
    """Base class for all use case-specific errors."""

    pass

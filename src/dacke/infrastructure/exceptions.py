class InfrastructureError(Exception):
    """Base class for all infrastructure-specific errors."""

    pass


class DatabaseError(InfrastructureError):
    """Base class for all database-specific errors."""

    pass


class DatabaseConnectionError(DatabaseError):
    """Exception raised when a database connection fails."""

    pass


class DatabaseOperationError(DatabaseError):
    """Exception raised when a database operation fails."""

    pass

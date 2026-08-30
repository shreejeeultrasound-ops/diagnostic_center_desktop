"""Application-level exceptions.

UI code catches these and shows a friendly message; raw stack traces are
never shown to the end user (see app.logging_config for where the
technical detail is logged instead).
"""


class AppError(Exception):
    """Base class for all expected/handled application errors."""


class ValidationError(AppError):
    """Raised when user-supplied data fails a business rule."""


class NotFoundError(AppError):
    """Raised when a referenced record does not exist."""


class DatabaseUnavailableError(AppError):
    """Raised when the database file cannot be opened or is corrupt."""


class BackupError(AppError):
    """Raised when a backup operation fails."""


class RestoreError(AppError):
    """Raised when a restore operation fails."""


class ReportGenerationError(AppError):
    """Raised when PDF/print generation fails."""

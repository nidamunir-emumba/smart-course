"""Framework-agnostic domain exceptions.

Services raise these; the API layer maps them to HTTP responses (see app/main.py).
Keeping them free of FastAPI/HTTP concerns lets the same services be reused by
workers and workflows later.
"""


class DomainError(Exception):
    """Base class for expected business-rule violations. `status_code` guides HTTP mapping."""

    status_code: int = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    status_code = 404


class ConflictError(DomainError):
    status_code = 409


class DuplicateEnrollmentError(ConflictError):
    pass


class EnrollmentLimitReachedError(ConflictError):
    pass


class PrerequisitesNotMetError(DomainError):
    status_code = 422


class CourseNotPublishedError(DomainError):
    status_code = 409

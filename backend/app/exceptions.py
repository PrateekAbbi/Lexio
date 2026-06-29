"""Application-level exceptions mapped to HTTP responses at the API boundary."""


class ConfigurationError(RuntimeError):
    """Raised when a required runtime dependency is not configured."""


class ExternalServiceError(RuntimeError):
    """Raised when an upstream API or database call fails."""


class EmptyDocumentError(ValueError):
    """Raised when a PDF contains no extractable text."""


class UnsupportedDocumentError(ValueError):
    """Raised when a request contains a document format the backend does not support."""


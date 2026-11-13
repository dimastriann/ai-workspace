"""Application-level errors that routers map to HTTP responses."""


class UploadError(Exception):
    """Base class for upload validation failures."""


class UnsupportedFileTypeError(UploadError):
    """The uploaded file type is not allowed."""


class FileTooLargeError(UploadError):
    """The uploaded file exceeds the configured size limit."""


class WorkspaceNotFoundError(UploadError):
    """The target workspace does not exist."""

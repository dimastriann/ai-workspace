"""Application-level errors that routers map to HTTP responses."""


class UploadError(Exception):
    """Base class for upload validation failures."""


class UnsupportedFileTypeError(UploadError):
    """The uploaded file type is not allowed."""


class FileTooLargeError(UploadError):
    """The uploaded file exceeds the configured size limit."""


class WorkspaceNotFoundError(UploadError):
    """The target workspace does not exist."""


class DocumentNotFoundError(Exception):
    """The requested document does not exist."""


class FolderNotFoundError(Exception):
    """The requested folder does not exist."""


class FolderConflictError(Exception):
    """A folder operation conflicts with existing structure or names."""

"""
Upload validation service.

Phase 1 responsibility: confirm the uploaded file is a supported type
and within size limits before it's accepted into the pipeline. Actual
image/PDF processing is implemented in Phase 2.
"""
import logging

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.errors import FileTooLargeError, InvalidFileError

logger = logging.getLogger(__name__)

SUPPORTED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
}


class UploadValidationService:
    """Validates incoming drawing uploads before they enter the pipeline."""

    def __init__(self) -> None:
        self._settings = get_settings()

    async def validate(self, file: UploadFile) -> bytes:
        """
        Validate content type and size, returning the raw bytes read.

        Raises:
            InvalidFileError: unsupported content type or empty file.
            FileTooLargeError: file exceeds MAX_UPLOAD_SIZE_MB.
        """
        if file.content_type not in SUPPORTED_CONTENT_TYPES:
            logger.warning("Rejected upload with unsupported type: %s", file.content_type)
            raise InvalidFileError(
                f"Unsupported file type '{file.content_type}'. "
                f"Supported types: {', '.join(sorted(SUPPORTED_CONTENT_TYPES))}."
            )

        contents = await file.read()

        if len(contents) == 0:
            raise InvalidFileError("Uploaded file is empty.")

        max_bytes = self._settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(contents) > max_bytes:
            raise FileTooLargeError(
                f"File exceeds the {self._settings.MAX_UPLOAD_SIZE_MB}MB limit."
            )

        return contents

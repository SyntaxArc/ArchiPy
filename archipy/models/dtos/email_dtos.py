import mimetypes
from typing import BinaryIO, Self

from pydantic import Field, model_validator

from archipy.models.dtos.base_dtos import BaseDTO
from archipy.models.types.email_types import EmailAttachmentDispositionType, EmailAttachmentType


class EmailAttachmentDTO(BaseDTO):
    """Pydantic model for email attachments."""

    content: str | bytes | BinaryIO
    filename: str
    content_type: str | None = Field(default=None)
    content_disposition: EmailAttachmentDispositionType = Field(default=EmailAttachmentDispositionType.ATTACHMENT)
    content_id: str | None = Field(default=None)
    attachment_type: EmailAttachmentType
    max_size: int

    @model_validator(mode="after")
    def validate_attachment(self) -> Self:
        """Validate and normalize attachment fields.

        This validator performs three operations:
        1. Sets content_type based on filename extension if not provided
        2. Validates that attachment size does not exceed maximum allowed size
        3. Ensures content_id is properly formatted with angle brackets

        Returns:
            The validated model instance

        Raises:
            ValueError: If attachment size exceeds maximum allowed size
        """
        # Set content type from filename if not provided
        if self.content_type is None:
            content_type, _ = mimetypes.guess_type(self.filename)
            self.content_type = content_type or "application/octet-stream"

        # Validate attachment size
        content = self.content
        if isinstance(content, str | bytes):
            content_size = len(content)
            if content_size > self.max_size:
                error_msg = f"Attachment size exceeds maximum allowed size of {self.max_size} bytes"
                raise ValueError(error_msg)

        # Ensure content_id has angle brackets
        if self.content_id and not self.content_id.startswith("<"):
            self.content_id = f"<{self.content_id}>"

        return self

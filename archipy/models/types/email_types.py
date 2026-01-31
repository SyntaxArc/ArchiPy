from enum import StrEnum


class EmailAttachmentType(StrEnum):
    """Enum representing different types of email attachments.

    This enum defines the types of attachments that can be included in an email,
    such as files, base64-encoded data, URLs, or binary data.

    Attributes:
        FILE (str): Represents a file attachment.
        BASE64 (str): Represents a base64-encoded attachment.
        URL (str): Represents an attachment referenced by a URL.
        BINARY (str): Represents raw binary data as an attachment.
    """

    FILE = "file"
    BASE64 = "base64"
    URL = "url"
    BINARY = "binary"


class EmailAttachmentDispositionType(StrEnum):
    """Enum representing attachment disposition types.

    This enum defines how an email attachment should be displayed or handled,
    such as being treated as a downloadable attachment or displayed inline.

    Attributes:
        ATTACHMENT (str): Represents an attachment that should be downloaded.
        INLINE (str): Represents an attachment that should be displayed inline.
    """

    ATTACHMENT = "ATTACHMENT"
    INLINE = "INLINE"

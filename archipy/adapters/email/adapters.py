import base64
import logging
import os
import smtplib
from datetime import datetime
from email import encoders
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from queue import Queue
from typing import BinaryIO, override

import requests
from jinja2 import Template
from pydantic import EmailStr, HttpUrl

from archipy.adapters.email.ports import EmailPort
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import EmailConfig
from archipy.helpers.utils.base_utils import BaseUtils
from archipy.models.dtos.email_dtos import EmailAttachmentDTO
from archipy.models.errors import InvalidArgumentError
from archipy.models.types.email_types import EmailAttachmentDispositionType, EmailAttachmentType

logger = logging.getLogger(__name__)


class EmailConnectionManager:
    """Manages SMTP connections with connection pooling and timeout handling."""

    def __init__(self, config: EmailConfig) -> None:
        self.config = config
        self.smtp_connection: smtplib.SMTP | None = None
        self.last_used: datetime | None = None

    def connect(self) -> None:
        """Establish SMTP connection with authentication."""
        if not self.config.SMTP_SERVER:
            raise InvalidArgumentError("SMTP_SERVER is required for email connection")

        try:
            self.smtp_connection = smtplib.SMTP(
                self.config.SMTP_SERVER,
                self.config.SMTP_PORT,
                timeout=self.config.CONNECTION_TIMEOUT,
            )
            self.smtp_connection.starttls()
            if self.config.USERNAME and self.config.PASSWORD:
                self.smtp_connection.login(self.config.USERNAME, self.config.PASSWORD)
            self.last_used = datetime.now()
        except Exception as e:
            BaseUtils.capture_exception(e)
            self.smtp_connection = None

    def disconnect(self) -> None:
        """Close SMTP connection safely."""
        try:
            if self.smtp_connection:
                self.smtp_connection.quit()
                self.smtp_connection = None
        except Exception as e:
            BaseUtils.capture_exception(e)
        finally:
            self.smtp_connection = None

    def refresh_if_needed(self) -> None:
        """Refresh connection if needed based on timeout."""
        if not self.smtp_connection or not self.last_used:
            self.connect()
            return

        time_diff = (datetime.now() - self.last_used).total_seconds()
        if time_diff > 300:  # Refresh after 5 minutes
            self.disconnect()
            self.connect()


class EmailConnectionPool:
    """Connection pool for managing multiple SMTP connections."""

    def __init__(self, config: EmailConfig) -> None:
        self.config = config
        self.pool: Queue[EmailConnectionManager] = Queue(maxsize=config.POOL_SIZE)
        self._initialize_pool()

    def _initialize_pool(self) -> None:
        for _ in range(self.config.POOL_SIZE):
            connection = EmailConnectionManager(self.config)
            self.pool.put(connection)

    def get_connection(self) -> EmailConnectionManager:
        """Get a connection from the pool."""
        connection = self.pool.get()
        connection.refresh_if_needed()
        return connection

    def return_connection(self, connection: EmailConnectionManager) -> None:
        """Return a connection to the pool."""
        connection.last_used = datetime.now()
        self.pool.put(connection)


class AttachmentHandler:
    """Enhanced attachment handler with better type safety and validation."""

    @staticmethod
    def create_attachment(
        source: str | bytes | BinaryIO | HttpUrl,
        filename: str,
        attachment_type: EmailAttachmentType,
        content_type: str | None = None,
        content_disposition: EmailAttachmentDispositionType = EmailAttachmentDispositionType.ATTACHMENT,
        content_id: str | None = None,
        max_size: int | None = None,
    ) -> EmailAttachmentDTO:
        """Create an attachment with validation."""
        if max_size is None:
            max_size = BaseConfig.global_config().EMAIL.ATTACHMENT_MAX_SIZE
        try:
            processed_content = AttachmentHandler._process_source(source, attachment_type)

            return EmailAttachmentDTO(
                content=processed_content,
                filename=filename,
                content_type=content_type,
                content_disposition=content_disposition,
                content_id=content_id,
                attachment_type=attachment_type,
                max_size=max_size,
            )
        except Exception as exception:
            raise InvalidArgumentError(f"Failed to create attachment: {exception!s}") from exception

    @staticmethod
    def _process_source(source: str | bytes | BinaryIO | HttpUrl, attachment_type: EmailAttachmentType) -> bytes:
        """Process different types of attachment sources."""
        if attachment_type == EmailAttachmentType.FILE:
            if isinstance(source, str):
                return Path(source).read_bytes()
            if isinstance(source, os.PathLike):
                return Path(os.fspath(source)).read_bytes()
            raise ValueError(f"File attachment type requires string path, got {type(source)}")
        elif attachment_type == EmailAttachmentType.BASE64:
            if isinstance(source, str | bytes):
                return base64.b64decode(source)
            raise ValueError(f"Base64 attachment type requires str or bytes, got {type(source)}")
        elif attachment_type == EmailAttachmentType.URL:
            if isinstance(source, str | HttpUrl):
                response = requests.get(str(source), timeout=30)
                response.raise_for_status()
                return bytes(response.content)
            raise ValueError(f"URL attachment type requires str or HttpUrl, got {type(source)}")
        elif attachment_type == EmailAttachmentType.BINARY:
            if isinstance(source, bytes):
                return source
            if isinstance(source, BinaryIO):
                return source.read()
            if hasattr(source, "read"):
                read_method = source.read
                if callable(read_method):
                    result = read_method()
                    if isinstance(result, bytes):
                        return result
                    if isinstance(result, str):
                        return result.encode("utf-8")
                    raise ValueError(f"read() method returned unexpected type: {type(result)}")
            raise ValueError(f"Invalid binary source type: {type(source)}")
        raise ValueError(f"Unsupported attachment type: {attachment_type}")

    @staticmethod
    def process_attachment(msg: MIMEMultipart, attachment: EmailAttachmentDTO) -> None:
        """Process and attach the attachment to the email message."""
        content = AttachmentHandler._get_content(attachment)
        part = AttachmentHandler._create_mime_part(content, attachment)

        # Add headers
        part.add_header("Content-Disposition", attachment.content_disposition.value, filename=attachment.filename)

        if attachment.content_id:
            part.add_header("Content-ID", attachment.content_id)

        msg.attach(part)

    @staticmethod
    def _get_content(attachment: EmailAttachmentDTO) -> bytes:
        """Get content as bytes from attachment."""
        if isinstance(attachment.content, str | bytes):
            return attachment.content if isinstance(attachment.content, bytes) else attachment.content.encode()
        return attachment.content.read()

    @staticmethod
    def _create_mime_part(
        content: bytes,
        attachment: EmailAttachmentDTO,
    ) -> MIMEText | MIMEImage | MIMEAudio | MIMEBase:
        """Create appropriate MIME part based on content type."""
        if not attachment.content_type:
            raise ValueError("Content type is required for attachment")
        main_type, sub_type = attachment.content_type.split("/", 1)

        if main_type == "text":
            return MIMEText(content.decode(), sub_type)
        if main_type == "image":
            return MIMEImage(content, _subtype=sub_type)
        if main_type == "audio":
            return MIMEAudio(content, _subtype=sub_type)
        part = MIMEBase(main_type, sub_type)
        part.set_payload(content)
        encoders.encode_base64(part)
        return part


class EmailAdapter(EmailPort):
    """Email adapter implementing EmailPort for sending emails with SMTP."""

    def __init__(self, config: EmailConfig | None = None) -> None:
        self.config = config or BaseConfig.global_config().EMAIL
        self.connection_pool = EmailConnectionPool(self.config)

    @override
    def send_email(
        self,
        to_email: EmailStr | list[EmailStr],
        subject: str,
        body: str,
        cc: EmailStr | list[EmailStr] | None = None,
        bcc: EmailStr | list[EmailStr] | None = None,
        attachments: list[str | EmailAttachmentDTO] | None = None,
        html: bool = False,
        template: str | None = None,
        template_vars: dict | None = None,
    ) -> None:
        """Send email with advanced features and connection pooling."""
        connection: EmailConnectionManager | None = None
        try:
            connection = self.connection_pool.get_connection()
            msg = self._create_message(
                to_email=to_email,
                subject=subject,
                body=body,
                cc=cc,
                bcc=bcc,
                attachments=attachments,
                html=html,
                template=template,
                template_vars=template_vars,
            )

            recipients = self._get_all_recipients(to_email, cc, bcc)

            for attempt in range(self.config.MAX_RETRIES):
                try:
                    if connection.smtp_connection:
                        connection.smtp_connection.send_message(msg, to_addrs=recipients)
                        logger.debug(f"Email sent successfully to {to_email}")
                        return
                    else:
                        connection.connect()
                except Exception as e:
                    if attempt == self.config.MAX_RETRIES - 1:
                        BaseUtils.capture_exception(e)
                    connection.connect()  # Retry with fresh connection

        except Exception as e:
            BaseUtils.capture_exception(e)
        finally:
            if connection:
                self.connection_pool.return_connection(connection)

    def _create_message(
        self,
        to_email: EmailStr | list[EmailStr],
        subject: str,
        body: str,
        cc: EmailStr | list[EmailStr] | None = None,
        bcc: EmailStr | list[EmailStr] | None = None,
        attachments: list[str | EmailAttachmentDTO] | None = None,
        html: bool = False,
        template: str | None = None,
        template_vars: dict | None = None,
    ) -> MIMEMultipart:
        msg = MIMEMultipart()
        msg["From"] = self.config.USERNAME or "no-reply@example.com"
        msg["To"] = to_email if isinstance(to_email, str) else ", ".join(to_email)
        msg["Subject"] = subject

        if cc:
            msg["Cc"] = cc if isinstance(cc, str) else ", ".join(cc)
        if bcc:
            msg["Bcc"] = bcc if isinstance(bcc, str) else ", ".join(bcc)

        if template:
            body = Template(template).render(**(template_vars or {}))

        msg.attach(MIMEText(body, "html" if html else "plain"))

        if attachments:
            for attachment in attachments:
                if isinstance(attachment, str):
                    # Treat as file path
                    attachment_obj = AttachmentHandler.create_attachment(
                        source=attachment,
                        filename=Path(attachment).name,
                        attachment_type=EmailAttachmentType.FILE,
                    )
                else:
                    attachment_obj = attachment
                AttachmentHandler.process_attachment(msg, attachment_obj)

        return msg

    @staticmethod
    def _get_all_recipients(
        to_email: EmailStr | list[EmailStr],
        cc: EmailStr | list[EmailStr] | None,
        bcc: EmailStr | list[EmailStr] | None,
    ) -> list[str]:
        """Get list of all recipients."""
        recipients = []

        # Add primary recipients
        if isinstance(to_email, str):
            recipients.append(to_email)
        else:
            recipients.extend(to_email)

        # Add CC recipients
        if cc:
            if isinstance(cc, str):
                recipients.append(cc)
            else:
                recipients.extend(cc)

        # Add BCC recipients
        if bcc:
            if isinstance(bcc, str):
                recipients.append(bcc)
            else:
                recipients.extend(bcc)

        return recipients

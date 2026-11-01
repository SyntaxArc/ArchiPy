"""Email adapter implementations for ArchiPy."""

from __future__ import annotations

import base64
import logging
import os
import smtplib
import ssl
import warnings
from email import encoders
from email.errors import MessageError
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from queue import Empty, Queue
from typing import TYPE_CHECKING, Any, BinaryIO, cast, override
from urllib.parse import urlparse

import httpx2
from pydantic import EmailStr, HttpUrl, ValidationError

from archipy.adapters.email.ports import EmailPort
from archipy.configs.base_config import BaseConfig
from archipy.helpers.decorators.tracing import trace_span
from archipy.helpers.utils.base_utils import BaseUtils
from archipy.helpers.utils.datetime_utils import DatetimeUtils
from archipy.models.dtos.email_dtos import EmailAttachmentDTO
from archipy.models.errors import ConfigurationError, InvalidArgumentError, UnavailableError
from archipy.models.types.email_types import EmailAttachmentDispositionType, EmailAttachmentType

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from opentelemetry.trace import SpanKind

    from archipy.configs.config_template import EmailConfig

logger = logging.getLogger(__name__)

_PERMANENT_FAILURE_CODE = 500


def _smtp_span_kind() -> SpanKind | None:
    """Return ``SpanKind.CLIENT`` for outgoing SMTP spans, or None when OpenTelemetry is not installed."""
    try:
        from opentelemetry.trace import SpanKind
    except ImportError:
        return None
    return SpanKind.CLIENT


def _annotate_current_span(attributes: dict[str, Any]) -> None:
    """Set attributes on the active span; do nothing when tracing is off or OpenTelemetry is missing.

    Only low-cardinality, non-sensitive values may be passed: never credentials, addresses, subjects or bodies.
    """
    try:
        from opentelemetry import trace
    except ImportError:
        return
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attributes(attributes)


class EmailConnectionManager:
    """Manages SMTP connections with connection pooling and timeout handling."""

    def __init__(self, config: EmailConfig) -> None:
        """Initialize EmailConnectionManager.

        Raises:
            ConfigurationError: If only one of ``USERNAME`` and ``PASSWORD`` is set while ``TLS_MODE`` is not ``auto``.
        """
        self.config = config
        self.smtp_connection: smtplib.SMTP | None = None
        self.last_used: datetime | None = None
        self.last_error: Exception | None = None
        self._validate_security()

    def _validate_security(self) -> None:
        """Check the TLS and credential settings; the legacy ``auto`` mode only warns."""
        half_set = bool(self.config.USERNAME) != bool(self.config.PASSWORD)
        if self.config.TLS_MODE == "auto":
            warnings.warn(
                "EMAIL.TLS_MODE='auto' is deprecated: STARTTLS is opportunistic, the certificate is not verified "
                "and a failed upgrade falls back to clear text. Set TLS_MODE to 'starttls' or 'implicit'.",
                DeprecationWarning,
                stacklevel=3,
            )
            if half_set:
                warnings.warn(
                    "EMAIL.USERNAME and EMAIL.PASSWORD must be set together; login is skipped. "
                    "This will be an error in a future release.",
                    DeprecationWarning,
                    stacklevel=3,
                )
        elif half_set:
            raise ConfigurationError(
                operation="email_credentials",
                reason="USERNAME and PASSWORD must be set together",
            )
        if self.config.TLS_MODE == "none" and self.config.USERNAME and self.config.PASSWORD:
            warnings.warn(
                "EMAIL.TLS_MODE='none' sends USERNAME and PASSWORD in clear text. "
                "Set TLS_MODE to 'starttls' or 'implicit'; clear-text login will be rejected in a future release.",
                DeprecationWarning,
                stacklevel=3,
            )
        if self.config.TLS_MODE in ("starttls", "implicit") and not self.config.TLS_VERIFY:
            warnings.warn(
                "EMAIL.TLS_VERIFY=False disables certificate and host name verification, which exposes the "
                "session and credentials to interception. Use TLS_CA_FILE for a private CA; "
                "TLS_VERIFY=False will be rejected in a future release.",
                DeprecationWarning,
                stacklevel=3,
            )

    def _build_ssl_context(self) -> ssl.SSLContext:
        """Build the TLS context from ``TLS_CA_FILE`` and ``TLS_VERIFY``."""
        context = ssl.create_default_context(cafile=self.config.TLS_CA_FILE)
        if not self.config.TLS_VERIFY:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        return context

    def _open_session(self) -> tuple[smtplib.SMTP, str]:
        """Open the SMTP session for ``TLS_MODE`` and return it with the TLS mode actually in use."""
        mode = self.config.TLS_MODE
        source_address = (self.config.SOURCE_ADDRESS, self.config.SOURCE_PORT) if self.config.SOURCE_ADDRESS else None
        common: dict[str, Any] = {
            "local_hostname": self.config.LOCAL_HOSTNAME,
            "timeout": self.config.CONNECTION_TIMEOUT,
            "source_address": source_address,
        }
        server = cast("str", self.config.SMTP_SERVER)
        if mode == "implicit":
            session: smtplib.SMTP = smtplib.SMTP_SSL(
                server,
                self.config.SMTP_PORT,
                context=self._build_ssl_context(),
                **common,
            )
            session.ehlo()
            return session, "implicit"
        session = smtplib.SMTP(server, self.config.SMTP_PORT, **common)
        try:
            tls_mode = self._negotiate_tls(session)
        except BaseException:
            session.close()
            raise
        return session, tls_mode

    def _negotiate_tls(self, session: smtplib.SMTP) -> str:
        """Greet the server and upgrade with STARTTLS as ``TLS_MODE`` demands; return the TLS mode in use."""
        mode = self.config.TLS_MODE
        session.ehlo()
        offered = session.has_extn("starttls")
        if mode == "starttls" and not offered:
            message = "STARTTLS is required but the server does not offer it"
            raise smtplib.SMTPNotSupportedError(message)
        if mode == "none" or (mode == "auto" and not offered):
            return "none"
        session.starttls(context=self._build_ssl_context() if mode == "starttls" else None)
        session.ehlo()
        return "starttls"

    def connect(self) -> None:
        """Establish the SMTP connection with the configured transport security and authentication.

        ``TLS_MODE`` ``starttls`` fails when the server does not offer STARTTLS or the upgrade fails, and
        ``implicit`` opens a TLS connection from the start; neither falls back to clear text.
        Failures are captured and leave ``smtp_connection`` as ``None``; the cause is kept in ``last_error``.

        Raises:
            InvalidArgumentError: If no SMTP server is configured.
        """
        if not self.config.SMTP_SERVER:
            raise InvalidArgumentError(argument_name="SMTP_SERVER")

        try:
            session, tls_mode = self._open_session()
            try:
                _annotate_current_span({"email.tls_mode": tls_mode})
                if self.config.USERNAME and self.config.PASSWORD:
                    if tls_mode == "none":
                        logger.warning("Logging in to the SMTP server without TLS: credentials are sent in clear text")
                    session.login(self.config.USERNAME, self.config.PASSWORD)
            except BaseException:
                session.close()
                raise
            self.smtp_connection = session
            self.last_used = DatetimeUtils.get_datetime_now()
            self.last_error = None
        except (smtplib.SMTPException, OSError, TimeoutError) as e:
            BaseUtils.capture_exception(e)
            self.smtp_connection = None
            self.last_error = e

    def disconnect(self) -> None:
        """Close SMTP connection safely."""
        try:
            if self.smtp_connection:
                self.smtp_connection.quit()
                self.smtp_connection = None
        except (smtplib.SMTPException, OSError, TimeoutError) as e:
            BaseUtils.capture_exception(e)
        finally:
            self.smtp_connection = None

    def refresh_if_needed(self) -> None:
        """Refresh connection if needed based on timeout."""
        if not self.smtp_connection or not self.last_used:
            self.connect()
            return

        time_diff = (DatetimeUtils.get_datetime_now() - self.last_used).total_seconds()
        if time_diff > self.config.CONNECTION_REFRESH_SECONDS:
            self.disconnect()
            self.connect()


class EmailConnectionPool:
    """Connection pool for managing multiple SMTP connections."""

    def __init__(self, config: EmailConfig) -> None:
        """Initialize EmailConnectionPool."""
        self.config = config
        self.pool: Queue[EmailConnectionManager] = Queue(maxsize=config.POOL_SIZE)
        self._initialize_pool()

    def _initialize_pool(self) -> None:
        for _ in range(self.config.POOL_SIZE):
            connection = EmailConnectionManager(self.config)
            self.pool.put(connection)

    def get_connection(self) -> EmailConnectionManager:
        """Get a connection from the pool.

        Waits at most ``CONNECTION_TIMEOUT`` seconds for a free slot. The slot goes back to the pool when
        refreshing the connection raises.

        Raises:
            UnavailableError: If no slot becomes free within ``CONNECTION_TIMEOUT`` seconds.
        """
        try:
            connection = self.pool.get(timeout=self.config.CONNECTION_TIMEOUT)
        except Empty as exception:
            raise UnavailableError(resource_type="SMTP") from exception
        try:
            connection.refresh_if_needed()
        except BaseException:
            self.pool.put(connection)
            raise
        return connection

    def return_connection(self, connection: EmailConnectionManager) -> None:
        """Return a connection to the pool."""
        connection.last_used = DatetimeUtils.get_datetime_now()
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
        """Create an attachment with validation.

        Args:
            source: Attachment content, file path, base64 string, URL or binary stream.
            filename: Name shown to the recipient.
            attachment_type: How ``source`` must be interpreted.
            content_type: Optional MIME type of the attachment.
            content_disposition: Whether the attachment is inline or a regular attachment.
            content_id: Optional Content-ID for inline attachments.
            max_size: Maximum size in bytes; defaults to the configured ``ATTACHMENT_MAX_SIZE``.

        Returns:
            EmailAttachmentDTO: The validated attachment.

        Raises:
            InvalidArgumentError: If the source cannot be read or the attachment fails validation
                (for example it exceeds the maximum size).
        """
        if max_size is None:
            max_size = BaseConfig.global_config().EMAIL.ATTACHMENT_MAX_SIZE
        try:
            processed_content = AttachmentHandler._process_source(source, attachment_type, max_size)

            return EmailAttachmentDTO(
                content=processed_content,
                filename=filename,
                content_type=content_type,
                content_disposition=content_disposition,
                content_id=content_id,
                attachment_type=attachment_type,
                max_size=max_size,
            )
        except (smtplib.SMTPException, OSError, TimeoutError, httpx2.HTTPError) as exception:
            raise InvalidArgumentError(
                argument_name="attachment",
                additional_data={"reason": "create_failed", "detail": str(exception)},
            ) from exception
        except ValidationError as exception:
            raise InvalidArgumentError(
                argument_name="attachment",
                additional_data={"reason": "validation_failed", "detail": str(exception)},
            ) from exception

    @staticmethod
    def _process_file_source(source: str | bytes | BinaryIO | HttpUrl) -> bytes:
        """Read bytes from a filesystem path attachment source."""
        if isinstance(source, str):
            return Path(source).read_bytes()
        if isinstance(source, os.PathLike):
            path_str: str = os.fspath(source)
            return Path(path_str).read_bytes()
        raise InvalidArgumentError(
            argument_name="source",
            additional_data={"attachment_type": "file", "got": type(source).__name__},
        )

    @staticmethod
    def _process_base64_source(source: str | bytes | BinaryIO | HttpUrl) -> bytes:
        """Decode a base64 attachment source."""
        if isinstance(source, str | bytes):
            return base64.b64decode(source)
        raise InvalidArgumentError(
            argument_name="source",
            additional_data={"attachment_type": "base64", "got": type(source).__name__},
        )

    @staticmethod
    @trace_span(name="email.fetch_attachment_url")
    def _process_url_source(source: str | bytes | BinaryIO | HttpUrl, max_size: int | None = None) -> bytes:
        """Fetch bytes from a URL attachment source.

        Only ``http`` and ``https`` URLs are fetched, on a host allowed by ``ATTACHMENT_URL_ALLOWED_HOSTS`` when
        set. The body is streamed and the download stops once it exceeds ``max_size``.
        """
        if not isinstance(source, str | HttpUrl):
            raise InvalidArgumentError(
                argument_name="source",
                additional_data={"attachment_type": "url", "got": type(source).__name__},
            )
        config = BaseConfig.global_config().EMAIL
        url = str(source)
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise InvalidArgumentError(argument_name="source", additional_data={"reason": "unsupported_url_scheme"})
        allowed_hosts = config.ATTACHMENT_URL_ALLOWED_HOSTS
        if allowed_hosts is not None and parsed.hostname not in allowed_hosts:
            raise InvalidArgumentError(argument_name="source", additional_data={"reason": "url_host_not_allowed"})
        limit = max_size if max_size is not None else config.ATTACHMENT_MAX_SIZE
        content = bytearray()
        with httpx2.stream("GET", url, timeout=config.ATTACHMENT_URL_TIMEOUT) as response:
            response.raise_for_status()
            for chunk in response.iter_bytes():
                content.extend(chunk)
                if len(content) > limit:
                    raise InvalidArgumentError(
                        argument_name="attachment",
                        additional_data={"reason": "url_content_too_large", "max_size": limit},
                    )
        return bytes(content)

    @staticmethod
    def _read_binary_content(source: object) -> bytes:
        """Read bytes from a binary-like object with a ``read`` method."""
        if isinstance(source, bytes):
            return source
        if isinstance(source, BinaryIO):
            return source.read()
        read = getattr(source, "read", None)
        if callable(read):
            result = cast("Callable[[], object]", read)()
            if isinstance(result, bytes):
                return result
            if isinstance(result, str):
                return result.encode("utf-8")
            raise InvalidArgumentError(
                argument_name="read_result",
                additional_data={"got": type(result).__name__},
            )
        raise InvalidArgumentError(
            argument_name="source",
            additional_data={"got": type(source).__name__},
        )

    @staticmethod
    def _process_source(
        source: str | bytes | BinaryIO | HttpUrl,
        attachment_type: EmailAttachmentType,
        max_size: int | None = None,
    ) -> bytes:
        """Process different types of attachment sources."""
        if attachment_type == EmailAttachmentType.URL:
            return AttachmentHandler._process_url_source(source, max_size)
        processors = {
            EmailAttachmentType.FILE: AttachmentHandler._process_file_source,
            EmailAttachmentType.BASE64: AttachmentHandler._process_base64_source,
            EmailAttachmentType.URL: AttachmentHandler._process_url_source,
            EmailAttachmentType.BINARY: AttachmentHandler._read_binary_content,
        }
        processor = processors.get(attachment_type)
        if processor is None:
            raise InvalidArgumentError(
                argument_name="attachment_type",
                additional_data={"got": str(attachment_type)},
            )
        return processor(source)

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
            raise InvalidArgumentError(argument_name="content_type")
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
        """Initialize EmailAdapter."""
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
        template_vars: dict[str, Any] | None = None,
    ) -> None:
        """Send email with advanced features and connection pooling.

        Args:
            to_email: Primary recipient(s) of the email.
            subject: Email subject line.
            body: Email body content (plain text or HTML).
            cc: Carbon copy recipient(s).
            bcc: Blind carbon copy recipient(s).
            attachments: List of file paths or EmailAttachmentDTO objects.
            html: If True, treats body as HTML content, otherwise plain text.
            template: A template string to render using template_vars.
            template_vars: Variables to use when rendering the template.

        Raises:
            InvalidArgumentError: If no SMTP server is configured or an attachment is invalid.
            UnavailableError: If the SMTP server cannot be reached or the email cannot be sent
                after ``MAX_RETRIES`` attempts. Delivery is at-least-once: a connection that drops after the
                message was sent can lead to a duplicate on retry; permanent (5xx) rejections are not retried.
        """
        self._send_email_traced(
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

    @trace_span(name="email.send", kind=_smtp_span_kind(), attributes={"network.protocol.name": "smtp"})
    def _send_email_traced(
        self,
        to_email: EmailStr | list[EmailStr],
        subject: str,
        body: str,
        cc: EmailStr | list[EmailStr] | None = None,
        bcc: EmailStr | list[EmailStr] | None = None,
        attachments: list[str | EmailAttachmentDTO] | None = None,
        html: bool = False,
        template: str | None = None,
        template_vars: dict[str, Any] | None = None,
    ) -> None:
        """Send the email inside the ``email.send`` span (SMTP client span without any message content)."""
        _annotate_current_span(
            {
                "server.address": self.config.SMTP_SERVER or "",
                "server.port": self.config.SMTP_PORT,
                "email.recipient_count": len(self._get_all_recipients(to_email, cc, bcc)),
                "email.attachment_count": len(attachments or []),
            },
        )
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

            last_error: Exception | None = None
            for _ in range(self.config.MAX_RETRIES):
                try:
                    if not connection.smtp_connection:
                        connection.connect()
                    if connection.smtp_connection:
                        connection.smtp_connection.send_message(msg, to_addrs=recipients)
                        logger.debug("Email sent successfully to %s", to_email)
                        return
                    last_error = connection.last_error
                except (MessageError, ValueError) as e:
                    raise InvalidArgumentError(
                        argument_name="message",
                        additional_data={"reason": "invalid_header", "detail": str(e)},
                    ) from e
                except (smtplib.SMTPException, OSError, TimeoutError) as e:
                    BaseUtils.capture_exception(e)
                    last_error = e
                    connection.disconnect()  # Close the broken session; reconnect on next attempt
                    if isinstance(e, smtplib.SMTPResponseException) and e.smtp_code >= _PERMANENT_FAILURE_CODE:
                        break  # Permanent rejection: a retry cannot succeed and could duplicate the message

            raise UnavailableError(resource_type="SMTP") from last_error
        except (smtplib.SMTPException, OSError, TimeoutError) as e:
            BaseUtils.capture_exception(e)
            raise UnavailableError(resource_type="SMTP") from e
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
        template_vars: dict[str, Any] | None = None,
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
            try:
                from jinja2 import Template
            except ImportError as exception:
                raise ConfigurationError(
                    operation="email_template",
                    reason="jinja2 is not installed; install it to render email templates",
                ) from exception
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

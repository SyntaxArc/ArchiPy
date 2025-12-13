from abc import abstractmethod

from pydantic import EmailStr

from archipy.models.dtos.email_dtos import EmailAttachmentDTO


class EmailPort:
    """Interface for email sending operations.

    This interface defines the contract for email adapters, ensuring
    a consistent approach to sending emails across different implementations.
    It provides a comprehensive set of features including support for:

    - Multiple recipients (To, CC, BCC)
    - HTML and plain text content
    - File and in-memory attachments
    - Template-based email rendering

    Implementing classes should handle the details of connecting to an
    email service, managing connections, and ensuring reliable delivery.

    Examples:
        >>> from archipy.adapters.email.ports import EmailPort
        >>>
        >>> class CustomEmailAdapter(EmailPort):
        ...     def __init__(self, config):
        ...         self.config = config
        ...
        ...     def send_email(
        ...         self,
        ...         to_email,
        ...         subject,
        ...         body,
        ...         cc=None,
        ...         bcc=None,
        ...         attachments=None,
        ...         html=False,
        ...         template=None,
        ...         template_vars=None,
        ...     ):
        ...         # Implementation details...
        ...         pass
    """

    @abstractmethod
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
        """Send an email with various options and features.

        This method handles the composition and delivery of an email with
        support for multiple recipients, HTML content, templates, and attachments.

        Args:
            to_email: Primary recipient(s) of the email
            subject: Email subject line
            body: Email body content (either plain text or HTML)
            cc: Carbon copy recipient(s)
            bcc: Blind carbon copy recipient(s)
            attachments: List of file paths or EmailAttachmentDTO objects
            html: If True, treats body as HTML content, otherwise plain text
            template: A template string to render using template_vars
            template_vars: Variables to use when rendering the template

        Returns:
            None

        Examples:
            >>> # Simple text email
            >>> adapter.send_email(to_email="user@example.com", subject="Hello", body="This is a test email")
            >>>
            >>> # HTML email with attachment
            >>> adapter.send_email(
            ...     to_email=["user1@example.com", "user2@example.com"],
            ...     subject="Report",
            ...     body="<h1>Monthly Report</h1><p>Please see attached</p>",
            ...     html=True,
            ...     attachments=["path/to/report.pdf"],
            ... )
            >>>
            >>> # Template-based email
            >>> template = "Hello {{ name }}, your account expires on {{ date }}"
            >>> adapter.send_email(
            ...     to_email="user@example.com",
            ...     subject="Account Expiration",
            ...     body="",  # Body will be rendered from template
            ...     template=template,
            ...     template_vars={"name": "John", "date": "2023-12-31"},
            ... )
        """
        raise NotImplementedError

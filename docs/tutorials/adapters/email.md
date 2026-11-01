---
title: Email Adapter Tutorial
description: Practical examples for using the ArchiPy email adapter.
---

# Email Adapter Tutorial

This page demonstrates how to use ArchiPy's email adapter for sending emails with proper error
handling and logging.

## Installation

```bash
uv add "archipy[email]"
```

## Configuration

Configure the email adapter via environment variables or an `EmailConfig` object.

### Environment Variables

!!! warning
    Keep `EMAIL__PASSWORD` out of source control. Load it from the environment or a secrets store.

!!! note
    `EMAIL__CONNECTION_TIMEOUT` defaults to `30` seconds. Pooled connections idle longer than
    `EMAIL__CONNECTION_REFRESH_SECONDS` are reconnected.

```bash
EMAIL__SMTP_SERVER=smtp.example.com
EMAIL__SMTP_PORT=587
EMAIL__USERNAME=your-username
EMAIL__PASSWORD=your-password
EMAIL__POOL_SIZE=5
EMAIL__CONNECTION_TIMEOUT=30
EMAIL__CONNECTION_REFRESH_SECONDS=300  # reconnect pooled connections idle longer than this
EMAIL__TLS_MODE=starttls  # auto (deprecated), none, starttls or implicit
EMAIL__TLS_CA_FILE=/etc/ssl/smtp-ca.pem  # optional CA bundle that verifies the server
EMAIL__TLS_VERIFY=true
```

### Transport Security

`EMAIL__TLS_MODE` selects how the SMTP session is protected:

| Mode       | Behavior                                                                                      |
|------------|-----------------------------------------------------------------------------------------------|
| `starttls` | Requires the server to offer STARTTLS and the upgrade to succeed; never falls back to clear text. |
| `implicit` | Opens a TLS connection from the start (SMTPS, usually port 465).                              |
| `none`     | Sends in clear text, only for trusted networks.                                               |
| `auto`     | Default, deprecated: upgrades only if STARTTLS is offered, without verifying the certificate. |

`starttls` and `implicit` verify the certificate and host name against the system CAs, or against
`EMAIL__TLS_CA_FILE` when set. `EMAIL__TLS_VERIFY=false` turns verification off.

!!! warning
    `auto` keeps the previous behavior and emits a `DeprecationWarning`. Set `EMAIL__TLS_MODE`
    explicitly; the default will change in a future major release.

`TLS_MODE=none` with credentials and `TLS_VERIFY=false` each emit a `DeprecationWarning` (clear-text login
and unverified certificates expose credentials to interception); both will be rejected in a future major
release. A login over a session without TLS is also logged as a warning.

`USERNAME` and `PASSWORD` must be set together. A half-set pair raises `ConfigurationError` when
`TLS_MODE` is not `auto`; in `auto` mode login is skipped with a `DeprecationWarning`.

`EMAIL__LOCAL_HOSTNAME` sets the name sent in `EHLO`, and `EMAIL__SOURCE_ADDRESS` with
`EMAIL__SOURCE_PORT` binds the local end of the connection.

### Direct Configuration

```python
from archipy.configs.config_template import EmailConfig

config = EmailConfig(
    SMTP_SERVER="smtp.example.com",
    SMTP_PORT=587,
    USERNAME="your-username",
    PASSWORD="your-password",  # noqa: S106
)
```

## Basic Usage

### Initializing the Adapter

```python
import logging

from archipy.adapters.email.adapters import EmailAdapter
from archipy.models.errors import ConfigurationError

# Configure logging
logger = logging.getLogger(__name__)

# Use global configuration (reads from BaseConfig.global_config().EMAIL)
try:
    email_adapter = EmailAdapter()
except ConfigurationError as e:
    logger.error(f"Failed to configure email adapter: {e}")
    raise
else:
    logger.info("Email adapter configured successfully")

# Or pass a custom config
from archipy.configs.config_template import EmailConfig

custom_config = EmailConfig(
    SMTP_SERVER="smtp.example.com",
    SMTP_PORT=587,
    USERNAME="your-username",
    PASSWORD="your-password",  # noqa: S106
)
email_adapter = EmailAdapter(config=custom_config)
```

### Sending Simple Emails

```python
import logging

from archipy.adapters.email.adapters import EmailAdapter
from archipy.models.errors import ConfigurationError

# Configure logging
logger = logging.getLogger(__name__)

email_adapter = EmailAdapter()

# Send a plain-text email
try:
    email_adapter.send_email(
        to_email="recipient@example.com",
        subject="Test Email",
        body="This is a test email from ArchiPy",
    )
except UnavailableError as e:
    logger.error(f"Failed to send email: {e}")
    raise
else:
    logger.info("Email sent successfully")
```

### Sending Emails with CC and BCC

```python
import logging

from archipy.adapters.email.adapters import EmailAdapter
from archipy.models.errors import ConfigurationError

# Configure logging
logger = logging.getLogger(__name__)

email_adapter = EmailAdapter()

# Single recipient or list for to_email, cc, and bcc
try:
    email_adapter.send_email(
        to_email=["primary@example.com"],
        subject="Important Notification",
        body="This message has CC and BCC recipients",
        cc=["cc1@example.com", "cc2@example.com"],
        bcc="bcc@example.com",
    )
except UnavailableError as e:
    logger.error(f"Failed to send email with CC/BCC: {e}")
    raise
else:
    logger.info("Email sent with CC and BCC recipients")
```

### Sending HTML Emails

```python
import logging

from archipy.adapters.email.adapters import EmailAdapter
from archipy.models.errors import ConfigurationError

# Configure logging
logger = logging.getLogger(__name__)

email_adapter = EmailAdapter()

html_content = """
<html>
  <body>
    <h1>Welcome to ArchiPy!</h1>
    <p>This is an <strong>HTML</strong> email.</p>
  </body>
</html>
"""

try:
    email_adapter.send_email(
        to_email="user@example.com",
        subject="HTML Email",
        body=html_content,
        html=True,
    )
except UnavailableError as e:
    logger.error(f"Failed to send HTML email: {e}")
    raise
else:
    logger.info("HTML email sent successfully")
```

### Sending Emails with Attachments

Pass file paths as strings or `EmailAttachmentDTO` objects in the `attachments` list:

```python
import logging

from archipy.adapters.email.adapters import EmailAdapter
from archipy.models.errors import InvalidArgumentError, UnavailableError

# Configure logging
logger = logging.getLogger(__name__)

email_adapter = EmailAdapter()

try:
    email_adapter.send_email(
        to_email="user@example.com",
        subject="Email with Attachment",
        body="Please find the attached document.",
        attachments=["/path/to/document.pdf", "/path/to/image.png"],
    )
except InvalidArgumentError as e:
    logger.error(f"Invalid attachment: {e}")
    raise
except UnavailableError as e:
    logger.error(f"Failed to send email with attachments: {e}")
    raise
else:
    logger.info("Email with attachments sent successfully")
```

## Integration with FastAPI

```python
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr

from archipy.adapters.email.adapters import EmailAdapter
from archipy.models.errors import InvalidArgumentError, UnavailableError

# Configure logging
logger = logging.getLogger(__name__)

app = FastAPI()
email_adapter = EmailAdapter()


class EmailRequest(BaseModel):
    to: list[EmailStr]
    subject: str
    body: str
    cc: list[EmailStr] | None = None
    bcc: list[EmailStr] | None = None


@app.post("/send-email")
async def send_email(email_request: EmailRequest) -> dict[str, str]:
    """Send an email via API endpoint.

    Args:
        email_request: Email details including recipients, subject, and body.

    Returns:
        Status message.

    Raises:
        HTTPException: If sending fails.
    """
    try:
        email_adapter.send_email(
            to_email=email_request.to,
            subject=email_request.subject,
            body=email_request.body,
            cc=email_request.cc,
            bcc=email_request.bcc,
        )
    except InvalidArgumentError as e:
        logger.error(f"Invalid email request: {e}")
        raise HTTPException(status_code=400, detail="Invalid email parameters") from e
    except UnavailableError as e:
        logger.error(f"Failed to send email: {e}")
        raise HTTPException(status_code=500, detail="Failed to send email") from e
    else:
        logger.info(f"Email sent to {len(email_request.to)} recipient(s)")
        return {"message": "Email sent successfully"}
```

## Error Handling

```python
import logging

from archipy.adapters.email.adapters import EmailAdapter
from archipy.configs.config_template import EmailConfig
from archipy.models.errors import ConfigurationError, InvalidArgumentError, UnavailableError

# Configure logging
logger = logging.getLogger(__name__)


def send_notification_email(recipient: str, subject: str, body: str) -> bool:
    """Send a notification email with comprehensive error handling.

    Args:
        recipient: Email address of the recipient.
        subject: Email subject line.
        body: Email body content.

    Returns:
        True if the email was sent successfully.

    Raises:
        ConfigurationError: If the email adapter cannot be initialised.
        InvalidArgumentError: If email parameters are invalid.
        UnavailableError: If the email service fails.
    """
    try:
        email_adapter = EmailAdapter()
    except ConfigurationError as e:
        logger.error(f"Email adapter configuration failed: {e}")
        raise

    try:
        email_adapter.send_email(
            to_email=recipient,
            subject=subject,
            body=body,
        )
    except InvalidArgumentError as e:
        logger.error(f"Invalid email parameters: {e}")
        raise
    except UnavailableError as e:
        logger.error(f"Failed to send email: {e}")
        raise
    else:
        logger.info(f"Notification email sent to {recipient}")
        return True
```

## Tracing

No OpenTelemetry instrumentor exists for `smtplib`, so the adapter creates its own span. With
`OTEL__IS_ENABLED=true` and `OTEL__TRACES_ENABLED=true`, every `send_email` call emits one
client span:

| Span         | Attribute                | Value                                                |
|--------------|--------------------------|------------------------------------------------------|
| `email.send` | `network.protocol.name`  | `smtp`                                               |
|              | `server.address`         | Configured SMTP host                                 |
|              | `server.port`            | Configured SMTP port                                 |
|              | `email.tls_mode`         | `starttls`, `implicit` or `none`, as negotiated with the server  |
|              | `email.recipient_count`  | Number of to, cc and bcc recipients                  |
|              | `email.attachment_count` | Number of attachments                                |

A failed send (unreachable server, rejected credentials) marks the span as an error and records the
`UnavailableError`. Credentials, addresses, subjects and bodies are never added to spans.

### Delivery Semantics

`MAX_RETRIES` is the number of send attempts. Delivery is at-least-once: if the connection drops after the
server received the message but before it confirmed, the retry can deliver a duplicate. Permanent (5xx)
rejections are not retried. A header that cannot be encoded (for example a subject with a line break) raises
`InvalidArgumentError`.

### URL Attachments

URL attachments accept `http` and `https` only, are downloaded with the `EMAIL__ATTACHMENT_URL_TIMEOUT`
timeout, and stop once `ATTACHMENT_MAX_SIZE` is exceeded. Set `EMAIL__ATTACHMENT_URL_ALLOWED_HOSTS` when the
URL can come from user input, to avoid server-side request forgery.

## See Also

- [Error Handling](../error_handling.md) — Exception handling patterns with proper chaining
- [Configuration Management](../config_management.md) — Email configuration setup
- [BDD Testing](../testing_strategy.md) — Testing email operations
- BDD feature files — [`email_adapter.feature`](https://github.com/SyntaxArc/ArchiPy/blob/master/features/email_adapter.feature), [`email_adapter_apm.feature`](https://github.com/SyntaxArc/ArchiPy/blob/master/features/email_adapter_apm.feature)
- [API Reference](../../api_reference/adapters/email.md) — Full Email adapter API documentation

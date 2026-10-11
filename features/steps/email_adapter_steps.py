import base64
import smtplib
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest import mock

from behave import given, then, when
from pydantic import ValidationError

from archipy.adapters.email.adapters import AttachmentHandler, EmailAdapter, EmailConnectionPool
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import EmailConfig
from archipy.helpers.utils.datetime_utils import DatetimeUtils
from archipy.models.errors import InvalidArgumentError, UnavailableError
from archipy.models.types.email_types import EmailAttachmentType
from features.test_helpers import get_current_scenario_context


class SmtpRecorder:
    """In-memory stand-in for an SMTP server, installed in place of smtplib.SMTP."""

    def __init__(self):
        self.sessions = []
        self.delivered = []
        self.delivered_by = []
        self.refuse_connections = False
        self.send_failures = 0

    def smtp_class(self):
        recorder = self

        class FakeSMTP:
            def __init__(self, host, port, timeout=None):
                if recorder.refuse_connections:
                    raise ConnectionRefusedError("connection refused")
                self.host = host
                self.port = port
                self.timeout = timeout
                self.started_tls = False
                self.login_args = None
                self.closed = False
                recorder.sessions.append(self)

            def starttls(self):
                self.started_tls = True

            def login(self, username, password):
                self.login_args = (username, password)

            def send_message(self, msg, to_addrs=None):
                if recorder.send_failures > 0:
                    recorder.send_failures -= 1
                    raise smtplib.SMTPServerDisconnected("server went away")
                recorder.delivered.append((msg, list(to_addrs or [])))
                recorder.delivered_by.append(self)

            def quit(self):
                self.closed = True

        return FakeSMTP


def _install_email_config(context, **overrides):
    """Set EMAIL on the global config and restore the previous state after the scenario."""
    try:
        previous_global = BaseConfig.global_config()
    except AssertionError:
        previous_global = None
        BaseConfig.set_global(BaseConfig())
    config = BaseConfig.global_config()
    previous_email = config.EMAIL
    values = {"POOL_SIZE": 1, "MAX_RETRIES": 3}
    values.update(overrides)
    config.EMAIL = EmailConfig(**values)

    def restore():
        config.EMAIL = previous_email
        if previous_global is None:
            BaseConfig.set_global(None)

    context.add_cleanup(restore)
    return config.EMAIL


def _install_smtp(context, scenario_context):
    recorder = SmtpRecorder()
    patcher = mock.patch.object(smtplib, "SMTP", recorder.smtp_class())
    patcher.start()
    context.add_cleanup(patcher.stop)
    scenario_context.store("smtp", recorder)
    return recorder


def _configure_server(context, server, refuse=False, send_failures=0):
    scenario_context = get_current_scenario_context(context)
    recorder = _install_smtp(context, scenario_context)
    recorder.refuse_connections = refuse
    recorder.send_failures = send_failures
    _install_email_config(context, SMTP_SERVER=server)
    scenario_context.store("smtp_server", server)


def _split(addresses):
    return [address.strip() for address in addresses.split(",")]


def _single_or_list(addresses):
    parts = _split(addresses)
    return parts[0] if len(parts) == 1 else parts


def _delivered(context):
    recorder = get_current_scenario_context(context).get("smtp")
    assert recorder.delivered, "no email was delivered"
    return recorder.delivered[-1]


def _send(context, to_email, subject, body, **kwargs):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("error", None)
    try:
        scenario_context.get("email_adapter").send_email(to_email, subject, body, **kwargs)
    except Exception as exception:
        scenario_context.store("error", exception)


@given('an SMTP server "{server}" that accepts mail')
def step_given_smtp_accepts(context, server):
    _configure_server(context, server)


@given('an SMTP server "{server}" that refuses connections')
def step_given_smtp_refuses(context, server):
    _configure_server(context, server, refuse=True)


@given('an SMTP server "{server}" that fails the next {count:d} sends')
def step_given_smtp_fails_sends(context, server, count):
    _configure_server(context, server, send_failures=count)


@given("no SMTP server is configured")
def step_given_no_smtp_server(context):
    scenario_context = get_current_scenario_context(context)
    _install_smtp(context, scenario_context)
    _install_email_config(context)


@given('SMTP credentials "{username}" and "{password}"')
def step_given_smtp_credentials(context, username, password):
    config = BaseConfig.global_config().EMAIL
    config.USERNAME = username
    config.PASSWORD = password


@given("the configured attachment maximum size is {size:d} bytes")
def step_given_attachment_max_size(context, size):
    BaseConfig.global_config().EMAIL.ATTACHMENT_MAX_SIZE = size


@given("an email adapter")
def step_given_email_adapter(context):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("email_adapter", EmailAdapter())


@given("an email connection pool of size {size:d}")
def step_given_connection_pool(context, size):
    scenario_context = get_current_scenario_context(context)
    BaseConfig.global_config().EMAIL.POOL_SIZE = size
    scenario_context.store("pool", EmailConnectionPool(BaseConfig.global_config().EMAIL))


def _tmp_dir(context):
    directory = tempfile.TemporaryDirectory()
    context.add_cleanup(directory.cleanup)
    return Path(directory.name)


@given('a FILE attachment "{filename}" with content "{content}"')
def step_given_file_attachment(context, filename, content):
    scenario_context = get_current_scenario_context(context)
    path = _tmp_dir(context) / filename
    path.write_text(content)
    attachment = AttachmentHandler.create_attachment(
        source=str(path),
        filename=filename,
        attachment_type=EmailAttachmentType.FILE,
    )
    scenario_context.store("attachment", attachment)


@given('a file on disk "{filename}" with content "{content}"')
def step_given_file_on_disk(context, filename, content):
    scenario_context = get_current_scenario_context(context)
    path = _tmp_dir(context) / filename
    path.write_text(content)
    scenario_context.store("file_path", str(path))


@given('a BASE64 attachment "{filename}" with content "{content}"')
def step_given_base64_attachment(context, filename, content):
    scenario_context = get_current_scenario_context(context)
    encoded = base64.b64encode(content.encode()).decode()
    attachment = AttachmentHandler.create_attachment(
        source=encoded,
        filename=filename,
        attachment_type=EmailAttachmentType.BASE64,
    )
    scenario_context.store("attachment", attachment)


@given('a BINARY attachment "{filename}" with content "{content}"')
def step_given_binary_attachment(context, filename, content):
    scenario_context = get_current_scenario_context(context)
    attachment = AttachmentHandler.create_attachment(
        source=content.encode(),
        filename=filename,
        attachment_type=EmailAttachmentType.BINARY,
    )
    scenario_context.store("attachment", attachment)


@given('a URL attachment "{filename}" served with content "{content}"')
def step_given_url_attachment(context, filename, content):
    scenario_context = get_current_scenario_context(context)
    url = f"https://files.test.local/{filename}"
    requested = []

    def fake_get(request_url, **kwargs):
        requested.append(request_url)
        response = mock.Mock()
        response.content = content.encode()
        response.raise_for_status.return_value = None
        return response

    patcher = mock.patch("archipy.adapters.email.adapters.httpx2.get", side_effect=fake_get)
    patcher.start()
    context.add_cleanup(patcher.stop)
    scenario_context.store("requested_urls", requested)
    attachment = AttachmentHandler.create_attachment(
        source=url,
        filename=filename,
        attachment_type=EmailAttachmentType.URL,
    )
    scenario_context.store("attachment", attachment)


@when('I send an email to "{to_email}" with subject "{subject}" and body "{body}"')
def step_when_send_email(context, to_email, subject, body):
    _send(context, _single_or_list(to_email), subject, body)


@when('I try to send an email to "{to_email}" with subject "{subject}" and body "{body}"')
def step_when_try_send_email(context, to_email, subject, body):
    _send(context, _single_or_list(to_email), subject, body)


@when('I send an HTML email to "{to_email}" with subject "{subject}" and body "{body}"')
def step_when_send_html_email(context, to_email, subject, body):
    _send(context, to_email, subject, body, html=True)


@when('I send an email to "{to_email}" using template "{template}" with name "{name}"')
def step_when_send_template_email(context, to_email, template, name):
    _send(context, to_email, "Templated", "ignored", template=template, template_vars={"name": name})


@when('I send an email to "{to_email}" with cc "{cc}" and bcc "{bcc}"')
def step_when_send_email_cc_bcc(context, to_email, cc, bcc):
    _send(context, to_email, "Copies", "Body", cc=cc, bcc=bcc)


@when("I send the email with the attachment")
def step_when_send_with_attachment(context):
    attachment = get_current_scenario_context(context).get("attachment")
    _send(context, "alice@example.com", "Attached", "See attachment", attachments=[attachment])


@when("I send the email with the file path as attachment")
def step_when_send_with_path(context):
    path = get_current_scenario_context(context).get("file_path")
    _send(context, "alice@example.com", "Attached", "See attachment", attachments=[path])


@when("I try to create a BINARY attachment \"{filename}\" of {size:d} bytes with a maximum size of {max_size:d} bytes")
def step_when_create_oversized_attachment(context, filename, size, max_size):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("error", None)
    try:
        AttachmentHandler.create_attachment(
            source=b"x" * size,
            filename=filename,
            attachment_type=EmailAttachmentType.BINARY,
            max_size=max_size,
        )
    except Exception as exception:
        scenario_context.store("error", exception)


@when('I try to create a BINARY attachment "{filename}" of {size:d} bytes with the configured maximum size')
def step_when_create_oversized_attachment_configured(context, filename, size):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("error", None)
    try:
        AttachmentHandler.create_attachment(
            source=b"x" * size,
            filename=filename,
            attachment_type=EmailAttachmentType.BINARY,
        )
    except Exception as exception:
        scenario_context.store("error", exception)


@when("I take a connection from the pool")
def step_when_take_connection(context):
    scenario_context = get_current_scenario_context(context)
    connection = scenario_context.get("pool").get_connection()
    history = scenario_context.get("connections", [])
    history.append(connection)
    scenario_context.store("connections", history)


@when("I return the connection to the pool")
def step_when_return_connection(context):
    scenario_context = get_current_scenario_context(context)
    scenario_context.get("pool").return_connection(scenario_context.get("connections")[-1])


@when("{seconds:d} seconds pass")
def step_when_time_passes(context, seconds):
    real_now = DatetimeUtils.get_datetime_now()
    patcher = mock.patch.object(
        DatetimeUtils,
        "get_datetime_now",
        side_effect=lambda: real_now + timedelta(seconds=seconds),
    )
    patcher.start()
    context.add_cleanup(patcher.stop)


@then("the SMTP server received {count:d} email")
@then("the SMTP server received {count:d} emails")
def step_then_received_count(context, count):
    recorder = get_current_scenario_context(context).get("smtp")
    assert len(recorder.delivered) == count, f"expected {count}, got {len(recorder.delivered)}"


@then("the SMTP server opened {count:d} sessions")
def step_then_sessions_count(context, count):
    recorder = get_current_scenario_context(context).get("smtp")
    assert len(recorder.sessions) == count, f"expected {count}, got {len(recorder.sessions)}"


@then('the delivered email has subject "{subject}"')
def step_then_subject(context, subject):
    msg, _ = _delivered(context)
    assert msg["Subject"] == subject


@then('the delivered email is addressed to "{to_email}"')
def step_then_addressed_to(context, to_email):
    msg, _ = _delivered(context)
    assert msg["To"] == to_email


@then('the delivered email has cc "{cc}"')
def step_then_cc(context, cc):
    msg, _ = _delivered(context)
    assert msg["Cc"] == cc


@then('the delivered email is sent from "{sender}"')
def step_then_sender(context, sender):
    msg, _ = _delivered(context)
    assert msg["From"] == sender


@then('the SMTP envelope recipients are "{recipients}"')
def step_then_envelope(context, recipients):
    _, to_addrs = _delivered(context)
    assert to_addrs == _split(recipients), to_addrs


def _body_part(msg):
    return msg.get_payload(0)


@then('the delivered email body is plain text "{body}"')
def step_then_plain_body(context, body):
    msg, _ = _delivered(context)
    part = _body_part(msg)
    assert part.get_content_subtype() == "plain"
    assert part.get_payload(decode=True).decode() == body


@then('the delivered email body is HTML "{body}"')
def step_then_html_body(context, body):
    msg, _ = _delivered(context)
    part = _body_part(msg)
    assert part.get_content_subtype() == "html"
    assert part.get_payload(decode=True).decode() == body


@then("the SMTP session used TLS")
def step_then_tls(context):
    recorder = get_current_scenario_context(context).get("smtp")
    assert recorder.sessions[0].started_tls


@then('the SMTP session logged in as "{username}" with password "{password}"')
def step_then_login(context, username, password):
    recorder = get_current_scenario_context(context).get("smtp")
    assert recorder.sessions[0].login_args == (username, password)


@then('the delivered email has attachment "{filename}" of type "{content_type}" with content "{content}"')
def step_then_attachment(context, filename, content_type, content):
    msg, _ = _delivered(context)
    parts = [part for part in msg.get_payload() if part.get_filename() == filename]
    assert len(parts) == 1, f"expected one attachment named {filename}"
    assert parts[0].get_content_type() == content_type
    assert parts[0].get_payload(decode=True).decode() == content


@then('the URL "{url}" was downloaded')
def step_then_url_downloaded(context, url):
    assert get_current_scenario_context(context).get("requested_urls") == [url]


@then("the attachment is rejected as an invalid argument for exceeding the maximum size")
def step_then_attachment_rejected(context):
    error = get_current_scenario_context(context).get("error")
    assert isinstance(error, InvalidArgumentError), repr(error)
    assert isinstance(error.__cause__, ValidationError), repr(error.__cause__)
    assert "exceeds maximum allowed size" in str(error.__cause__)


@then('an unavailable error is raised for "{resource}"')
def step_then_unavailable(context, resource):
    error = get_current_scenario_context(context).get("error")
    assert isinstance(error, UnavailableError), repr(error)
    assert error.additional_data["resource_type"] == resource, error.additional_data


@then("the unavailable error was caused by a connection error")
def step_then_unavailable_cause_connection(context):
    error = get_current_scenario_context(context).get("error")
    assert isinstance(error.__cause__, ConnectionRefusedError), repr(error.__cause__)


@then("the unavailable error was caused by a dropped SMTP session")
def step_then_unavailable_cause_dropped(context):
    error = get_current_scenario_context(context).get("error")
    assert isinstance(error.__cause__, smtplib.SMTPServerDisconnected), repr(error.__cause__)


@then("every opened SMTP session was closed")
def step_then_every_session_closed(context):
    recorder = get_current_scenario_context(context).get("smtp")
    assert recorder.sessions, "no session was opened"
    assert all(session.closed for session in recorder.sessions)


@then("the delivered email was sent over the second SMTP session")
def step_then_delivered_over_second_session(context):
    recorder = get_current_scenario_context(context).get("smtp")
    assert recorder.delivered_by == [recorder.sessions[1]]


@then('an invalid argument error is raised for "{argument}"')
def step_then_invalid_argument(context, argument):
    error = get_current_scenario_context(context).get("error")
    assert isinstance(error, InvalidArgumentError), repr(error)
    assert argument in str(error) or argument in str(getattr(error, "argument_name", "")), str(error)


@then("no error is raised")
def step_then_no_error(context):
    assert get_current_scenario_context(context).get("error") is None


@then("the connection is established")
def step_then_connection_established(context):
    connection = get_current_scenario_context(context).get("connections")[-1]
    assert connection.smtp_connection is not None


@then("the same connection is handed out")
def step_then_same_connection(context):
    connections = get_current_scenario_context(context).get("connections")
    assert connections[0] is connections[-1]


@then("the first SMTP session was closed")
def step_then_first_session_closed(context):
    recorder = get_current_scenario_context(context).get("smtp")
    assert recorder.sessions[0].closed
    assert not recorder.sessions[-1].closed

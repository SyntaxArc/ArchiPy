import base64
import json
import smtplib
import socket
import ssl
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock

import httpx2
from behave import given, then, when
from pydantic import ValidationError

from archipy.adapters.email.adapters import AttachmentHandler, EmailAdapter, EmailConnectionPool
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import EmailConfig
from archipy.models.errors import InvalidArgumentError, UnavailableError
from archipy.models.types.email_types import EmailAttachmentType
from features.test_containers import ContainerManager
from features.test_helpers import get_current_scenario_context


MAILPIT_NAMES = ("mailpit", "mailpit-plain")
_active_mailpit = {"name": "mailpit"}


def _mailpit(name=None):
    instance = ContainerManager._container_instances.get(name or _active_mailpit["name"])
    assert instance is not None, "Mailpit container is not running"
    return instance


def _api(method, path, name=None):
    response = httpx2.request(method, f"{_mailpit(name).api_url}{path}", timeout=10)
    response.raise_for_status()
    return response.content


def _api_json(path):
    return json.loads(_api("GET", path))


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


def _inject_send_failures(context, scenario_context, count):
    """Fault injection: make the next ``count`` smtplib send_message calls drop the session, then work normally."""
    original = smtplib.SMTP.send_message
    state = {"remaining": count, "failed_sessions": [], "used_sessions": []}

    def flaky(self, msg, *args, **kwargs):
        if state["remaining"] > 0:
            state["remaining"] -= 1
            state["failed_sessions"].append(self)
            raise smtplib.SMTPServerDisconnected("server went away")
        state["used_sessions"].append(self)
        return original(self, msg, *args, **kwargs)

    patcher = mock.patch.object(smtplib.SMTP, "send_message", flaky)
    patcher.start()
    context.add_cleanup(patcher.stop)
    scenario_context.store("faults", state)


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


def _configure_mailpit(context, name):
    _active_mailpit["name"] = name
    mailpit = _mailpit(name)
    _install_email_config(
        context,
        SMTP_SERVER=mailpit.host,
        SMTP_PORT=mailpit.smtp_port,
        USERNAME=mailpit.USERNAME,
        PASSWORD=mailpit.PASSWORD,
    )


@given("an empty Mailpit mailbox")
def step_given_empty_mailbox(context):
    _active_mailpit["name"] = "mailpit"
    for name in MAILPIT_NAMES:
        if name in ContainerManager._container_instances:
            _api("DELETE", "/api/v1/messages", name)


@given("the Mailpit SMTP server is configured")
def step_given_mailpit_configured(context):
    _configure_mailpit(context, "mailpit")


@given("the plain Mailpit SMTP server is configured")
def step_given_plain_mailpit_configured(context):
    _configure_mailpit(context, "mailpit-plain")


@given("an SMTP endpoint on a closed port")
def step_given_closed_port(context):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    _install_email_config(context, SMTP_SERVER="127.0.0.1", SMTP_PORT=port)


@given("the next {count:d} SMTP sends fail")
def step_given_sends_fail(context, count):
    _inject_send_failures(context, get_current_scenario_context(context), count)


@given("no SMTP server is configured")
def step_given_no_smtp_server(context):
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


@given('a URL attachment "{filename}" served with content "{content}" by a local HTTP server')
def step_given_url_attachment(context, filename, content):
    scenario_context = get_current_scenario_context(context)
    requested = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requested.append(self.path)
            payload = content.encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def stop_server():
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    context.add_cleanup(stop_server)
    scenario_context.store("requested_urls", requested)
    attachment = AttachmentHandler.create_attachment(
        source=f"http://127.0.0.1:{server.server_port}/{filename}",
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
    sessions = scenario_context.get("sessions", [])
    sessions.append(connection.smtp_connection)
    scenario_context.store("sessions", sessions)


@when("I return the connection to the pool")
def step_when_return_connection(context):
    scenario_context = get_current_scenario_context(context)
    scenario_context.get("pool").return_connection(scenario_context.get("connections")[-1])


@given("the connection refresh interval is {seconds:d} seconds")
def step_given_refresh_interval(context, seconds):
    BaseConfig.global_config().EMAIL.CONNECTION_REFRESH_SECONDS = seconds


@when("I wait {seconds:f} seconds")
def step_when_wait(context, seconds):
    time.sleep(seconds)


@then("Mailpit holds {count:d} email")
@then("Mailpit holds {count:d} emails")
def step_then_received_count(context, count):
    actual = _api_json("/api/v1/messages")["messages_count"]
    assert actual == count, f"expected {count}, got {actual}"


def _delivered(context):
    messages = _api_json("/api/v1/messages")["messages"]
    assert messages, "no email was delivered"
    return _api_json(f"/api/v1/message/{messages[0]['ID']}")


def _addresses(entries):
    return ", ".join(entry["Address"] for entry in entries)


@then('the delivered email has subject "{subject}"')
def step_then_subject(context, subject):
    assert _delivered(context)["Subject"] == subject


@then('the delivered email is addressed to "{to_email}"')
def step_then_addressed_to(context, to_email):
    assert _addresses(_delivered(context)["To"]) == to_email


@then('the delivered email has cc "{cc}"')
def step_then_cc(context, cc):
    assert _addresses(_delivered(context)["Cc"]) == cc


@then('the delivered email has bcc "{bcc}"')
def step_then_bcc(context, bcc):
    assert _addresses(_delivered(context)["Bcc"]) == bcc


@then('the delivered email is sent from "{sender}"')
def step_then_sender(context, sender):
    assert _delivered(context)["From"]["Address"] == sender


@then('the delivered email body is plain text "{body}"')
def step_then_plain_body(context, body):
    assert _delivered(context)["Text"].strip() == body


@then('the delivered email body is HTML "{body}"')
def step_then_html_body(context, body):
    assert _delivered(context)["HTML"].strip() == body


@then('the delivered email has attachment "{filename}" of type "{content_type}" with content "{content}"')
def step_then_attachment(context, filename, content_type, content):
    message = _delivered(context)
    parts = [part for part in message["Attachments"] if part["FileName"] == filename]
    assert len(parts) == 1, f"expected one attachment named {filename}, got {message['Attachments']}"
    assert parts[0]["ContentType"].split(";")[0] == content_type, parts[0]["ContentType"]
    body = _api("GET", f"/api/v1/message/{message['ID']}/part/{parts[0]['PartID']}")
    assert body.decode() == content, body


@then('the local HTTP server was asked for "{path}"')
def step_then_url_downloaded(context, path):
    assert get_current_scenario_context(context).get("requested_urls") == [path]


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


@then("the unavailable error was caused by an authentication failure")
def step_then_unavailable_cause_auth(context):
    error = get_current_scenario_context(context).get("error")
    assert isinstance(error.__cause__, smtplib.SMTPAuthenticationError), repr(error.__cause__)


def _adapter_socket(context):
    adapter = get_current_scenario_context(context).get("email_adapter")
    session = adapter.connection_pool.pool.queue[0].smtp_connection
    assert session is not None, "adapter holds no SMTP session"
    return session.sock


@then("the adapter session is encrypted with TLS")
def step_then_session_tls(context):
    assert isinstance(_adapter_socket(context), ssl.SSLSocket)


@then("the adapter session is not encrypted with TLS")
def step_then_session_not_tls(context):
    assert not isinstance(_adapter_socket(context), ssl.SSLSocket)


@then("every failed SMTP session was closed")
def step_then_failed_sessions_closed(context):
    failed = get_current_scenario_context(context).get("faults")["failed_sessions"]
    assert failed, "no session failed"
    assert all(session.sock is None for session in failed)


@then("the adapter holds no open SMTP session")
def step_then_adapter_no_session(context):
    adapter = get_current_scenario_context(context).get("email_adapter")
    assert all(connection.smtp_connection is None for connection in adapter.connection_pool.pool.queue)


@then("the delivered email was sent over a new SMTP session")
def step_then_delivered_over_new_session(context):
    faults = get_current_scenario_context(context).get("faults")
    assert len(faults["used_sessions"]) == 1
    assert faults["used_sessions"][0] is not faults["failed_sessions"][0]


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


@then("the same SMTP session was kept")
def step_then_same_session(context):
    connections = get_current_scenario_context(context).get("sessions")
    assert connections[0] is connections[-1]
    assert connections[0].sock is not None


@then("the SMTP session was replaced {replaced}")
def step_then_session_replaced(context, replaced):
    sessions = get_current_scenario_context(context).get("sessions")
    assert (sessions[0] is not sessions[-1]) == (replaced == "yes")


@then("the first SMTP session was closed")
def step_then_first_session_closed(context):
    sessions = get_current_scenario_context(context).get("sessions")
    assert sessions[0] is not sessions[-1]
    assert sessions[0].sock is None
    assert sessions[-1].sock is not None

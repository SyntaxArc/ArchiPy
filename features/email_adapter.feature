@needs-mailpit @needs-mailpit-plain @needs-otel-collector
Feature: Email adapter

  Background:
    Given an empty Mailpit mailbox

  Scenario: Send a plain-text email
    Given the Mailpit SMTP server is configured
    And an email adapter
    When I send an email to "alice@example.com" with subject "Hello" and body "Hi there"
    Then Mailpit holds 1 email
    And the delivered email has subject "Hello"
    And the delivered email is addressed to "alice@example.com"
    And the delivered email body is plain text "Hi there"

  Scenario: Send an HTML email
    Given the Mailpit SMTP server is configured
    And an email adapter
    When I send an HTML email to "alice@example.com" with subject "News" and body "<b>Big news</b>"
    Then Mailpit holds 1 email
    And the delivered email body is HTML "<b>Big news</b>"

  Scenario: Send an email rendered from a template
    Given the Mailpit SMTP server is configured
    And an email adapter
    When I send an email to "alice@example.com" using template "Dear {{ name }}" with name "Bob"
    Then the delivered email body is plain text "Dear Bob"

  Scenario: Send an email with cc and bcc recipients
    Given the Mailpit SMTP server is configured
    And an email adapter
    When I send an email to "to@example.com" with cc "cc@example.com" and bcc "bcc@example.com"
    Then the delivered email has cc "cc@example.com"
    And the delivered email has bcc "bcc@example.com"
    And the delivered email is addressed to "to@example.com"

  Scenario: Send an email to multiple recipients
    Given the Mailpit SMTP server is configured
    And an email adapter
    When I send an email to "one@example.com, two@example.com" with subject "Team" and body "Hi all"
    Then Mailpit holds 1 email
    And the delivered email is addressed to "one@example.com, two@example.com"

  Scenario: Correct SMTP credentials deliver the email
    Given the Mailpit SMTP server is configured
    And an email adapter
    When I send an email to "alice@example.com" with subject "Hello" and body "Hi there"
    Then Mailpit holds 1 email
    And the delivered email is sent from "mailer@example.com"

  Scenario: A wrong SMTP password is rejected and nothing is delivered
    Given the Mailpit SMTP server is configured
    And SMTP credentials "mailer@example.com" and "wrong-password"
    And an email adapter
    When I try to send an email to "alice@example.com" with subject "Hello" and body "Hi there"
    Then an unavailable error is raised for "SMTP"
    And the unavailable error was caused by an authentication failure
    And Mailpit holds 0 emails

  Scenario: STARTTLS is used when the server advertises it
    Given the Mailpit SMTP server is configured
    And an email adapter
    When I send an email to "alice@example.com" with subject "Hello" and body "Hi there"
    Then Mailpit holds 1 email
    And the adapter session is encrypted with TLS

  Scenario: STARTTLS is skipped when the server does not advertise it
    Given the plain Mailpit SMTP server is configured
    And an email adapter
    When I send an email to "alice@example.com" with subject "Hello" and body "Hi there"
    Then Mailpit holds 1 email
    And the delivered email is sent from "mailer@example.com"
    And the adapter session is not encrypted with TLS

  Scenario: A wrong SMTP password is rejected by the plain server too
    Given the plain Mailpit SMTP server is configured
    And SMTP credentials "mailer@example.com" and "wrong-password"
    And an email adapter
    When I try to send an email to "alice@example.com" with subject "Hello" and body "Hi there"
    Then an unavailable error is raised for "SMTP"
    And the unavailable error was caused by an authentication failure
    And Mailpit holds 0 emails

  Scenario: Required STARTTLS delivers over a verified TLS session
    Given the Mailpit SMTP server is configured
    And the SMTP transport security is "starttls" verified with the Mailpit CA
    And an email adapter
    When I send an email to "alice@example.com" with subject "Hello" and body "Hi there"
    Then Mailpit holds 1 email
    And the adapter session is encrypted with TLS

  Scenario: Required STARTTLS refuses an untrusted server certificate
    Given the Mailpit SMTP server is configured
    And the SMTP transport security is "starttls"
    And an email adapter
    When I try to send an email to "alice@example.com" with subject "Hello" and body "Hi there"
    Then an unavailable error is raised for "SMTP"
    And the unavailable error was caused by a certificate verification failure
    And Mailpit holds 0 emails

  Scenario: Required STARTTLS accepts an untrusted certificate when verification is off
    Given the Mailpit SMTP server is configured
    And the SMTP transport security is "starttls" without certificate verification
    And an email adapter
    When I send an email to "alice@example.com" with subject "Hello" and body "Hi there"
    Then Mailpit holds 1 email
    And the adapter session is encrypted with TLS

  Scenario: Required STARTTLS fails instead of falling back to clear text
    Given the plain Mailpit SMTP server is configured
    And the SMTP transport security is "starttls"
    And an email adapter
    When I try to send an email to "alice@example.com" with subject "Hello" and body "Hi there"
    Then an unavailable error is raised for "SMTP"
    And the unavailable error was caused by a missing STARTTLS offer
    And Mailpit holds 0 emails
    And the adapter holds no open SMTP session

  Scenario: Transport security none sends in clear text on request
    Given the Mailpit SMTP server is configured
    And the SMTP transport security is "none"
    And an email adapter
    When I send an email to "alice@example.com" with subject "Hello" and body "Hi there"
    Then Mailpit holds 1 email
    And the adapter session is not encrypted with TLS

  Scenario: Implicit TLS opens an encrypted session from the start
    Given a local SMTPS server
    And the SMTP transport security is "implicit" verified with the local SMTPS CA
    And an email connection pool of size 1
    When I take a connection from the pool
    Then the connection is established
    And the pooled session is encrypted with TLS

  Scenario: The deprecated auto transport security warns
    Given the Mailpit SMTP server is configured
    When I create an email adapter
    Then an email deprecation warning mentions "TLS_MODE"

  Scenario Outline: A half-set credential pair is rejected
    Given the Mailpit SMTP server is configured
    And the SMTP transport security is "<mode>" verified with the Mailpit CA
    And only the SMTP <field> is set
    When I create an email adapter
    Then a configuration error is raised for "email_credentials"

    Examples:
      | mode     | field    |
      | starttls | username |
      | starttls | password |
      | implicit | username |
      | none     | password |

  Scenario: The EHLO host name and source address are applied to the SMTP session
    Given the Mailpit SMTP server is configured
    And the SMTP local host name "mailer.example.org" and source address "127.0.0.1"
    And an email adapter
    When I send an email to "alice@example.com" with subject "Hello" and body "Hi there"
    Then Mailpit holds 1 email
    And the adapter session says EHLO as "mailer.example.org" from source address "127.0.0.1"

  Scenario: Send an email with a FILE attachment
    Given the Mailpit SMTP server is configured
    And an email adapter
    And a FILE attachment "notes.txt" with content "file body"
    When I send the email with the attachment
    Then the delivered email has attachment "notes.txt" of type "text/plain" with content "file body"

  Scenario: Send an email with a plain file path attachment
    Given the Mailpit SMTP server is configured
    And an email adapter
    And a file on disk "path.txt" with content "path body"
    When I send the email with the file path as attachment
    Then the delivered email has attachment "path.txt" of type "text/plain" with content "path body"

  Scenario: Send an email with a BASE64 attachment
    Given the Mailpit SMTP server is configured
    And an email adapter
    And a BASE64 attachment "data.json" with content "base64 body"
    When I send the email with the attachment
    Then the delivered email has attachment "data.json" of type "application/json" with content "base64 body"

  Scenario: Send an email with a BINARY attachment
    Given the Mailpit SMTP server is configured
    And an email adapter
    And a BINARY attachment "pixel.png" with content "binary body"
    When I send the email with the attachment
    Then the delivered email has attachment "pixel.png" of type "image/png" with content "binary body"

  Scenario: Send an email with a URL attachment
    Given the Mailpit SMTP server is configured
    And an email adapter
    And a URL attachment "remote.pdf" served with content "url body" by a local HTTP server
    When I send the email with the attachment
    Then the local HTTP server was asked for "/remote.pdf"
    And the delivered email has attachment "remote.pdf" of type "application/pdf" with content "url body"

  Scenario: Reject an attachment larger than the explicit maximum size
    When I try to create a BINARY attachment "big.bin" of 20 bytes with a maximum size of 10 bytes
    Then the attachment is rejected as an invalid argument for exceeding the maximum size

  Scenario: Reject an attachment larger than the configured maximum size
    Given the Mailpit SMTP server is configured
    And the configured attachment maximum size is 16 bytes
    When I try to create a BINARY attachment "big.bin" of 32 bytes with the configured maximum size
    Then the attachment is rejected as an invalid argument for exceeding the maximum size

  Scenario: Sending without an SMTP server configured is rejected
    Given no SMTP server is configured
    And an email adapter
    When I try to send an email to "alice@example.com" with subject "Hello" and body "Hi there"
    Then an invalid argument error is raised for "SMTP_SERVER"

  Scenario: Connection failure raises an unavailable error and nothing is delivered
    Given an SMTP endpoint on a closed port
    And an email adapter
    When I try to send an email to "alice@example.com" with subject "Hello" and body "Hi there"
    Then an unavailable error is raised for "SMTP"
    And the unavailable error was caused by a connection error
    And Mailpit holds 0 emails

  # Fault injection: a healthy real server never drops a session mid-send, so send_message is made to fail.
  Scenario: Persistent send failure raises an unavailable error and nothing is delivered
    Given the Mailpit SMTP server is configured
    And the next 3 SMTP sends fail
    And an email adapter
    When I try to send an email to "alice@example.com" with subject "Hello" and body "Hi there"
    Then an unavailable error is raised for "SMTP"
    And the unavailable error was caused by a dropped SMTP session
    And Mailpit holds 0 emails
    And every failed SMTP session was closed
    And the adapter holds no open SMTP session

  # Fault injection: see above.
  Scenario: Transient send failure closes the broken session and retries on a new one
    Given the Mailpit SMTP server is configured
    And the next 1 SMTP sends fail
    And an email adapter
    When I send an email to "alice@example.com" with subject "Hello" and body "Hi there"
    Then Mailpit holds 1 email
    And every failed SMTP session was closed
    And the delivered email was sent over a new SMTP session

  Scenario: A pooled connection is reused and returned to the pool
    Given the Mailpit SMTP server is configured
    And an email connection pool of size 1
    When I take a connection from the pool
    Then the connection is established
    When I return the connection to the pool
    And I take a connection from the pool
    Then the same connection is handed out
    And the same SMTP session was kept

  Scenario Outline: A pooled connection is refreshed only after the refresh interval
    Given the Mailpit SMTP server is configured
    And the connection refresh interval is <interval> seconds
    And an email connection pool of size 1
    When I take a connection from the pool
    And I return the connection to the pool
    And I wait <wait> seconds
    And I take a connection from the pool
    Then the SMTP session was replaced <replaced>

    Examples:
      | interval | wait | replaced |
      | 30       | 0.2  | no       |
      | 1        | 1.2  | yes      |

  Scenario: An idle pooled connection past the refresh interval closes the old session
    Given the Mailpit SMTP server is configured
    And the connection refresh interval is 1 seconds
    And an email connection pool of size 1
    When I take a connection from the pool
    And I return the connection to the pool
    And I wait 1.2 seconds
    And I take a connection from the pool
    Then the first SMTP session was closed

  @needs-otel-collector
  Scenario: httpx2 client calls emit HTTP spans
    Given adapter spans are exported to the collector
    When I call the Mailpit API with httpx2
    Then the collector should have a span with attribute "http.url" containing "/api/v1/info"

  Scenario: Sending an email emits an SMTP client span with safe attributes
    Given adapter spans are exported to the collector
    And the Mailpit SMTP server is configured
    And an email adapter
    When I send an email to "alice@example.com, bob@example.com" with subject "Quarterly numbers" and body "Confidential body"
    Then Mailpit holds 1 email
    And the "email.send" span points at the active Mailpit SMTP server
    And the "email.send" span has attribute "network.protocol.name" equal to "smtp"
    And the "email.send" span has attribute "email.recipient_count" equal to "2"
    And the "email.send" span has attribute "email.attachment_count" equal to "0"
    And the "email.send" span has attribute "email.tls_mode" equal to "starttls"

  Scenario: The SMTP span reports no TLS when the server does not advertise STARTTLS
    Given adapter spans are exported to the collector
    And the plain Mailpit SMTP server is configured
    And an email adapter
    When I send an email to "alice@example.com" with subject "Hello" and body "Hi there"
    Then the "email.send" span has attribute "email.tls_mode" equal to "none"

  Scenario: The SMTP span counts recipients and attachments
    Given adapter spans are exported to the collector
    And the Mailpit SMTP server is configured
    And a FILE attachment "notes.txt" with content "file body"
    And an email adapter
    When I send the email with the attachment
    Then the "email.send" span has attribute "email.recipient_count" equal to "1"
    And the "email.send" span has attribute "email.attachment_count" equal to "1"

  Scenario: A wrong SMTP password marks the span as failed without leaking secrets
    Given adapter spans are exported to the collector
    And the Mailpit SMTP server is configured
    And SMTP credentials "mailer@example.com" and "wrong-password"
    And an email adapter
    When I try to send an email to "alice@example.com" with subject "Quarterly numbers" and body "Confidential body"
    Then an unavailable error is raised for "SMTP"
    And the "email.send" span ends with error status
    And the "email.send" span records an exception of type "UnavailableError"
    And no exported span exposes "wrong-password"
    And no exported span exposes "alice@example.com"
    And no exported span exposes "Quarterly numbers"
    And no exported span exposes "Confidential body"

  Scenario: A connection failure marks the span as failed
    Given adapter spans are exported to the collector
    And an SMTP endpoint on a closed port
    And an email adapter
    When I try to send an email to "alice@example.com" with subject "Hello" and body "Hi there"
    Then an unavailable error is raised for "SMTP"
    And the "email.send" span ends with error status

  Scenario: A successful send does not expose the password, recipients, subject or body
    Given adapter spans are exported to the collector
    And the Mailpit SMTP server is configured
    And an email adapter
    When I send an email to "alice@example.com" with subject "Quarterly numbers" and body "Confidential body"
    Then the "email.send" span has attribute "network.protocol.name" equal to "smtp"
    And no exported span exposes "s3cret"
    And no exported span exposes "alice@example.com"
    And no exported span exposes "Quarterly numbers"
    And no exported span exposes "Confidential body"

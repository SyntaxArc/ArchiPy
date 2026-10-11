Feature: Email adapter

  Scenario: Send a plain-text email
    Given an SMTP server "smtp.test.local" that accepts mail
    And an email adapter
    When I send an email to "alice@example.com" with subject "Hello" and body "Hi there"
    Then the SMTP server received 1 email
    And the delivered email has subject "Hello"
    And the delivered email is addressed to "alice@example.com"
    And the delivered email body is plain text "Hi there"

  Scenario: Send an HTML email
    Given an SMTP server "smtp.test.local" that accepts mail
    And an email adapter
    When I send an HTML email to "alice@example.com" with subject "News" and body "<b>Big news</b>"
    Then the SMTP server received 1 email
    And the delivered email body is HTML "<b>Big news</b>"

  Scenario: Send an email rendered from a template
    Given an SMTP server "smtp.test.local" that accepts mail
    And an email adapter
    When I send an email to "alice@example.com" using template "Dear {{ name }}" with name "Bob"
    Then the delivered email body is plain text "Dear Bob"

  Scenario: Send an email with cc and bcc recipients
    Given an SMTP server "smtp.test.local" that accepts mail
    And an email adapter
    When I send an email to "to@example.com" with cc "cc@example.com" and bcc "bcc@example.com"
    Then the delivered email has cc "cc@example.com"
    And the SMTP envelope recipients are "to@example.com, cc@example.com, bcc@example.com"

  Scenario: Send an email to multiple recipients
    Given an SMTP server "smtp.test.local" that accepts mail
    And an email adapter
    When I send an email to "one@example.com, two@example.com" with subject "Team" and body "Hi all"
    Then the delivered email is addressed to "one@example.com, two@example.com"
    And the SMTP envelope recipients are "one@example.com, two@example.com"

  Scenario: SMTP credentials are used to log in
    Given an SMTP server "smtp.test.local" that accepts mail
    And SMTP credentials "mailer@example.com" and "s3cret"
    And an email adapter
    When I send an email to "alice@example.com" with subject "Hello" and body "Hi there"
    Then the SMTP session used TLS
    And the SMTP session logged in as "mailer@example.com" with password "s3cret"
    And the delivered email is sent from "mailer@example.com"

  Scenario: Send an email with a FILE attachment
    Given an SMTP server "smtp.test.local" that accepts mail
    And an email adapter
    And a FILE attachment "notes.txt" with content "file body"
    When I send the email with the attachment
    Then the delivered email has attachment "notes.txt" of type "text/plain" with content "file body"

  Scenario: Send an email with a plain file path attachment
    Given an SMTP server "smtp.test.local" that accepts mail
    And an email adapter
    And a file on disk "path.txt" with content "path body"
    When I send the email with the file path as attachment
    Then the delivered email has attachment "path.txt" of type "text/plain" with content "path body"

  Scenario: Send an email with a BASE64 attachment
    Given an SMTP server "smtp.test.local" that accepts mail
    And an email adapter
    And a BASE64 attachment "data.json" with content "base64 body"
    When I send the email with the attachment
    Then the delivered email has attachment "data.json" of type "application/json" with content "base64 body"

  Scenario: Send an email with a BINARY attachment
    Given an SMTP server "smtp.test.local" that accepts mail
    And an email adapter
    And a BINARY attachment "pixel.png" with content "binary body"
    When I send the email with the attachment
    Then the delivered email has attachment "pixel.png" of type "image/png" with content "binary body"

  Scenario: Send an email with a URL attachment
    Given an SMTP server "smtp.test.local" that accepts mail
    And an email adapter
    And a URL attachment "remote.pdf" served with content "url body"
    When I send the email with the attachment
    Then the URL "https://files.test.local/remote.pdf" was downloaded
    And the delivered email has attachment "remote.pdf" of type "application/pdf" with content "url body"

  Scenario: Reject an attachment larger than the explicit maximum size
    When I try to create a BINARY attachment "big.bin" of 20 bytes with a maximum size of 10 bytes
    Then the attachment is rejected as an invalid argument for exceeding the maximum size

  Scenario: Reject an attachment larger than the configured maximum size
    Given an SMTP server "smtp.test.local" that accepts mail
    And the configured attachment maximum size is 16 bytes
    When I try to create a BINARY attachment "big.bin" of 32 bytes with the configured maximum size
    Then the attachment is rejected as an invalid argument for exceeding the maximum size

  Scenario: Sending without an SMTP server configured is rejected
    Given no SMTP server is configured
    And an email adapter
    When I try to send an email to "alice@example.com" with subject "Hello" and body "Hi there"
    Then an invalid argument error is raised for "SMTP_SERVER"

  Scenario: Connection failure raises an unavailable error and nothing is delivered
    Given an SMTP server "smtp.test.local" that refuses connections
    And an email adapter
    When I try to send an email to "alice@example.com" with subject "Hello" and body "Hi there"
    Then an unavailable error is raised for "SMTP"
    And the unavailable error was caused by a connection error
    And the SMTP server received 0 emails

  Scenario: Persistent send failure raises an unavailable error and nothing is delivered
    Given an SMTP server "smtp.test.local" that fails the next 3 sends
    And an email adapter
    When I try to send an email to "alice@example.com" with subject "Hello" and body "Hi there"
    Then an unavailable error is raised for "SMTP"
    And the unavailable error was caused by a dropped SMTP session
    And the SMTP server received 0 emails
    And every opened SMTP session was closed

  Scenario: Transient send failure closes the broken session and retries on a new one
    Given an SMTP server "smtp.test.local" that fails the next 1 sends
    And an email adapter
    When I send an email to "alice@example.com" with subject "Hello" and body "Hi there"
    Then the SMTP server received 1 email
    And the SMTP server opened 2 sessions
    And the first SMTP session was closed
    And the delivered email was sent over the second SMTP session

  Scenario: A pooled connection is reused and returned to the pool
    Given an SMTP server "smtp.test.local" that accepts mail
    And an email connection pool of size 1
    When I take a connection from the pool
    Then the connection is established
    When I return the connection to the pool
    And I take a connection from the pool
    Then the same connection is handed out
    And the SMTP server opened 1 sessions

  Scenario Outline: A pooled connection is refreshed only after the refresh interval
    Given an SMTP server "smtp.test.local" that accepts mail
    And an email connection pool of size 1
    When I take a connection from the pool
    And I return the connection to the pool
    And <seconds> seconds pass
    And I take a connection from the pool
    Then the SMTP server opened <sessions> sessions

    Examples:
      | seconds | sessions |
      | 60      | 1        |
      | 301     | 2        |

  Scenario: An idle pooled connection past the refresh interval closes the old session
    Given an SMTP server "smtp.test.local" that accepts mail
    And an email connection pool of size 1
    When I take a connection from the pool
    And I return the connection to the pool
    And 301 seconds pass
    And I take a connection from the pool
    Then the first SMTP session was closed

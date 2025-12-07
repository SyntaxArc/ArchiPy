Feature: File Utilities

  Scenario: Generate secure file link
    Given a valid file path "/secure/files/document.pdf"
    When a secure link is created
    Then the secure link should contain a hash and expiration timestamp

  Scenario: Fail to generate secure link due to missing path
    Given an empty file path
    When a secure link creation is attempted
    Then an error message "Invalid argument provided: path" should be raised

  Scenario: Fail to generate secure link due to negative minutes
    Given a valid file path "/secure/files/document.pdf" and negative minutes
    When a secure link creation is attempted
    Then an error message "Value is out of acceptable range" should be raised

  Scenario Outline: Validate file name with allowed extensions
    Given a file name "<file_name>"
    When the file name is validated
    Then the validation should <expected_result>

    Examples:
      | file_name      | expected_result |
      | image.jpg      | succeed         |
      | picture.png    | succeed         |
      | document.pdf   | succeed         |
      | notes.txt      | succeed         |
      | script.exe     | fail            |
      | archive.zip    | fail            |

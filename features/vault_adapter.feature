@needs-vault
Feature: Vault Adapter
  As a developer
  I want to use the Vault adapter for secret and transit operations
  So that applications can manage secrets and encryption at runtime

  Background:
    Given a configured Vault adapter

  Scenario: Write and read a KV v2 secret
    When I write Vault secret "app/db" with key "password" and value "s3cret"
    Then reading Vault secret "app/db" should return key "password" with value "s3cret"

  Scenario: List and delete a KV v2 secret
    Given a Vault secret "app/listed" with key "token" and value "abc"
    When I list Vault secrets under "app"
    Then the Vault secret list should include "listed"
    When I delete Vault secret "app/listed"
    Then reading Vault secret "app/listed" should fail with NotFoundError

  Scenario: Transit encrypt and decrypt round-trip
    Given a Vault transit key named "archipy-test"
    When I encrypt plaintext "hello-vault" with transit key "archipy-test"
    Then decrypting the ciphertext with transit key "archipy-test" should return "hello-vault"

  Scenario: Cached read_secret returns stale value until write invalidates
    Given a Vault adapter with secret cache TTL 60 seconds
    And a Vault secret "app/cached" with key "v" and value "one"
    When I read Vault secret "app/cached"
    And the Vault secret "app/cached" is updated out-of-band with key "v" and value "stale"
    Then reading Vault secret "app/cached" should return key "v" with value "one"
    When I write Vault secret "app/cached" with key "v" and value "two"
    Then reading Vault secret "app/cached" should return key "v" with value "two"

  Scenario: Cached read_secret is invalidated on delete
    Given a Vault adapter with secret cache TTL 60 seconds
    And a Vault secret "app/cached-del" with key "v" and value "one"
    When I read Vault secret "app/cached-del"
    And I delete Vault secret "app/cached-del"
    Then reading Vault secret "app/cached-del" should fail with NotFoundError

  Scenario: Adapter renews token when TTL is below threshold
    Given a Vault secret "app/renew-probe" with key "ok" and value "1"
    And a Vault adapter using a renewable token with TTL 90 seconds and renew threshold 120 seconds
    When I read Vault secret "app/renew-probe"
    Then the Vault client token should still be valid
    And the token should have been renewed

  Scenario Outline: Invalid Vault adapter arguments raise InvalidArgumentError
    When I call Vault "<operation>" with invalid args
    Then a Vault InvalidArgumentError should be raised for "<argument>"

    Examples:
      | operation                              | argument    |
      | read_secret empty path                 | path        |
      | write_secret empty path                | path        |
      | write_secret empty payload             | secret      |
      | delete_secret empty path               | path        |
      | renew_lease empty id                   | lease_id    |
      | revoke_lease empty id                  | lease_id    |
      | encrypt empty key                      | key_name    |
      | encrypt empty plaintext                | plaintext   |
      | decrypt empty key                      | key_name    |
      | decrypt empty ciphertext               | ciphertext  |
      | get_dynamic_credentials empty mount    | mount_point |
      | get_dynamic_credentials empty role     | role        |

  @needs-postgres
  Scenario: Generate renew and revoke dynamic database credentials
    Given a Vault database role named "readonly" backed by Postgres
    When I generate dynamic credentials from mount "database" for role "readonly"
    Then the Vault lease should contain database credentials
    When I renew the Vault lease
    Then the renewed Vault lease should be valid
    When I revoke the Vault lease
    Then revoking the Vault lease again should fail

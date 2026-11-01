@keycloak-dtos
Feature: Keycloak DTOs

  Scenario Outline: Response DTOs keep fields Keycloak adds later
    Given a Keycloak <dto> response with an unknown field "futureField"
    Then the <dto> response keeps "futureField" in its extra fields

    Examples:
      | dto                     |
      | KeycloakRoleDTO         |
      | KeycloakGroupDTO        |
      | KeycloakUserDTO         |
      | KeycloakOrganizationDTO |
      | KeycloakClientScopeDTO  |
      | KeycloakAuthzPolicyDTO  |
      | KeycloakTokenDTO        |
      | KeycloakUserInfoDTO     |
      | KeycloakTokenClaimsDTO  |

  Scenario Outline: Request DTOs reject unknown fields
    When a Keycloak <dto> is built with an unknown field "typoField"
    Then building the <dto> fails with a validation error

    Examples:
      | dto                             |
      | KeycloakGroupRequestDTO         |
      | KeycloakUserRequestDTO          |
      | KeycloakClientScopeRequestDTO   |
      | KeycloakComponentRequestDTO     |
      | KeycloakAuthzResourceRequestDTO |
      | KeycloakUmaResourceRequestDTO   |
      | KeycloakUmaPolicyRequestDTO     |

  Scenario Outline: Request DTOs serialize to the wire names Keycloak expects
    Given a Keycloak request DTO <dto> with <attribute> set to "<value>"
    Then its payload has "<wire_name>" set to "<value>"

    Examples:
      | dto                             | attribute    | wire_name   | value  |
      | KeycloakUserRequestDTO          | first_name   | firstName   | Alice  |
      | KeycloakComponentRequestDTO     | provider_id  | providerId  | ldap   |
      | KeycloakClientScopeRequestDTO   | protocol     | protocol    | saml   |
      | KeycloakAuthzResourceRequestDTO | display_name | displayName | Report |

  Scenario Outline: Request DTOs validate both the field name and the wire name
    When I validate a Keycloak request DTO <dto> from a payload keyed by <key_style> with "<key>" set to "<value>"
    Then the validated DTO has <attribute> equal to "<value>"

    Examples:
      | dto                         | key_style  | key         | attribute   | value |
      | KeycloakUserRequestDTO      | field name | first_name  | first_name  | Alice |
      | KeycloakUserRequestDTO      | wire name  | firstName   | first_name  | Alice |
      | KeycloakComponentRequestDTO | field name | provider_id | provider_id | ldap  |
      | KeycloakComponentRequestDTO | wire name  | providerId  | provider_id | ldap  |

  Scenario Outline: Reading a response DTO like a dict warns
    Given a Keycloak KeycloakRoleDTO response with name "admin"
    When the response is read with <access>
    Then a dict-style access deprecation warning is raised
    And the value read is "admin"

    Examples:
      | access   |
      | brackets |
      | get      |

  Scenario: Empty claims are falsy
    Given a Keycloak KeycloakTokenClaimsDTO response without claims
    Then the response is falsy

  Scenario Outline: Adapter request payloads accept a DTO or a deprecated dict
    When a <kind> payload is converted for the Keycloak adapter
    Then the adapter payload is {"name": "ops"}
    And the dict deprecation warning is <warned>

    Examples:
      | kind | warned |
      | DTO  | absent |
      | dict | raised |

  Scenario Outline: Mutation responses become a typed result
    When the Keycloak mutation body <body> is converted
    Then the mutation result message is <message>
    And the mutation result extra fields are <extra>

    Examples:
      | body                    | message        | extra       |
      | an empty dict           | none           | none        |
      | empty bytes             | none           | none        |
      | a skip-exists dict      | Already exists | none        |
      | JSON bytes with a field | none           | futureField |
      | non-JSON bytes          | none           | none        |

  Scenario Outline: Each kind of mutation has its own result DTO
    When the Keycloak mutation body a skip-exists dict is converted to <result_dto>
    Then the result is a <result_dto> and a KeycloakMutationResultDTO
    And the mutation result message is Already exists

    Examples:
      | result_dto              |
      | KeycloakCreateResultDTO |
      | KeycloakUpdateResultDTO |
      | KeycloakDeleteResultDTO |
      | KeycloakAssignResultDTO |

  Scenario Outline: A create result gets the id of the new resource unless the create was skipped
    Given a Keycloak create result with message <message>
    When the id of the created resource is looked up as "new-id"
    Then the create result id is <id>
    And the lookup ran <ran>

    Examples:
      | message        | id     | ran |
      | none           | new-id | yes |
      | Already exists | none   | no  |

  Scenario Outline: Connection options reach the <client> Keycloak clients
    Given a Keycloak config with a CA bundle, a client certificate and key, a 2.5 second timeout, 4 retries, a pool of 7, a proxy and a custom header
    When the <client> adapter builds its OpenID and UMA clients
    Then every client connection uses the CA bundle, the client certificate pair, the timeout, the retries, the pool, the proxy and the header

    Examples:
      | client |
      | sync   |
      | async  |

  Scenario: A client key without a client certificate is rejected
    When a Keycloak config is built with a client key file but no client certificate
    Then building the Keycloak config fails with a validation error

  Scenario Outline: VERIFY_SSL keeps boolean spellings and treats other strings as a CA bundle path
    When a Keycloak config is built with VERIFY_SSL "<value>"
    Then the Keycloak config VERIFY_SSL is "<parsed>"

    Examples:
      | value                   | parsed                  |
      | false                   | False                   |
      | False                   | False                   |
      | 0                       | False                   |
      | true                    | True                    |
      | 1                       | True                    |
      | /etc/ssl/private-ca.pem | /etc/ssl/private-ca.pem |

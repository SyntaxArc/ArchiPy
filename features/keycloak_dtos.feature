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

  Scenario Outline: Request DTOs serialize to the wire names Keycloak expects
    Given a Keycloak request DTO <dto> with <attribute> set to "<value>"
    Then its payload has "<wire_name>" set to "<value>"

    Examples:
      | dto                             | attribute    | wire_name   | value  |
      | KeycloakUserRequestDTO          | first_name   | firstName   | Alice  |
      | KeycloakComponentRequestDTO     | provider_id  | providerId  | ldap   |
      | KeycloakClientScopeRequestDTO   | protocol     | protocol    | saml   |
      | KeycloakAuthzResourceRequestDTO | display_name | displayName | Report |

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

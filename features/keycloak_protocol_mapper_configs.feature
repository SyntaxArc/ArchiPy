@keycloak-mapper-configs
Feature: Keycloak protocol mapper config DTOs

  Scenario Outline: Every mapper config round-trips through its wire map
    Given the <mapper> config DTO with every property set to a non-default value
    When the config is serialized and parsed back
    Then the parsed config equals the original

    Examples:
      | mapper                                        |
      | oidc-allowed-origins-mapper                   |
      | oidc-audience-mapper                          |
      | oidc-audience-resolve-mapper                  |
      | oidc-acr-mapper                               |
      | oidc-amr-mapper                               |
      | oidc-claims-param-token-mapper                |
      | oidc-claims-param-value-idtoken-mapper        |
      | oidc-group-membership-mapper                  |
      | oidc-hardcoded-role-mapper                    |
      | oidc-hardcoded-claim-mapper                   |
      | oidc-nonce-backwards-compatible-mapper        |
      | oidc-organization-group-membership-mapper     |
      | oidc-organization-membership-mapper           |
      | oidc-sha256-pairwise-sub-mapper               |
      | oidc-parameterized-scope-audience-mapper      |
      | oidc-parameterized-scope-client-sub-mapper    |
      | oidc-parameterized-scope-mapper               |
      | oidc-parameterized-scope-user-property-mapper |
      | oidc-role-name-mapper                         |
      | oidc-session-state-mapper                     |
      | oidc-sub-mapper                               |
      | oidc-address-mapper                           |
      | oidc-usermodel-attribute-mapper               |
      | oidc-usermodel-client-role-mapper             |
      | oidc-usermodel-property-mapper                |
      | oidc-usermodel-realm-role-mapper              |
      | oidc-usersessionmodel-note-mapper             |
      | oidc-full-name-mapper                         |
      | oid4vc-context-mapper                         |
      | oid4vc-vc-type-mapper                         |
      | oid4vc-subject-id-mapper                      |
      | oid4vc-generated-id-mapper                    |
      | oid4vc-issued-at-time-claim-mapper            |
      | oid4vc-static-claim-mapper                    |
      | oid4vc-target-role-mapper                     |
      | oid4vc-user-attribute-mapper                  |
      | saml-audience-mapper                          |
      | saml-audience-resolve-mapper                  |
      | saml-authn-context-class-ref-mapper           |
      | saml-group-membership-mapper                  |
      | saml-hardcode-attribute-mapper                |
      | saml-hardcode-role-mapper                     |
      | saml-organization-group-membership-mapper     |
      | saml-organization-membership-mapper           |
      | saml-user-attribute-mapper                    |
      | saml-user-property-mapper                     |
      | saml-user-session-note-mapper                 |
      | saml-role-name-mapper                         |
      | saml-role-list-mapper                         |
      | saml-user-attribute-nameid-mapper             |
      | docker-v2-allow-all-mapper                    |

  Scenario Outline: Default configs match the documented defaults
    Given the <mapper> config DTO with default values
    Then the serialized config has "<property>" set to "<value>"

    Examples:
      | mapper                                    | property                   | value                                  |
      | oidc-acr-mapper                           | id.token.claim             | true                                   |
      | oidc-acr-mapper                           | access.token.claim         | true                                   |
      | oidc-acr-mapper                           | lightweight.claim          | false                                  |
      | oidc-acr-mapper                           | introspection.token.claim  | true                                   |
      | oidc-group-membership-mapper              | full.path                  | true                                   |
      | oidc-hardcoded-claim-mapper               | access.tokenResponse.claim | false                                  |
      | oidc-organization-group-membership-mapper | addGroupRoleMappings       | false                                  |
      | oidc-organization-membership-mapper       | jsonType.label             | String                                 |
      | oidc-organization-membership-mapper       | multivalued                | true                                   |
      | oidc-organization-membership-mapper       | addOrganizationAttributes  | false                                  |
      | oidc-organization-membership-mapper       | addOrganizationId          | false                                  |
      | oidc-organization-membership-mapper       | addOrganizationDomain      | false                                  |
      | oidc-address-mapper                       | user.attribute.street      | street                                 |
      | oidc-address-mapper                       | user.attribute.locality    | locality                               |
      | oidc-address-mapper                       | user.attribute.region      | region                                 |
      | oidc-address-mapper                       | user.attribute.postal_code | postal_code                            |
      | oidc-address-mapper                       | user.attribute.country     | country                                |
      | oidc-address-mapper                       | user.attribute.formatted   | formatted                              |
      | oidc-usermodel-client-role-mapper         | multivalued                | true                                   |
      | oidc-usermodel-realm-role-mapper          | multivalued                | true                                   |
      | oidc-usersessionmodel-note-mapper         | access.tokenResponse.claim | false                                  |
      | oidc-full-name-mapper                     | id.token.claim             | true                                   |
      | oidc-full-name-mapper                     | access.token.claim         | true                                   |
      | oidc-full-name-mapper                     | lightweight.claim          | false                                  |
      | oidc-full-name-mapper                     | userinfo.token.claim       | true                                   |
      | oidc-full-name-mapper                     | introspection.token.claim  | true                                   |
      | oid4vc-context-mapper                     | context                    | https://www.w3.org/2018/credentials/v1 |
      | oid4vc-context-mapper                     | vc.mandatory               | false                                  |
      | oid4vc-vc-type-mapper                     | vc.mandatory               | false                                  |
      | oid4vc-subject-id-mapper                  | claim.name                 | id                                     |
      | oid4vc-subject-id-mapper                  | userAttribute              | username                               |
      | oid4vc-subject-id-mapper                  | vc.mandatory               | false                                  |
      | oid4vc-generated-id-mapper                | claim.name                 | id                                     |
      | oid4vc-generated-id-mapper                | vc.mandatory               | false                                  |
      | oid4vc-issued-at-time-claim-mapper        | claim.name                 | iat                                    |
      | oid4vc-issued-at-time-claim-mapper        | valueSource                | COMPUTE                                |
      | oid4vc-issued-at-time-claim-mapper        | vc.mandatory               | false                                  |
      | oid4vc-static-claim-mapper                | vc.mandatory               | false                                  |
      | oid4vc-target-role-mapper                 | clientId                   | roles                                  |
      | oid4vc-target-role-mapper                 | vc.mandatory               | false                                  |
      | oid4vc-user-attribute-mapper              | vc.mandatory               | false                                  |
      | saml-group-membership-mapper              | attribute.name             | member                                 |
      | saml-group-membership-mapper              | single                     | true                                   |
      | saml-group-membership-mapper              | full.path                  | true                                   |
      | saml-organization-group-membership-mapper | addGroupRoleMappings       | false                                  |
      | saml-role-list-mapper                     | attribute.name             | Role                                   |
      | saml-role-list-mapper                     | single                     | true                                   |

  Scenario Outline: Config DTOs reject unknown fields
    When the <mapper> config DTO is built with an unknown field "typoField"
    Then the config DTO build is rejected as invalid

    Examples:
      | mapper                                        |
      | oidc-allowed-origins-mapper                   |
      | oidc-audience-mapper                          |
      | oidc-audience-resolve-mapper                  |
      | oidc-acr-mapper                               |
      | oidc-amr-mapper                               |
      | oidc-claims-param-token-mapper                |
      | oidc-claims-param-value-idtoken-mapper        |
      | oidc-group-membership-mapper                  |
      | oidc-hardcoded-role-mapper                    |
      | oidc-hardcoded-claim-mapper                   |
      | oidc-nonce-backwards-compatible-mapper        |
      | oidc-organization-group-membership-mapper     |
      | oidc-organization-membership-mapper           |
      | oidc-sha256-pairwise-sub-mapper               |
      | oidc-parameterized-scope-audience-mapper      |
      | oidc-parameterized-scope-client-sub-mapper    |
      | oidc-parameterized-scope-mapper               |
      | oidc-parameterized-scope-user-property-mapper |
      | oidc-role-name-mapper                         |
      | oidc-session-state-mapper                     |
      | oidc-sub-mapper                               |
      | oidc-address-mapper                           |
      | oidc-usermodel-attribute-mapper               |
      | oidc-usermodel-client-role-mapper             |
      | oidc-usermodel-property-mapper                |
      | oidc-usermodel-realm-role-mapper              |
      | oidc-usersessionmodel-note-mapper             |
      | oidc-full-name-mapper                         |
      | oid4vc-context-mapper                         |
      | oid4vc-vc-type-mapper                         |
      | oid4vc-subject-id-mapper                      |
      | oid4vc-generated-id-mapper                    |
      | oid4vc-issued-at-time-claim-mapper            |
      | oid4vc-static-claim-mapper                    |
      | oid4vc-target-role-mapper                     |
      | oid4vc-user-attribute-mapper                  |
      | saml-audience-mapper                          |
      | saml-audience-resolve-mapper                  |
      | saml-authn-context-class-ref-mapper           |
      | saml-group-membership-mapper                  |
      | saml-hardcode-attribute-mapper                |
      | saml-hardcode-role-mapper                     |
      | saml-organization-group-membership-mapper     |
      | saml-organization-membership-mapper           |
      | saml-user-attribute-mapper                    |
      | saml-user-property-mapper                     |
      | saml-user-session-note-mapper                 |
      | saml-role-name-mapper                         |
      | saml-role-list-mapper                         |
      | saml-user-attribute-nameid-mapper             |
      | docker-v2-allow-all-mapper                    |

  Scenario Outline: A config DTO builds the protocol mapper request
    Given the <mapper> config DTO with default values
    When a mapper named "my-mapper" is built from the config
    Then the mapper request has protocol "<protocol>" and protocol mapper "<mapper>"
    And the mapper request config equals the serialized config

    Examples:
      | mapper                                        | protocol       |
      | oidc-allowed-origins-mapper                   | openid-connect |
      | oidc-audience-mapper                          | openid-connect |
      | oidc-audience-resolve-mapper                  | openid-connect |
      | oidc-acr-mapper                               | openid-connect |
      | oidc-amr-mapper                               | openid-connect |
      | oidc-claims-param-token-mapper                | openid-connect |
      | oidc-claims-param-value-idtoken-mapper        | openid-connect |
      | oidc-group-membership-mapper                  | openid-connect |
      | oidc-hardcoded-role-mapper                    | openid-connect |
      | oidc-hardcoded-claim-mapper                   | openid-connect |
      | oidc-nonce-backwards-compatible-mapper        | openid-connect |
      | oidc-organization-group-membership-mapper     | openid-connect |
      | oidc-organization-membership-mapper           | openid-connect |
      | oidc-sha256-pairwise-sub-mapper               | openid-connect |
      | oidc-parameterized-scope-audience-mapper      | openid-connect |
      | oidc-parameterized-scope-client-sub-mapper    | openid-connect |
      | oidc-parameterized-scope-mapper               | openid-connect |
      | oidc-parameterized-scope-user-property-mapper | openid-connect |
      | oidc-role-name-mapper                         | openid-connect |
      | oidc-session-state-mapper                     | openid-connect |
      | oidc-sub-mapper                               | openid-connect |
      | oidc-address-mapper                           | openid-connect |
      | oidc-usermodel-attribute-mapper               | openid-connect |
      | oidc-usermodel-client-role-mapper             | openid-connect |
      | oidc-usermodel-property-mapper                | openid-connect |
      | oidc-usermodel-realm-role-mapper              | openid-connect |
      | oidc-usersessionmodel-note-mapper             | openid-connect |
      | oidc-full-name-mapper                         | openid-connect |
      | oid4vc-context-mapper                         | oid4vc         |
      | oid4vc-vc-type-mapper                         | oid4vc         |
      | oid4vc-subject-id-mapper                      | oid4vc         |
      | oid4vc-generated-id-mapper                    | oid4vc         |
      | oid4vc-issued-at-time-claim-mapper            | oid4vc         |
      | oid4vc-static-claim-mapper                    | oid4vc         |
      | oid4vc-target-role-mapper                     | oid4vc         |
      | oid4vc-user-attribute-mapper                  | oid4vc         |
      | saml-audience-mapper                          | saml           |
      | saml-audience-resolve-mapper                  | saml           |
      | saml-authn-context-class-ref-mapper           | saml           |
      | saml-group-membership-mapper                  | saml           |
      | saml-hardcode-attribute-mapper                | saml           |
      | saml-hardcode-role-mapper                     | saml           |
      | saml-organization-group-membership-mapper     | saml           |
      | saml-organization-membership-mapper           | saml           |
      | saml-user-attribute-mapper                    | saml           |
      | saml-user-property-mapper                     | saml           |
      | saml-user-session-note-mapper                 | saml           |
      | saml-role-name-mapper                         | saml           |
      | saml-role-list-mapper                         | saml           |
      | saml-user-attribute-nameid-mapper             | saml           |
      | docker-v2-allow-all-mapper                    | docker-v2      |

  Scenario Outline: Booleans travel as lowercase strings
    Given the oidc-audience-mapper config DTO with <attribute> set to <value>
    Then the serialized config has "<wire_name>" set to "<wire_value>"

    Examples:
      | attribute                 | value | wire_name                 | wire_value |
      | id_token_claim            | True  | id.token.claim            | true       |
      | access_token_claim        | False | access.token.claim        | false      |
      | introspection_token_claim | False | introspection.token.claim | false      |

  Scenario Outline: Unset properties are omitted from the wire map
    Given the <mapper> config DTO with default values
    Then the serialized config has no "<property>" key

    Examples:
      | mapper                          | property                 |
      | oidc-audience-mapper            | included.client.audience |
      | oidc-hardcoded-claim-mapper     | claim.name               |
      | oidc-usermodel-attribute-mapper | multivalued              |
      | saml-user-attribute-mapper      | aggregate.attrs          |

  Scenario Outline: Wire maps are parsed into the typed config
    When the wire config <config> of <mapper> is parsed
    Then the parsed config has <attribute> equal to "<value>"

    Examples:
      | mapper                       | config                                           | attribute                | value     |
      | oidc-audience-mapper         | included.client.audience=my-client,unknown.key=x | included_client_audience | my-client |
      | oidc-audience-mapper         | id.token.claim=true                              | id_token_claim           | True      |
      | oidc-audience-mapper         | access.token.claim=false                         | access_token_claim       | False     |
      | saml-group-membership-mapper | single=false,attribute.name=groups               | single                   | False     |
      | saml-group-membership-mapper | single=false,attribute.name=groups               | attribute_name           | groups    |

  Scenario Outline: Unknown mapper ids are not parsed
    When the wire config a=b of <mapper> is parsed
    Then no typed config is returned

    Examples:
      | mapper              |
      | oidc-made-up-mapper |
      | custom-spi-mapper   |

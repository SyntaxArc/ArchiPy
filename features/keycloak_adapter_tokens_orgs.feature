# features/keycloak_adapter_tokens_orgs.feature
@needs-keycloak @needs-envoy @needs-otel-collector
Feature: Keycloak Tokens, Organizations and Role Management Testing
  As a developer
  I want to test Keycloak authentication operations
  So that I can ensure secure authentication and management operations

  @tokens
  Scenario Outline: Token introspection
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    And I have a valid token for "<username>" with password "<password>" using <adapter_type> adapter
    When I introspect the token using <adapter_type> adapter
    Then the <adapter_type> token introspection should succeed
    And the introspection result should indicate active token

    Examples:
      | adapter_type | username  | password | realm_name             | realm_display_name | client_name       | via    |
      | sync         | testuser  | pass123  | test-realm             | Test Realm         | test-client       | direct |
      | async        | asyncuser | async123 | async-test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | testuser  | pass123  | test-realm-envoy       | Test Realm         | test-client       | envoy  |
      | async        | asyncuser | async123 | async-test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @tokens
  Scenario Outline: Token info retrieval
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    And I have a valid token for "<username>" with password "<password>" using <adapter_type> adapter
    When I get token info using <adapter_type> adapter
    Then the <adapter_type> token info request should succeed
    And the token info should contain user claims

    Examples:
      | adapter_type | username  | password | realm_name             | realm_display_name | client_name       | via    |
      | sync         | testuser  | pass123  | test-realm             | Test Realm         | test-client       | direct |
      | async        | asyncuser | async123 | async-test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | testuser  | pass123  | test-realm-envoy       | Test Realm         | test-client       | envoy  |
      | async        | asyncuser | async123 | async-test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @roles
  Scenario Outline: Role permission checking
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    And I create a realm role named "<role_name>" with description "<role_description>" using <adapter_type> adapter
    And I assign realm role "<role_name>" to user "<username>" using <adapter_type> adapter
    And I have a valid token for "<username>" with password "<password>" using <adapter_type> adapter
    When I check if user has role "<role_name>" using <adapter_type> adapter
    Then the <adapter_type> role check should succeed
    And the user should have the role "<role_name>"

    Examples:
      | adapter_type | username  | password | role_name       | role_description | realm_name             | realm_display_name | client_name       | via    |
      | sync         | testuser  | pass123  | test-role       | Test Role        | test-realm             | Test Realm         | test-client       | direct |
      | async        | asyncuser | async123 | async-test-role | Async Test Role  | async-test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | testuser  | pass123  | test-role       | Test Role        | test-realm-envoy       | Test Realm         | test-client       | envoy  |
      | async        | asyncuser | async123 | async-test-role | Async Test Role  | async-test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @roles
  Scenario Outline: Role removal operations
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    And I create a realm role named "<role_name>" with description "<role_description>" using <adapter_type> adapter
    And I assign realm role "<role_name>" to user "<username>" using <adapter_type> adapter
    When I remove realm role "<role_name>" from user "<username>" using <adapter_type> adapter
    Then the <adapter_type> role removal should succeed
    And the user "<username>" should not have realm role "<role_name>"

    Examples:
      | adapter_type | username  | password | role_name       | role_description | realm_name             | realm_display_name | client_name       | via    |
      | sync         | testuser  | pass123  | test-role       | Test Role        | test-realm             | Test Realm         | test-client       | direct |
      | async        | asyncuser | async123 | async-test-role | Async Test Role  | async-test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | testuser  | pass123  | test-role       | Test Role        | test-realm-envoy       | Test Realm         | test-client       | envoy  |
      | async        | asyncuser | async123 | async-test-role | Async Test Role  | async-test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @users
  Scenario Outline: User deletion operations
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    When I delete user "<username>" using <adapter_type> adapter
    Then the <adapter_type> user deletion should succeed
    And the user "<username>" should not exist

    Examples:
      | adapter_type | username   | password | realm_name             | realm_display_name | client_name       | via    |
      | sync         | testuser   | pass123  | test-realm             | Test Realm         | test-client       | direct |
      | async        | asyncuser6 | async123 | async-test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | testuser   | pass123  | test-realm-envoy       | Test Realm         | test-client       | envoy  |
      | async        | asyncuser6 | async123 | async-test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @organizations
  Scenario Outline: Organization create get update and delete
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I enable organization of realm named "<realm_name>"
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    When I create an organization with name "<org_name>" and alias "<org_alias>" using <adapter_type> adapter
    Then the <adapter_type> organization creation should succeed
    And the organization "<org_name>" should exist
    And the organization should have alias "<org_alias>"
    When I get all organizations using <adapter_type> adapter
    Then the organizations list should contain organization "<org_name>"
    When I get organizations with search "<org_name>" using <adapter_type> adapter
    Then the organizations list should contain organization "<org_name>"
    When I update the organization name to "<org_display_name>" using <adapter_type> adapter
    Then the <adapter_type> organization update should succeed
    And the organization should have name "<org_display_name>"
    When I delete the organization using <adapter_type> adapter
    Then the <adapter_type> organization deletion should succeed

    Examples:
      | adapter_type | org_name       | org_alias       | org_display_name  | realm_name       | realm_display_name | client_name       | via    |
      | sync         | test-org       | test-org-alias  | Test Org Display  | test-realm       | Test Realm         | test-client       | direct |
      | async        | async-test-org | async-org-alias | Async Org Display | test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | test-org       | test-org-alias  | Test Org Display  | test-realm-envoy | Test Realm         | test-client       | envoy  |
      | async        | async-test-org | async-org-alias | Async Org Display | test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @organizations
  Scenario Outline: Organization members add and remove
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I enable organization of realm named "<realm_name>"
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    And I create an organization with name "<org_name>" and alias "<org_alias>" using <adapter_type> adapter
    When I add user "<username>" to the organization using <adapter_type> adapter
    Then the <adapter_type> organization add member should succeed
    When I get organization members using <adapter_type> adapter
    Then the organization should have 1 member
    When I get organizations for user "<username>" using <adapter_type> adapter
    Then the user organizations list should contain organization "<org_name>"
    When I remove user "<username>" from the organization using <adapter_type> adapter
    Then the <adapter_type> organization remove member should succeed
    When I get organization members count using <adapter_type> adapter
    Then the organization members count should be 0
    When I get organizations for user "<username>" using <adapter_type> adapter
    Then the user organizations list should not contain organization "<org_name>"

    Examples:
      | adapter_type | username     | password | org_name   | org_alias    | realm_name       | realm_display_name | client_name       | via    |
      | sync         | orguser      | pass123  | test-org1  | test-alias1  | test-realm       | Test Realm         | test-client       | direct |
      | async        | asyncorguser | async123 | async-org1 | async-alias1 | test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | orguser      | pass123  | test-org1  | test-alias1  | test-realm-envoy | Test Realm         | test-client       | envoy  |
      | async        | asyncorguser | async123 | async-org1 | async-alias1 | test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @organizations
  Scenario Outline: Organization identity providers, counts, members and invitations
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I enable organization of realm named "<realm_name>"
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    And I create an organization with name "<org_name>" and alias "<org_alias>" using <adapter_type> adapter
    When I create the identity provider "<idp_alias>" using <adapter_type> adapter
    And I link the identity provider "<idp_alias>" to the organization using <adapter_type> adapter
    Then the organization lists the identity provider "<idp_alias>" and returns it by alias using <adapter_type> adapter
    When I enable auto membership for the identity provider "<idp_alias>" of the organization using <adapter_type> adapter
    And I unlink the identity provider "<idp_alias>" from the organization using <adapter_type> adapter
    Then the organization no longer lists the identity provider "<idp_alias>" using <adapter_type> adapter
    And the organization count includes the organization and a search for it counts 1 using <adapter_type> adapter
    When I add user "<username>" to the organization using <adapter_type> adapter
    Then the organization returns member "<username>" by id and accepts a membership type change using <adapter_type> adapter
    And the organization has no invitations and an unknown invitation is not found using <adapter_type> adapter

    Examples:
      | adapter_type | username       | password | org_name   | org_alias    | idp_alias | realm_name       | realm_display_name | client_name       | via    |
      | sync         | orgextrauser   | pass123  | extra-org  | extra-alias  | ext-idp   | test-realm       | Test Realm         | test-client       | direct |
      | async        | asyncextrauser | async123 | aextra-org | aextra-alias | aext-idp  | test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | orgextrauser   | pass123  | extra-org  | extra-alias  | ext-idp   | test-realm-envoy | Test Realm         | test-client       | envoy  |
      | async        | asyncextrauser | async123 | aextra-org | aextra-alias | aext-idp  | test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @organizations
  Scenario Outline: Organization groups, group members and role mappings
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I enable organization of realm named "<realm_name>"
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    And I create an organization with name "<org_name>" and alias "<org_alias>" using <adapter_type> adapter
    When I create the organization group "<group_name>" and the subgroup "<child_name>" using <adapter_type> adapter
    Then the organization groups report their ids and are found by path, list and children using <adapter_type> adapter
    When I add user "<username>" to the organization using <adapter_type> adapter
    And I add user "<username>" to the organization group and assign realm role "offline_access" using <adapter_type> adapter
    Then the organization group lists member "<username>" and role "offline_access" in every role view using <adapter_type> adapter
    When I remove the role and the member, then update and delete the organization group using <adapter_type> adapter
    Then the organization group was renamed, emptied and no longer exists using <adapter_type> adapter

    Examples:
      | adapter_type | username      | password | org_name | org_alias  | group_name | child_name | realm_name       | realm_display_name | client_name       | via    |
      | sync         | orggroupuser  | pass123  | grp-org  | grp-alias  | team       | team-sub   | test-realm       | Test Realm         | test-client       | direct |
      | async        | aorggroupuser | async123 | agrp-org | agrp-alias | ateam      | ateam-sub  | test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | orggroupuser  | pass123  | grp-org  | grp-alias  | team       | team-sub   | test-realm-envoy | Test Realm         | test-client       | envoy  |
      | async        | aorggroupuser | async123 | agrp-org | agrp-alias | ateam      | ateam-sub  | test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @roles
  Scenario Outline: Roles addressed by id with composites and management permissions
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a realm role named "<role>" with description "Parent" using <adapter_type> adapter
    And I create a realm role named "<child>" with description "Child" using <adapter_type> adapter
    When I update the role "<role>" by its id and add "<child>" as a composite using <adapter_type> adapter
    Then the role "<role>" by id has description "updated" and lists "<child>" as composite using <adapter_type> adapter
    And the management permissions of the role "<role>" by id are readable or report the disabled feature using <adapter_type> adapter
    When I remove "<child>" from the composite "<role>" and delete the role "<role>" by its id using <adapter_type> adapter
    Then the composite was removed and the role no longer exists by id using <adapter_type> adapter

    Examples:
      | adapter_type | role         | child       | realm_name       | realm_display_name | client_name       | via    |
      | sync         | parent-role  | child-role  | test-realm       | Test Realm         | test-client       | direct |
      | async        | aparent-role | achild-role | test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | parent-role  | child-role  | test-realm-envoy | Test Realm         | test-client       | envoy  |
      | async        | aparent-role | achild-role | test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @roles
  Scenario Outline: Role mappings of users and groups and scope mappings of clients and client scopes
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    When I create the realm role "<realm_role>" and the client role "<client_role>" of client "<client_name>" using <adapter_type> adapter
    Then the user "<username>" gets, lists and loses the realm and client roles through role mappings using <adapter_type> adapter
    And the group "<group>" lists the role mappings it lacked before using <adapter_type> adapter
    And the client scope "<scope>" and the client map scopes to the realm and client roles using <adapter_type> adapter

    Examples:
      | adapter_type | username     | password | realm_role | client_role | group      | scope      | realm_name       | realm_display_name | client_name | via    |
      | sync         | mapuser      | pass123  | map-rrole  | map-crole   | map-group  | map-scope  | test-realm       | Test Realm         | map-client  | direct |
      | async        | asyncmapuser | async123 | amap-rrole | amap-crole  | amap-group | amap-scope | test-realm       | Async Test Realm   | amap-client | direct |
      | sync         | mapuser      | pass123  | map-rrole  | map-crole   | map-group  | map-scope  | test-realm-envoy | Test Realm         | map-client  | envoy  |
      | async        | asyncmapuser | async123 | amap-rrole | amap-crole  | amap-group | amap-scope | test-realm-envoy | Async Test Realm   | amap-client | envoy  |

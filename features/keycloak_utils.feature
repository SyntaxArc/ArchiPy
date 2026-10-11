Feature: Keycloak utilities authentication decorators

  Background:
    Given a keycloak utils stub adapter is installed
    And the keycloak utils stub accepts token "good-token" for user "user-1" with realm roles "reader"

  Scenario Outline: FastAPI dependency populates request state for a valid token
    Given the keycloak utils fastapi auth requires any of roles "reader,writer"
    When the keycloak utils <mode> fastapi dependency is called with token "good-token"
    Then the keycloak utils dependency returns user info with subject "user-1"
    And the keycloak utils request state has user roles "reader"
    And the keycloak utils request state has an empty actor chain

    Examples:
      | mode  |
      | sync  |
      | async |

  Scenario Outline: FastAPI dependency accepts a client role from resource access
    Given the keycloak utils stub token "good-token" has client role "operator"
    And the keycloak utils fastapi auth requires all roles "reader,operator"
    When the keycloak utils <mode> fastapi dependency is called with token "good-token"
    Then the keycloak utils request state has user roles "operator,reader"

    Examples:
      | mode  |
      | sync  |
      | async |

  Scenario Outline: FastAPI dependency rejects missing credentials
    When the keycloak utils <mode> fastapi dependency is called without credentials
    Then the keycloak utils call fails with error code "UNAUTHENTICATED"

    Examples:
      | mode  |
      | sync  |
      | async |

  Scenario Outline: FastAPI dependency rejects a token that fails validation
    Given the keycloak utils stub treats token "bad-token" as invalid
    When the keycloak utils <mode> fastapi dependency is called with token "bad-token"
    Then the keycloak utils call fails with error code "TOKEN_EXPIRED"

    Examples:
      | mode  |
      | sync  |
      | async |

  Scenario Outline: FastAPI dependency rejects a token whose claims cannot be read
    Given the keycloak utils stub has no token info for token "good-token"
    When the keycloak utils <mode> fastapi dependency is called with token "good-token"
    Then the keycloak utils call fails with error code "TOKEN_EXPIRED"

    Examples:
      | mode  |
      | sync  |
      | async |

  Scenario Outline: FastAPI dependency rejects a token without userinfo
    Given the keycloak utils stub has no userinfo for token "good-token"
    When the keycloak utils <mode> fastapi dependency is called with token "good-token"
    Then the keycloak utils call fails with error code "UNAUTHENTICATED"

    Examples:
      | mode  |
      | sync  |
      | async |

  Scenario Outline: FastAPI dependency rejects a caller without the required role
    Given the keycloak utils fastapi auth requires any of roles "admin"
    When the keycloak utils <mode> fastapi dependency is called with token "good-token"
    Then the keycloak utils call fails with error code "PERMISSION_DENIED"
    And the keycloak utils error lists required roles "admin"

    Examples:
      | mode  |
      | sync  |
      | async |

  Scenario Outline: FastAPI dependency requires every role when all roles are required
    Given the keycloak utils fastapi auth requires all roles "reader,writer"
    When the keycloak utils <mode> fastapi dependency is called with token "good-token"
    Then the keycloak utils call fails with error code "PERMISSION_DENIED"

    Examples:
      | mode  |
      | sync  |
      | async |

  Scenario Outline: FastAPI dependency enforces UMA permissions
    Given the keycloak utils fastapi auth requires permissions "doc#read,doc#write"
    And the keycloak utils stub grants permissions "doc#read" to token "good-token"
    When the keycloak utils <mode> fastapi dependency is called with token "good-token"
    Then the keycloak utils call fails with error code "PERMISSION_DENIED"
    And the keycloak utils error lists missing permission "doc#write"

    Examples:
      | mode  |
      | sync  |
      | async |

  Scenario Outline: FastAPI dependency allows the owner of a resource
    Given the keycloak utils fastapi auth guards resource type "users" by path parameter "user_uuid"
    And the keycloak utils request path parameter "user_uuid" is "user-1"
    When the keycloak utils <mode> fastapi dependency is called with token "good-token"
    Then the keycloak utils dependency returns user info with subject "user-1"

    Examples:
      | mode  |
      | sync  |
      | async |

  Scenario Outline: FastAPI dependency denies a non owner of a resource
    Given the keycloak utils fastapi auth guards resource type "users" by path parameter "user_uuid"
    And the keycloak utils request path parameter "user_uuid" is "user-2"
    When the keycloak utils <mode> fastapi dependency is called with token "good-token"
    Then the keycloak utils call fails with error code "PERMISSION_DENIED"

    Examples:
      | mode  |
      | sync  |
      | async |

  Scenario Outline: FastAPI dependency lets an admin role bypass resource ownership
    Given the keycloak utils fastapi auth guards resource type "users" by path parameter "user_uuid"
    And the keycloak utils fastapi auth treats roles "reader" as admin roles
    And the keycloak utils request path parameter "user_uuid" is "user-2"
    When the keycloak utils <mode> fastapi dependency is called with token "good-token"
    Then the keycloak utils dependency returns user info with subject "user-1"

    Examples:
      | mode  |
      | sync  |
      | async |

  Scenario Outline: FastAPI dependency rejects a request missing the resource path parameter
    Given the keycloak utils fastapi auth guards resource type "users" by path parameter "user_uuid"
    When the keycloak utils <mode> fastapi dependency is called with token "good-token"
    Then the keycloak utils call fails with error code "INVALID_ARGUMENT"

    Examples:
      | mode  |
      | sync  |
      | async |

  Scenario Outline: FastAPI dependency exposes the delegated actor chain
    Given the keycloak utils stub token "good-token" carries actor chain "user:admin-1,client:agent-app"
    When the keycloak utils <mode> fastapi dependency is called with token "good-token"
    Then the keycloak utils request state actor chain is "USER:admin-1,CLIENT:agent-app"

    Examples:
      | mode  |
      | sync  |
      | async |

  Scenario Outline: gRPC handler runs with the auth context for a valid token
    Given the keycloak utils grpc auth requires any of roles "reader"
    When the keycloak utils <mode> grpc handler is invoked with bearer token "good-token"
    Then the keycloak utils grpc handler ran with user "user-1" and roles "reader"
    And the keycloak utils grpc handler returned "handled"
    And the keycloak utils auth context is cleared

    Examples:
      | mode  |
      | sync  |
      | async |

  Scenario Outline: gRPC handler accepts a raw token without the bearer prefix
    When the keycloak utils <mode> grpc handler is invoked with metadata key "authorization" value "good-token"
    Then the keycloak utils grpc handler ran with user "user-1" and roles "reader"

    Examples:
      | mode  |
      | sync  |
      | async |

  Scenario Outline: gRPC handler aborts the servicer context when the token is missing
    When the keycloak utils <mode> grpc handler is invoked without metadata
    Then the keycloak utils servicer context was aborted with status "UNAUTHENTICATED"
    And the keycloak utils grpc handler did not run
    And the keycloak utils auth context is cleared

    Examples:
      | mode  |
      | sync  |
      | async |

  Scenario Outline: gRPC handler aborts the servicer context when the token is invalid
    Given the keycloak utils stub treats token "bad-token" as invalid
    When the keycloak utils <mode> grpc handler is invoked with bearer token "bad-token"
    Then the keycloak utils servicer context was aborted with status "UNAUTHENTICATED"
    And the keycloak utils grpc handler did not run

    Examples:
      | mode  |
      | sync  |
      | async |

  Scenario Outline: gRPC handler aborts the servicer context when the role is insufficient
    Given the keycloak utils grpc auth requires any of roles "admin"
    When the keycloak utils <mode> grpc handler is invoked with bearer token "good-token"
    Then the keycloak utils servicer context was aborted with status "PERMISSION_DENIED"
    And the keycloak utils grpc handler did not run
    And the keycloak utils auth context is cleared

    Examples:
      | mode  |
      | sync  |
      | async |

  Scenario Outline: gRPC handler aborts when the request lacks the resource attribute
    Given the keycloak utils grpc auth reads the resource from request attribute "user_id"
    When the keycloak utils <mode> grpc handler is invoked with bearer token "good-token"
    Then the keycloak utils servicer context was aborted with status "INVALID_ARGUMENT"

    Examples:
      | mode  |
      | sync  |
      | async |

  Scenario Outline: gRPC handler raises the typed error when the context is not a servicer context
    When the keycloak utils <mode> grpc handler is invoked without metadata on a plain context
    Then the keycloak utils call fails with error code "UNAUTHENTICATED"
    And the keycloak utils grpc handler did not run

    Examples:
      | mode  |
      | sync  |
      | async |

  Scenario: Sync gRPC handler wraps unexpected failures in an internal error
    Given the keycloak utils grpc handler crashes with a runtime failure
    When the keycloak utils sync grpc handler is invoked with bearer token "good-token" on a plain context
    Then the keycloak utils call fails with error code "INTERNAL_ERROR"
    And the keycloak utils auth context is cleared

  Scenario: Async gRPC handler aborts with an internal status on unexpected failures
    Given the keycloak utils grpc handler crashes with a runtime failure
    When the keycloak utils async grpc handler is invoked with bearer token "good-token"
    Then the keycloak utils servicer context was aborted with status "INTERNAL"
    And the keycloak utils auth context is cleared

  Scenario: Auth context manager stores and returns the context
    Given no keycloak utils auth context is set
    When the keycloak utils auth context is set for user "user-9"
    Then the keycloak utils auth context belongs to user "user-9"

  Scenario: Auth context manager clears the context
    Given the keycloak utils auth context is set for user "user-9"
    When the keycloak utils auth context is cleared by the manager
    Then the keycloak utils auth context is cleared

  Scenario: Auth context manager returns nothing when no context was set
    Given no keycloak utils auth context is set
    Then the keycloak utils auth context is cleared

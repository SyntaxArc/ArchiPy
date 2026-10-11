Feature: Deprecation Decorators
  As a library maintainer
  I want to mark methods and classes as deprecated
  So that callers are warned or blocked when they use them

  Scenario: Deprecated method warns with the default message and still runs
    Given a method decorated with method_deprecation_warning without a message
    When the deprecated-warning method is called
    Then the deprecation result is "old-result"
    And exactly one DeprecationWarning was emitted
    And the deprecation warning text is "This method is deprecated and will be removed in a future version."
    And the deprecation warning points at the calling code

  Scenario: Deprecated method warns with a custom message
    Given a method decorated with method_deprecation_warning with message "use new_method instead"
    When the deprecated-warning method is called
    Then the deprecation result is "old-result"
    And exactly one DeprecationWarning was emitted
    And the deprecation warning text is "use new_method instead"

  Scenario: Deprecated method warns on every call
    Given a method decorated with method_deprecation_warning without a message
    When the deprecated-warning method is called 3 times
    Then 3 DeprecationWarnings were emitted

  Scenario: Deprecated class warns with the default message on instantiation
    Given a class decorated with class_deprecation_warning without a message
    When the deprecated-warning class is instantiated with value 42
    Then the deprecated-warning instance holds value 42
    And exactly one DeprecationWarning was emitted
    And the deprecation warning text is "This class is deprecated and will be removed in a future version."
    And the deprecation warning points at the calling code

  Scenario: Deprecated class warns with a custom message
    Given a class decorated with class_deprecation_warning with message "use NewClass instead"
    When the deprecated-warning class is instantiated with value 1
    Then exactly one DeprecationWarning was emitted
    And the deprecation warning text is "use NewClass instead"

  Scenario: Deprecated method raises DeprecationError in English by default
    Given a method decorated with method_deprecation_error without arguments
    When the deprecated-error method is called
    Then the deprecated-error method body did not run
    And a DeprecationError is raised
    And the deprecation error code is "DEPRECATED_FEATURE"
    And the deprecation error names feature "legacy_method"
    And the deprecation error message is "This feature is deprecated and should no longer be used"

  Scenario: Deprecated method raises DeprecationError with custom operation and language
    Given a method decorated with method_deprecation_error with operation "OldApi.call" and language FA
    When the deprecated-error method is called
    Then a DeprecationError is raised
    And the deprecation error names feature "OldApi.call"
    And the deprecation error message is "این ویژگی منسوخ شده و دیگر نباید استفاده شود"

  Scenario: Deprecated class raises DeprecationError in Persian by default
    Given a class decorated with class_deprecation_error without arguments
    When the deprecated-error class is instantiated
    Then a DeprecationError is raised
    And the deprecation error names feature "LegacyClass"
    And the deprecation error message is "این ویژگی منسوخ شده و دیگر نباید استفاده شود"

  Scenario: Deprecated class raises DeprecationError with custom operation and language
    Given a class decorated with class_deprecation_error with operation "OldThing" and language EN
    When the deprecated-error class is instantiated
    Then a DeprecationError is raised
    And the deprecation error names feature "OldThing"
    And the deprecation error message is "This feature is deprecated and should no longer be used"

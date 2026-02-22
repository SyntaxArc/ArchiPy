Feature: Type-Safe Field Name References for DTOs

  Scenario: FieldStr class attributes exist on BaseDTO subclasses
    Given a DTO subclass with fields "name" and "email"
    When I access the field names as class attributes
    Then each attribute should be a FieldStr instance
    And each attribute value should match its field name

  Scenario: Instance attribute access returns actual values
    Given a DTO subclass with fields "name" and "email"
    When I create an instance with name "Alice" and email "alice@example.com"
    Then instance attribute "name" should return "Alice"
    And instance attribute "email" should return "alice@example.com"
    And class attribute "name" should still return FieldStr "name"

  Scenario: FieldStr works as dictionary key
    Given a DTO subclass with fields "name" and "email"
    When I use a FieldStr class attribute as a dictionary key
    Then the dictionary should be accessible with the equivalent plain string

  Scenario: FieldStr works in string comparisons
    Given a DTO subclass with fields "name" and "email"
    When I compare the FieldStr class attribute to a plain string
    Then the comparison should return true for matching strings
    And the comparison should return false for non-matching strings

  Scenario: Inherited DTOs get FieldStr attributes
    Given a parent DTO with field "base_field" and a child DTO with field "child_field"
    When I access field names on the child class
    Then the child should have FieldStr for "base_field"
    And the child should have FieldStr for "child_field"

  Scenario: Existing PaginationDTO has FieldStr attributes
    Given the PaginationDTO class
    When I access its field name class attributes
    Then "page" should be a FieldStr with value "page"
    And "page_size" should be a FieldStr with value "page_size"

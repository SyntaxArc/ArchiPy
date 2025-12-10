Feature: TTL Cache Decorator
  As a developer
  I want to cache function results with TTL expiration
  So that I can improve performance by avoiding redundant computations

  Scenario: Basic function caching
    Given a function decorated with ttl_cache_decorator
    When I call the function with argument 5
    Then the function should be executed
    And the result should be 10
    When I call the function again with argument 5
    Then the function should not be executed again
    And the result should be 10

  Scenario: Different arguments create separate cache entries
    Given a function decorated with ttl_cache_decorator
    When I call the function with argument 5
    Then the function should be executed
    When I call the function with argument 10
    Then the function should be executed
    And the execution count should be 2

  Scenario: Cache expiration after TTL
    Given a function decorated with ttl_cache_decorator with TTL 2 seconds
    When I call the function with argument 5
    Then the function should be executed
    When I wait for 3 seconds
    And I call the function with argument 5
    Then the function should be executed again
    And the execution count should be 2

  Scenario: Cache respects maxsize limit
    Given a function decorated with ttl_cache_decorator with maxsize 3
    When I call the function with arguments 1, 2, 3, 4
    Then the execution count should be 4
    When I call the function with argument 1
    Then the function should be executed again
    And the execution count should be 5

  Scenario: Instance method caching
    Given a class with a cached method
    When I create an instance and call the cached method with argument 5
    Then the method should be executed
    And the result should be 10
    When I call the cached method again with argument 5
    Then the method should not be executed again
    And the result should be 10

  Scenario: Cache shared across instances
    Given a class with a cached method
    When I create two instances
    And I call the cached method on instance 1 with argument 5
    Then the method should be executed
    When I call the cached method on instance 2 with argument 5
    Then the method should not be executed again
    And both instances should return the same result

  Scenario: Clear cache functionality
    Given a function decorated with ttl_cache_decorator
    When I call the function with argument 5
    Then the function should be executed
    When I clear the cache
    And I call the function with argument 5
    Then the function should be executed again
    And the execution count should be 2

  Scenario: Clear all caches pattern
    Given a class with multiple cached methods
    When I call both cached methods
    Then both methods should be executed
    When I clear all caches
    And I call both cached methods again
    Then both methods should be executed again

  Scenario: None values are cached
    Given a function that returns None decorated with ttl_cache_decorator
    When I call the function with argument 5
    Then the function should be executed
    And the result should be None
    When I call the function again with argument 5
    Then the function should not be executed again
    And the result should be None

  Scenario: Exceptions are not cached
    Given a function that raises exceptions decorated with ttl_cache_decorator
    When I call the function with argument 5
    Then an exception should be raised
    And the function should be executed
    When I call the function with argument 5
    Then an exception should be raised
    And the function should be executed again

  Scenario: Keyword arguments handled correctly
    Given a function decorated with ttl_cache_decorator
    When I call the function with keyword argument x=5
    Then the function should be executed
    When I call the function with keyword argument x=5
    Then the function should not be executed again
    When I call the function with positional argument 5
    Then the function should be executed again

  Scenario: Mixed positional and keyword arguments
    Given a function with multiple parameters decorated with ttl_cache_decorator
    When I call the function with positional 5 and keyword y=10
    Then the function should be executed
    And the result should be 15
    When I call the function with positional 5 and keyword y=10
    Then the function should not be executed again
    And the result should be 15
    When I call the function with positional 5 and keyword y=20
    Then the function should be executed again
    And the result should be 25

  Scenario: Bound method identity consistency
    Given a class with a cached method
    When I create an instance
    Then the cached method should maintain identity consistency

  Scenario: Cache with different argument types
    Given a function decorated with ttl_cache_decorator
    When I call the function with string argument "test"
    Then the function should be executed
    When I call the function with integer argument 5
    Then the function should be executed
    When I call the function with string argument "test"
    Then the function should not be executed again
    And the execution count should be 2

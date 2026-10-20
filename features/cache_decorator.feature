Feature: TTL Cache Decorator
  As a developer
  I want to cache function results with TTL expiration
  So that I can improve performance by avoiding redundant computations

  Scenario: Basic function caching
    Given a function decorated with ttl_cache
    When I call the function with argument 5
    Then the function should be executed
    And the result should be 10
    When I call the function again with argument 5
    Then the function should not be executed again
    And the result should be 10

  Scenario: Different arguments create separate cache entries
    Given a function decorated with ttl_cache
    When I call the function with argument 5
    Then the function should be executed
    When I call the function with argument 10
    Then the function should be executed
    And the execution count should be 2

  Scenario: Cache expiration after TTL
    Given a function decorated with ttl_cache with TTL 2 seconds
    When I call the function with argument 5
    Then the function should be executed
    When I wait for 3 seconds
    And I call the function with argument 5
    Then the function should be executed again
    And the execution count should be 2

  Scenario: Cache respects maxsize limit
    Given a function decorated with ttl_cache with maxsize 3
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
    Given a function decorated with ttl_cache
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
    Given a function that returns None decorated with ttl_cache
    When I call the function with argument 5
    Then the function should be executed
    And the result should be None
    When I call the function again with argument 5
    Then the function should not be executed again
    And the result should be None

  Scenario: Exceptions are not cached
    Given a function that raises exceptions decorated with ttl_cache
    When I call the function with argument 5
    Then an exception should be raised
    And the function should be executed
    When I call the function with argument 5
    Then an exception should be raised
    And the function should be executed again

  Scenario: Keyword arguments handled correctly
    Given a function decorated with ttl_cache
    When I call the function with keyword argument x=5
    Then the function should be executed
    When I call the function with keyword argument x=5
    Then the function should not be executed again
    When I call the function with positional argument 5
    Then the function should be executed again

  Scenario: Mixed positional and keyword arguments
    Given a function with multiple parameters decorated with ttl_cache
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
    Given a function decorated with ttl_cache
    When I call the function with string argument "test"
    Then the function should be executed
    When I call the function with integer argument 5
    Then the function should be executed
    When I call the function with string argument "test"
    Then the function should not be executed again
    And the execution count should be 2

  Scenario: Equal values of different types are cached separately
    Given a function decorated with ttl_cache
    When I call the function with integer argument 1
    Then the function should be executed
    When I call the function with float argument 1.0
    Then the function should be executed

  Scenario: Unhashable arguments bypass the cache instead of failing
    Given a function decorated with ttl_cache
    When I call the function with a list argument
    Then the function should be executed
    When I call the function with a list argument
    Then the function should be executed again
    And the execution count should be 2

  Scenario: Async functions are cached by their awaited result
    Given an async function decorated with ttl_cache
    When I await the function with argument 5
    Then the function should be executed
    And the result should be 10
    When I await the function with argument 5
    Then the function should not be executed again
    And the result should be 10

  Scenario: Concurrent callers share the cache without errors
    Given a function decorated with ttl_cache
    When 8 threads call the function with argument 5 concurrently
    Then no thread should have raised an error
    And every thread should have received 10

  Scenario: Same-named cached methods in a class hierarchy do not share bound state
    Given a parent and child class with same-named cached methods
    When I call the child method with argument 3
    Then the child method result should be "child:base:3"

  Scenario: Decorators import without the cache extra
    Given cachetools is not installed
    When I import archipy.helpers.decorators
    Then the import should succeed
    And decorating with ttl_cache should fail with a message mentioning "archipy[cache]"

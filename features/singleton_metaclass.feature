Feature: Singleton Metaclass
  As a developer
  I want classes that only ever have one instance
  So that shared resources are created once

  Scenario: Repeated instantiation returns the same instance
    Given a class using the Singleton metaclass
    When the singleton class is instantiated twice
    Then both singleton instances are the same object
    And the singleton constructor ran 1 times

  Scenario: Constructor arguments after the first call are ignored
    Given a class using the Singleton metaclass
    When the singleton class is instantiated with value 10 and then with value 20
    Then both singleton instances are the same object
    And the singleton instance value is 10

  Scenario: Different singleton classes have independent instances
    Given two classes using the Singleton metaclass
    When each singleton class is instantiated
    Then the two singleton instances are different objects

  Scenario: A subclass of a singleton class has its own instance
    Given a class using the Singleton metaclass
    And a subclass of that singleton class
    When the singleton class and its subclass are instantiated
    Then the two singleton instances are different objects

  Scenario: Thread-safe singleton creates one instance under concurrency
    Given a thread-safe singleton class with a slow constructor
    When 8 threads instantiate the singleton class at the same time
    Then all threads received the same singleton instance
    And the singleton constructor ran 1 times

  Scenario: Singleton is thread-safe by default
    Given a singleton class with default thread safety and a slow constructor
    When 8 threads instantiate the singleton class at the same time
    Then all threads received the same singleton instance
    And the singleton constructor ran 1 times

  Scenario: The singleton decorator returns one instance and runs the constructor once
    Given a class using the singleton decorator
    When the singleton class is instantiated with value 10 and then with value 20
    Then both singleton instances are the same object
    And the singleton instance value is 10
    And the singleton constructor ran 1 times

  Scenario: The singleton decorator keeps the decorated name a class
    Given a class using the singleton decorator
    When the singleton class is instantiated twice
    Then the singleton instances are instances of the decorated class

  Scenario: The singleton decorator gives a subclass its own instance
    Given a class using the singleton decorator
    And a subclass of that singleton class
    When the singleton class and its subclass are instantiated
    Then the two singleton instances are different objects

  Scenario: The singleton decorator creates one instance under concurrency
    Given a thread-safe class using the singleton decorator with a slow constructor
    When 8 threads instantiate the singleton class at the same time
    Then all threads received the same singleton instance
    And the singleton constructor ran 1 times

  Scenario: A singleton constructor may create another singleton without deadlocking
    Given a singleton class whose constructor creates another singleton
    When the outer singleton class is instantiated in a worker thread
    Then the worker thread finished
    And the inner singleton instance was created

  Scenario: A singleton without locking still hands every thread the same instance
    Given a singleton class without thread safety and a slow constructor
    When 8 threads instantiate the singleton class at the same time
    Then all threads received the same singleton instance

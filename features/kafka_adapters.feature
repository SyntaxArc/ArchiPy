# features/kafka_operations.feature
@needs-kafka
Feature: Kafka Adapter Operations Testing
  As a developer
  I want to test Kafka adapter operations
  So that I can ensure reliable messaging functionality

  Background:
    Given a configured Kafka admin adapter
    And a test topic named "test-topic"

  Scenario: Create and verify a topic
    When I create a topic named "test-topic-2"
    Then the topic "test-topic-2" should exist
    And the topic list should include "test-topic-2"

  Scenario: Produce and consume a message
    Given a Kafka producer for topic "test-topic"
    And a Kafka consumer subscribed to topic "test-topic" with group "test-group"
    When I produce a message "Hello Kafka" to topic "test-topic"
    Then the consumer should receive message "Hello Kafka" from topic "test-topic" with group "test-group"

  Scenario: Validate producer health
    Given a Kafka producer for topic "test-topic"
    When I validate the producer health
    Then the producer health check should pass

  Scenario: Produce message with additional parameters
    Given a test topic named "test-topic2"
    And a Kafka producer for topic "test-topic2"
    And a Kafka consumer subscribed to topic "test-topic2" with group "test-group2"
    When I produce one message "Hello Kafka with key" with key "test-key" to topic "test-topic2"
    Then the consumer should receive message "Hello Kafka with key" from topic "test-topic2" with group "test-group2"

  Scenario: Delete a topic
    Given a topic named "test-topic-deletable" exists
    When I delete the topic "test-topic-deletable"
    Then the topic "test-topic-deletable" should not exist

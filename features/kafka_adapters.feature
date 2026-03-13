# features/kafka_operations.feature
@needs-kafka
Feature: Kafka Adapter Operations Testing
  As a developer
  I want to test Kafka adapter operations
  So that I can ensure reliable messaging functionality

  Background:
    Given a configured Kafka admin adapter

  Scenario: Create and verify a topic
    When I create a topic named "test-topic-create"
    Then the topic "test-topic-create" should exist
    And the topic list should include "test-topic-create"

  Scenario: Produce and consume a message
    Given a test topic named "test-topic"
    And a Kafka producer for topic "test-topic"
    And a Kafka consumer subscribed to topic "test-topic" with group "test-group"
    When I produce a message "Hello Kafka" to topic "test-topic"
    Then the consumer should receive message "Hello Kafka" from topic "test-topic" with group "test-group"

  Scenario: Validate producer health
    Given a Kafka producer for topic "test-topic"
    When I validate the producer health for topic "test-topic"
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

  Scenario: Batch produce and consume multiple messages
    Given a test topic named "test-topic-batch"
    And a Kafka producer for topic "test-topic-batch"
    And a Kafka consumer subscribed to topic "test-topic-batch" with group "test-group-batch"
    When I produce 3 messages to topic "test-topic-batch"
    Then the consumer should receive 3 messages from topic "test-topic-batch" with group "test-group-batch"

  Scenario: Verify message key is preserved
    Given a test topic named "test-topic-key"
    And a Kafka producer for topic "test-topic-key"
    And a Kafka consumer subscribed to topic "test-topic-key" with group "test-group-key"
    When I produce one message "keyed-value" with key "my-key" to topic "test-topic-key"
    Then the consumer should receive 1 messages from topic "test-topic-key" with group "test-group-key"
    And the received message should have key "my-key"

  Scenario: Commit consumed message offset
    Given a test topic named "test-topic-commit"
    And a Kafka producer for topic "test-topic-commit"
    And a Kafka consumer subscribed to topic "test-topic-commit" with group "test-group-commit"
    When I produce a message "commit-me" to topic "test-topic-commit"
    Then the consumer should receive message "commit-me" from topic "test-topic-commit" with group "test-group-commit"
    And I commit the consumed offset for topic "test-topic-commit" with group "test-group-commit"
    And the commit should succeed

  @async
  Scenario: Async create and verify a topic
    When I create a topic named "test-topic-create-async"
    Then the topic "test-topic-create-async" should exist
    And the topic list should include "test-topic-create-async"

  @async
  Scenario: Async produce and consume a message
    Given a test topic named "test-topic-async"
    And an async Kafka producer for topic "test-topic-async"
    And an async Kafka consumer subscribed to topic "test-topic-async" with group "test-group-async"
    When I async produce a message "Hello Kafka Async" to topic "test-topic-async"
    Then the async consumer should receive message "Hello Kafka Async" from topic "test-topic-async" with group "test-group-async"

  @async
  Scenario: Async validate producer health
    Given an async Kafka producer for topic "test-topic-async"
    When I validate the async producer health for topic "test-topic-async"
    Then the async producer health check should pass

  @async
  Scenario: Async produce message with additional parameters
    Given a test topic named "test-topic2-async"
    And an async Kafka producer for topic "test-topic2-async"
    And an async Kafka consumer subscribed to topic "test-topic2-async" with group "test-group2-async"
    When I async produce one message "Hello Kafka with key async" with key "test-key" to topic "test-topic2-async"
    Then the async consumer should receive message "Hello Kafka with key async" from topic "test-topic2-async" with group "test-group2-async"

  @async
  Scenario: Async delete a topic
    Given a topic named "test-topic-deletable-async" exists
    When I delete the topic "test-topic-deletable-async"
    Then the topic "test-topic-deletable-async" should not exist

  @async
  Scenario: Async batch produce and consume multiple messages
    Given a test topic named "test-topic-batch-async"
    And an async Kafka producer for topic "test-topic-batch-async"
    And an async Kafka consumer subscribed to topic "test-topic-batch-async" with group "test-group-batch-async"
    When I async produce 3 messages to topic "test-topic-batch-async"
    Then the async consumer should receive 3 messages from topic "test-topic-batch-async" with group "test-group-batch-async"

  @async
  Scenario: Async verify message key is preserved
    Given a test topic named "test-topic-key-async"
    And an async Kafka producer for topic "test-topic-key-async"
    And an async Kafka consumer subscribed to topic "test-topic-key-async" with group "test-group-key-async"
    When I async produce one message "keyed-value-async" with key "my-key-async" to topic "test-topic-key-async"
    Then the async consumer should receive 1 messages from topic "test-topic-key-async" with group "test-group-key-async"
    And the async received message should have key "my-key-async"

  @async
  Scenario: Async commit consumed message offset
    Given a test topic named "test-topic-commit-async"
    And an async Kafka producer for topic "test-topic-commit-async"
    And an async Kafka consumer subscribed to topic "test-topic-commit-async" with group "test-group-commit-async"
    When I async produce a message "async-commit-me" to topic "test-topic-commit-async"
    Then the async consumer should receive message "async-commit-me" from topic "test-topic-commit-async" with group "test-group-commit-async"
    And I async commit the consumed offset for topic "test-topic-commit-async" with group "test-group-commit-async"
    And the async commit should succeed

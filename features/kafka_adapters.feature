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

  Scenario: Commit without message (null commit)
    Given a test topic named "test-topic-null-commit"
    And a Kafka producer for topic "test-topic-null-commit"
    And a Kafka consumer subscribed to topic "test-topic-null-commit" with group "test-group-null-commit"
    When I produce a message "null-commit-test" to topic "test-topic-null-commit"
    Then the consumer should receive message "null-commit-test" from topic "test-topic-null-commit" with group "test-group-null-commit"
    When I commit without message for topic "test-topic-null-commit" with group "test-group-null-commit"
    Then the null commit should succeed

  @async
  Scenario: Async commit without message (null commit)
    Given a test topic named "test-topic-null-commit-async"
    And an async Kafka producer for topic "test-topic-null-commit-async"
    And an async Kafka consumer subscribed to topic "test-topic-null-commit-async" with group "test-group-null-commit-async"
    When I async produce a message "async-null-commit-test" to topic "test-topic-null-commit-async"
    Then the async consumer should receive message "async-null-commit-test" from topic "test-topic-null-commit-async" with group "test-group-null-commit-async"
    When I async commit without message for topic "test-topic-null-commit-async" with group "test-group-null-commit-async"
    Then the async null commit should succeed

  Scenario: Batch consume multiple messages
    Given a test topic named "test-topic-batch-consume"
    And a Kafka producer for topic "test-topic-batch-consume"
    And a Kafka consumer subscribed to topic "test-topic-batch-consume" with group "test-group-batch-consume"
    When I produce 5 messages to topic "test-topic-batch-consume"
    Then the consumer should receive 5 messages from topic "test-topic-batch-consume" with group "test-group-batch-consume"
    And I commit the batch for topic "test-topic-batch-consume" with group "test-group-batch-consume"
    And the commit should succeed

  @async
  Scenario: Async batch consume multiple messages
    Given a test topic named "test-topic-batch-consume-async"
    And an async Kafka producer for topic "test-topic-batch-consume-async"
    And an async Kafka consumer subscribed to topic "test-topic-batch-consume-async" with group "test-group-batch-consume-async"
    When I async produce 5 messages to topic "test-topic-batch-consume-async"
    Then the async consumer should receive 5 messages from topic "test-topic-batch-consume-async" with group "test-group-batch-consume-async"
    And I async commit the batch for topic "test-topic-batch-consume-async" with group "test-group-batch-consume-async"
    And the async commit should succeed

  @needs-otel-collector
  Scenario: Kafka producer and consumer emit spans
    Given adapter spans are exported to the collector
    When I produce and consume a message on topic "span-topic" through the Kafka adapters
    Then the collector should have a span with attribute "messaging.system" containing "kafka"
    And no span of this thread should be left active

  @needs-otel-collector
  Scenario: Async Kafka producer and consumer emit spans
    Given adapter spans are exported to the collector
    When I produce and consume a message on topic "span-topic-async" through the async Kafka adapters
    Then the collector should have a span with attribute "messaging.system" containing "kafka"

  @needs-otel-collector
  Scenario: Kafka consume span ends when the message is committed
    Given adapter spans are exported to the collector
    When I produce and consume a message on topic "span-topic-commit" through the Kafka adapters
    Then the collector should have a span whose name contains "span-topic-commit process"
    And no span of this thread should be left active

  @needs-otel-collector
  Scenario: A batch consume produces one consume span that ends at the commit
    Given adapter spans are exported to the collector
    When I produce 3 messages on topic "span-topic-batch" and consume them as one batch
    Then the consume span of topic "span-topic-batch" should not have been exported yet
    When I commit the last message of the batch
    Then exactly one consume span of topic "span-topic-batch" should be exported with 3 links
    And no span of this thread should be left active

  @needs-otel-collector
  Scenario: With auto commit the consume span stays open until the consumer is closed
    Given adapter spans are exported to the collector
    When I poll one message from topic "span-topic-auto" with auto commit enabled
    Then the consume span of topic "span-topic-auto" should not have been exported yet
    When the auto commit consumer is closed
    Then exactly one consume span of topic "span-topic-auto" should be exported with 1 links

  @needs-otel-collector
  Scenario: Each polled message gets its own consume span that ends at its commit
    Given adapter spans are exported to the collector
    When 3 messages are produced on topic "span-topic-multi" and polled and committed one by one
    Then 3 consume spans of topic "span-topic-multi" should be exported
    And no span of this thread should be left active

  @needs-otel-collector
  Scenario: Without commits each consume span ends at the next poll
    Given adapter spans are exported to the collector
    When 3 messages are produced on topic "span-topic-nocommit" and polled without committing
    Then 2 consume spans of topic "span-topic-nocommit" should be exported and the last one still open
    When the multi message consumer is closed
    Then 3 consume spans of topic "span-topic-nocommit" should be exported

  Scenario Outline: Health check of a <mode> producer reports an unreachable broker as unavailable
    Given an unreachable Kafka broker
    When I validate the health of a <mode> producer on that broker
    Then the Kafka operation should raise "UnavailableError"

    Examples:
      | mode  |
      | sync  |
      | async |

  Scenario Outline: Listing topics with the <adapter_kind> adapter fails when the broker is unreachable
    Given an unreachable Kafka broker
    When I list topics with the <adapter_kind> adapter on that broker
    Then the Kafka operation should raise "InternalError"

    Examples:
      | adapter_kind   |
      | admin          |
      | sync producer  |
      | async producer |

  Scenario: Producing into a full local queue is reported as resource exhaustion
    Given an unreachable Kafka broker
    When I produce 2 messages with a producer whose queue holds only 1 message on that broker
    Then the Kafka operation should raise "ResourceExhaustedError"

  Scenario Outline: A <mode> <role> with an invalid setting raises a configuration error
    When I use a <mode> <role> configured with an invalid setting
    Then the Kafka operation should raise "ConfigurationError"

    Examples:
      | mode  | role     |
      | sync  | producer |
      | sync  | consumer |
      | async | producer |
      | async | consumer |

  Scenario Outline: A <mode> consumer created with <arguments> is rejected
    When I create a <mode> consumer with <arguments>
    Then the Kafka operation should raise "InvalidArgumentError"

    Examples:
      | mode  | arguments                  |
      | sync  | no topics or partitions    |
      | sync  | both topics and partitions |
      | async | no topics or partitions    |
      | async | both topics and partitions |

  Scenario Outline: A <mode> consumer assigned to a partition reads its messages
    Given a single partition topic named "test-topic-assign-<mode>"
    And a Kafka producer for topic "test-topic-assign-<mode>"
    When I produce a message "assigned-message" to topic "test-topic-assign-<mode>"
    Then a <mode> consumer assigned to partition 0 of topic "test-topic-assign-<mode>" should receive message "assigned-message"

    Examples:
      | mode  |
      | sync  |
      | async |

  Scenario Outline: A <mode> consumer polls a single message
    Given a test topic named "test-topic-poll-<mode>"
    And a Kafka producer for topic "test-topic-poll-<mode>"
    When I produce a message "polled-message" to topic "test-topic-poll-<mode>"
    Then a <mode> consumer polling topic "test-topic-poll-<mode>" with group "test-group-poll-<mode>" should receive message "polled-message"

    Examples:
      | mode  |
      | sync  |
      | async |

  Scenario Outline: A <mode> consumer polling an empty topic receives nothing
    Given a test topic named "test-topic-poll-empty-<mode>"
    Then a <mode> consumer polling the empty topic "test-topic-poll-empty-<mode>" with group "test-group-poll-empty-<mode>" should receive nothing

    Examples:
      | mode  |
      | sync  |
      | async |

  Scenario Outline: Closing a <mode> producer delivers the messages still queued
    Given a test topic named "test-topic-close-<mode>"
    When a <mode> producer for topic "test-topic-close-<mode>" produces "closed-message" without flushing and is closed
    Then a <mode> consumer polling topic "test-topic-close-<mode>" with group "test-group-close-<mode>" should receive message "closed-message"

    Examples:
      | mode  |
      | sync  |
      | async |

  Scenario Outline: A <mode> producer lists a single topic
    Given a test topic named "test-topic-list-<mode>"
    Then a <mode> producer for topic "test-topic-list-<mode>" should list that topic

    Examples:
      | mode  |
      | sync  |
      | async |

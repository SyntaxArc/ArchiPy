# features/kafka_clients_spans.feature
@needs-kafka
Feature: Kafka Clients and Spans Testing
  As a developer
  I want to test Kafka adapter operations
  So that I can ensure reliable messaging functionality

  Background:
    Given a configured Kafka admin adapter

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

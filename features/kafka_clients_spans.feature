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
    Then the Kafka operation should raise one of "NetworkError, ServiceUnavailableError, ConnectionTimeoutError"

    Examples:
      | adapter_kind   |
      | admin          |
      | sync producer  |
      | async producer |

  Scenario Outline: A Kafka failure with code <code> is raised as <error>
    When the adapters handle a Kafka failure with code <code>
    Then the Kafka operation should raise "<error>"

    Examples:
      | code                       | error                   |
      | _MSG_TIMED_OUT             | ConnectionTimeoutError  |
      | _TIMED_OUT                 | ConnectionTimeoutError  |
      | REQUEST_TIMED_OUT          | ConnectionTimeoutError  |
      | _TRANSPORT                 | NetworkError            |
      | _ALL_BROKERS_DOWN          | ServiceUnavailableError |
      | BROKER_NOT_AVAILABLE       | ServiceUnavailableError |
      | _AUTHENTICATION            | UnauthenticatedError    |
      | SASL_AUTHENTICATION_FAILED | UnauthenticatedError    |
      | TOPIC_AUTHORIZATION_FAILED | PermissionDeniedError   |
      | GROUP_AUTHORIZATION_FAILED | PermissionDeniedError   |
      | _INVALID_ARG               | InvalidArgumentError    |

  Scenario: A transactional producer commits and aborts transactions
    Given a test topic named "test-topic-txn"
    When a transactional producer for topic "test-topic-txn" aborts "aborted-message" and then commits "committed-message"
    Then a read committed consumer on topic "test-topic-txn" with group "test-group-txn" should first receive "committed-message"

  Scenario Outline: A <mode> producer with <setting> cannot be used for a transaction
    When I use a <mode> producer with <setting> for a transaction
    Then the Kafka operation should raise "<error>"

    Examples:
      | mode  | setting             | error                |
      | sync  | no transactional id | InvalidArgumentError |
      | async | a transactional id  | ConfigurationError   |

  Scenario: An async consumer whose subscription failed keeps failing instead of polling unsubscribed
    When I poll an async consumer subscribed to an invalid topic pattern twice
    Then the Kafka operation should raise "InvalidArgumentError"

  Scenario Outline: A sync consumer that fails with <failure> leaves no client running
    When I create 3 sync consumers that fail with <failure>
    Then the Kafka operation should raise "InvalidArgumentError"
    And no librdkafka client should be left running

    Examples:
      | failure                 |
      | no topics               |
      | an invalid subscription |

  Scenario Outline: A <mode> consumer that <operation>s a message carrying <code> raises <error>
    When a <mode> consumer <operation>s a message that carries the Kafka error <code>
    Then the Kafka operation should raise "<error>"

    Examples:
      | mode  | operation | code                       | error                   |
      | sync  | poll      | _ALL_BROKERS_DOWN          | ServiceUnavailableError |
      | sync  | consume   | _AUTHENTICATION            | UnauthenticatedError    |
      | async | poll      | TOPIC_AUTHORIZATION_FAILED | PermissionDeniedError   |
      | async | consume   | _ALL_BROKERS_DOWN          | ServiceUnavailableError |

  Scenario Outline: A <mode> consumer skips a message carrying the harmless error <code>
    When a <mode> consumer <operation>s a message that carries the Kafka error <code>
    Then the consumer should have received nothing

    Examples:
      | mode  | operation | code                  |
      | sync  | poll      | _PARTITION_EOF        |
      | sync  | consume   | UNKNOWN_TOPIC_OR_PART |
      | async | poll      | _PARTITION_EOF        |
      | async | consume   | UNKNOWN_TOPIC_OR_PART |

  Scenario: A sync producer serves delivery reports so a small queue does not overflow
    Given a test topic named "test-topic-small-queue"
    When I produce 200 messages to topic "test-topic-small-queue" without flushing through a queue limited to 5 messages
    Then the Kafka operation should raise nothing

  Scenario: A failed delivery is reported to the caller and logged without the payload
    Given an unreachable Kafka broker
    When a sync producer on that broker fails to deliver "secret-payload" with key "user-key" to topic "failed-delivery-topic"
    Then the delivery failure should be passed to the on_delivery callback
    And the logs should mention topic "failed-delivery-topic" but not "secret-payload"

  Scenario Outline: A <mode> producer with missing keys sent as <setting> delivers a keyless message with <key_state>
    Given a test topic named "test-topic-keyless-<mode>-<code>"
    When a <mode> producer with missing keys sent as <setting> produces a message without a key to topic "test-topic-keyless-<mode>-<code>"
    Then the message on topic "test-topic-keyless-<mode>-<code>" should have <key_state> and the deprecation warning should be <warned>

    Examples:
      | mode  | setting      | code   | key_state    | warned     |
      | sync  | an empty key | legacy | an empty key | raised     |
      | sync  | no key       | none   | no key       | not raised |
      | async | an empty key | legacy | an empty key | raised     |
      | async | no key       | none   | no key       | not raised |

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

  Scenario Outline: A SASL_SSL <role> with hostname verification <setting> verifies broker hostnames with <expected>
    When Kafka client settings are built for a <role> with hostname verification <setting>
    Then the Kafka broker hostname verification should be "<expected>"

    Examples:
      | role           | setting | expected |
      | sync client    | default | https    |
      | sync client    | none    | none     |
      | async producer | default | https    |
      | async producer | none    | none     |
      | async consumer | default | https    |
      | async consumer | none    | none     |

  Scenario Outline: Kafka client settings for protocol <protocol> with mechanism <mechanism> carry <present> and omit <absent>
    When Kafka client settings are built for protocol <protocol> with mechanism <mechanism>, username <username>, CA file <ca>, certificate <cert> and key <key>
    Then the Kafka client settings should include "<present>"
    And the Kafka client settings should not include "<absent>"

    Examples:
      | protocol       | mechanism     | username | ca     | cert       | key        | present                                             | absent                                 |
      | SSL            | -             | -        | -      | client.pem | client.key | ssl.certificate.location,ssl.key.location           | ssl.ca.location,sasl.username          |
      | SASL_PLAINTEXT | PLAIN         | user     | -      | -          | -          | sasl.mechanism,sasl.username,sasl.password          | ssl.ca.location                        |
      | SASL_PLAINTEXT | OAUTHBEARER   | -        | -      | -          | -          | security.protocol,sasl.mechanism                    | sasl.username,sasl.password            |
      | SASL_SSL       | GSSAPI        | -        | ca.pem | -          | -          | sasl.mechanism,ssl.ca.location                      | sasl.username,ssl.certificate.location |
      | SASL_SSL       | SCRAM-SHA-512 | user     | -      | -          | -          | sasl.username,ssl.endpoint.identification.algorithm | ssl.ca.location                        |
      | PLAINTEXT      | -             | -        | -      | -          | -          | security.protocol                                   | sasl.mechanism,ssl.ca.location         |
      | ssl            | -             | -        | ca.pem | -          | -          | security.protocol,ssl.ca.location                   | sasl.mechanism,sasl.username           |
      | sasl_ssl       | plain         | user     | ca.pem | -          | -          | sasl.mechanism,sasl.username,ssl.ca.location        | ssl.certificate.location               |

  Scenario Outline: A <role> built with Kafka setting <setting> set to <value> passes <option> to librdkafka as <expected>
    When Kafka client settings are built for a <role> with Kafka setting <setting> set to <value>
    Then the Kafka client option "<option>" should be "<expected>"

    Examples:
      | role           | setting                  | value      | option                   | expected   |
      | sync client    | CLIENT_ID                | my-app     | client.id                | my-app     |
      | async producer | CLIENT_ID                | my-app     | client.id                | my-app     |
      | async consumer | CLIENT_ID                | my-app     | client.id                | my-app     |
      | sync client    | CONNECTIONS_MAX_IDLE_MS  | 60000      | connections.max.idle.ms  | 60000      |
      | async producer | SOCKET_TIMEOUT_MS        | 20000      | socket.timeout.ms        | 20000      |
      | async consumer | RECONNECT_BACKOFF_MAX_MS | 5000       | reconnect.backoff.max.ms | 5000       |
      | async producer | RETRY_BACKOFF_MS         | 250        | retry.backoff.ms         | 250        |
      | async producer | MESSAGE_TIMEOUT_MS       | 90000      | message.timeout.ms       | 90000      |
      | async consumer | GROUP_INSTANCE_ID        | instance-1 | group.instance.id        | instance-1 |
      | async consumer | ENABLE_AUTO_OFFSET_STORE | false      | enable.auto.offset.store | False      |
      | async producer | SOCKET_TIMEOUT_MS        | unset      | socket.timeout.ms        | absent     |
      | async consumer | GROUP_INSTANCE_ID        | unset      | group.instance.id        | absent     |
      | async producer | GROUP_INSTANCE_ID        | instance-1 | group.instance.id        | absent     |

  Scenario Outline: Listing topics with the <adapter_kind> adapter waits for the configured timeout of <timeout_ms> ms
    Given an unreachable Kafka broker
    When I list topics with the <adapter_kind> adapter on that broker with the default timeout set to <timeout_ms> ms
    Then listing topics should have waited at least <seconds> seconds

    Examples:
      | adapter_kind   | timeout_ms | seconds |
      | admin          | 2500       | 2.5     |
      | sync producer  | 1500       | 1.5     |
      | async producer | 2000       | 2.0     |

  Scenario Outline: A Kafka configuration with protocol <protocol>, mechanism <mechanism> and username <username> is rejected
    When a Kafka configuration is validated with protocol <protocol>, mechanism <mechanism> and username <username>
    Then the Kafka configuration should be rejected as incomplete

    Examples:
      | protocol       | mechanism     | username |
      | SASL_PLAINTEXT | -             | user     |
      | SASL_SSL       | PLAIN         | -        |
      | SASL_SSL       | SCRAM-SHA-256 | -        |
      | sasl_ssl       | plain         | -        |
      | Sasl_Plaintext | scram-sha-512 | -        |

  Scenario Outline: A Kafka configuration with protocol <protocol> is rejected as unknown
    When a Kafka configuration is validated with protocol <protocol>, mechanism - and username -
    Then the Kafka configuration should be rejected as an unknown protocol

    Examples:
      | protocol |
      | TLS      |
      | kerberos |

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

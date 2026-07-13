@needs-redis @needs-redis-cluster
Feature: Redis Testing
  As a developer
  I want to test Redis operations with both mocks and real containers
  So that I can ensure compatibility and reliability across different environments

  Background:
    Given test entities are defined

  Scenario Outline: Store and retrieve a simple key-value pair
    Given a configured <adapter_type>
    When I store the key "user-id" with value "12345" in <adapter_type>
    Then the sync store operation should succeed
    When I retrieve the value for key "user-id" from <adapter_type>
    Then the sync retrieved value should be "12345"

    Examples: Adapter Types
      | adapter_type    |
      | mock            |
      | container       |
      | cluster         |

  Scenario Outline: Remove a key
    Given a configured <adapter_type>
    When I store the key "session-token" with value "abcde" in <adapter_type>
    Then the sync store operation should succeed
    When I remove the key "session-token" from <adapter_type>
    Then the sync remove operation should delete one key
    When I check if "session-token" exists in <adapter_type>
    Then the sync key should not exist

    Examples: Adapter Types
      | adapter_type    |
      | mock            |
      | container       |
      | cluster         |

  Scenario Outline: Manage a list of items
    Given a configured <adapter_type>
    When I add "apple, banana, orange" to the list "fruits" in <adapter_type>
    Then the sync list "fruits" should have 3 items
    When I fetch all items from the list "fruits" in <adapter_type>
    Then the sync list "fruits" should contain "apple, banana, orange"

    Examples: Adapter Types
      | adapter_type    |
      | mock            |
      | container       |
      | cluster         |

  Scenario Outline: Handle a hash structure
    Given a configured <adapter_type>
    When I assign "name" to "Alice" in the hash "profile" in <adapter_type>
    Then the sync hash assignment should succeed
    When I retrieve the "name" field from the hash "profile" in <adapter_type>
    Then the sync retrieved field value should be "Alice"

    Examples: Adapter Types
      | adapter_type    |
      | mock            |
      | container       |
      | cluster         |

  Scenario Outline: Manage a set of colors
    Given a configured <adapter_type>
    When I add "red, blue, green" to the set "colors" in <adapter_type>
    Then the sync set "colors" should have 3 members
    When I fetch all members from the set "colors" in <adapter_type>
    Then the sync set "colors" should contain "red, blue, green"

    Examples: Adapter Types
      | adapter_type    |
      | mock            |
      | container       |
      | cluster         |

  @async
  Scenario Outline: Store and retrieve a key-value pair asynchronously
    Given a configured async <adapter_type>
    When I store the key "order-id" with value "67890" in async <adapter_type>
    Then the async store operation should succeed
    When I retrieve the value for key "order-id" from async <adapter_type>
    Then the async retrieved value should be "67890"

    Examples: Adapter Types
      | adapter_type    |
      | mock            |
      | container       |
      | cluster         |

  @async
  Scenario Outline: Remove a key asynchronously
    Given a configured async <adapter_type>
    When I store the key "cache-key" with value "xyz" in async <adapter_type>
    Then the async store operation should succeed
    When I remove the key "cache-key" from async <adapter_type>
    Then the async remove operation should delete one key
    When I check if "cache-key" exists in async <adapter_type>
    Then the async key should not exist

    Examples: Adapter Types
      | adapter_type    |
      | mock            |
      | container       |
      | cluster         |

  @async
  Scenario Outline: Manage a list of tasks asynchronously
    Given a configured async <adapter_type>
    When I add "task1, task2, task3" to the list "tasks" in async <adapter_type>
    Then the async list "tasks" should have 3 items
    When I fetch all items from the list "tasks" in async <adapter_type>
    Then the async list "tasks" should contain "task1, task2, task3"

    Examples: Adapter Types
      | adapter_type    |
      | mock            |
      | container       |
      | cluster         |

  @async
  Scenario Outline: Handle a hash structure asynchronously
    Given a configured async <adapter_type>
    When I assign "email" to "bob@example.com" in the hash "contact" in async <adapter_type>
    Then the async hash assignment should succeed
    When I retrieve the "email" field from the hash "contact" in async <adapter_type>
    Then the async retrieved field value should be "bob@example.com"

    Examples: Adapter Types
      | adapter_type    |
      | mock            |
      | container       |
      | cluster         |

  @async
  Scenario Outline: Manage a set of tags asynchronously
    Given a configured async <adapter_type>
    When I add "tag1, tag2, tag3" to the set "tags" in async <adapter_type>
    Then the async set "tags" should have 3 members
    When I fetch all members from the set "tags" in async <adapter_type>
    Then the async set "tags" should contain "tag1, tag2, tag3"

    Examples: Adapter Types
      | adapter_type    |
      | mock            |
      | container       |
      | cluster         |

  Scenario: Cluster reports healthy state
    Given a configured cluster
    When I query cluster info from the adapter
    Then cluster state should be ok

  Scenario Outline: Hash-tagged keys round-trip on cluster
    Given a configured cluster
    When I store the key "<key>" with value "<value>" in cluster
    And I retrieve the value for key "<key>" from cluster
    Then the sync retrieved value should be "<value>"

    Examples: Hash-tagged keys
      | key        | value   |
      | {user}:1   | alice   |
      | {order}:99 | shipped |

  Scenario Outline: Slot lookup in valid range on cluster
    Given a configured cluster
    When I get the cluster slot for key "<key>"
    Then the slot should be between 0 and 16383

    Examples: Keys
      | key        |
      | {user}:1   |
      | order:99   |

  Scenario: Cluster topology has 3 masters and 3 replicas
    Given a configured cluster
    When I query cluster nodes from the adapter
    Then cluster should have 3 masters and 3 replicas

  Scenario Outline: Hash-tagged keys share slot on cluster
    Given a configured cluster
    When I get the cluster slots for keys "<key1>" and "<key2>"
    Then both keys should share the same slot

    Examples: Hash-tagged key pairs
      | key1       | key2       |
      | {user}:1   | {user}:2   |
      | {order}:1  | {order}:2  |

  Scenario Outline: Slot key inspection on cluster
    Given a configured cluster
    When I store the key "<key>" with value "<value>" in cluster
    And I inspect keys in the cluster slot for key "<key>"
    Then the cluster slot should contain at least 1 key
    And the cluster slot should include key "<key>"

    Examples: Keys
      | key        | value   |
      | {user}:1   | alice   |
      | {order}:99 | shipped |

  @async
  Scenario: Cluster reports healthy state asynchronously
    Given a configured async cluster
    When I query cluster info from the async adapter
    Then cluster state should be ok

  @async
  Scenario Outline: Hash-tagged keys round-trip on cluster asynchronously
    Given a configured async cluster
    When I store the key "<key>" with value "<value>" in async cluster
    And I retrieve the value for key "<key>" from async cluster
    Then the async retrieved value should be "<value>"

    Examples: Hash-tagged keys
      | key        | value   |
      | {user}:1   | alice   |
      | {order}:99 | shipped |

  @async
  Scenario Outline: Slot lookup in valid range on cluster asynchronously
    Given a configured async cluster
    When I get the cluster slot for key "<key>" from the async adapter
    Then the slot should be between 0 and 16383

    Examples: Keys
      | key        |
      | {user}:1   |
      | order:99   |

  @async
  Scenario: Cluster topology has 3 masters and 3 replicas asynchronously
    Given a configured async cluster
    When I query cluster nodes from the async adapter
    Then cluster should have 3 masters and 3 replicas

  @async
  Scenario Outline: Hash-tagged keys share slot on cluster asynchronously
    Given a configured async cluster
    When I get the cluster slots for keys "<key1>" and "<key2>" from the async adapter
    Then both keys should share the same slot

    Examples: Hash-tagged key pairs
      | key1       | key2       |
      | {user}:1   | {user}:2   |
      | {order}:1  | {order}:2  |

  @async
  Scenario Outline: Slot key inspection on cluster asynchronously
    Given a configured async cluster
    When I store the key "<key>" with value "<value>" in async cluster
    And I inspect keys in the cluster slot for key "<key>" from the async adapter
    Then the cluster slot should contain at least 1 key
    And the cluster slot should include key "<key>"

    Examples: Keys
      | key        | value   |
      | {user}:1   | alice   |
      | {order}:99 | shipped |

  Scenario Outline: Store key with expiry and verify TTL
    Given a configured <adapter_type>
    When I store the key "bdd-s-ttl-key" with value "expires" and expiry 60 seconds in <adapter_type>
    Then the sync store with expiry should succeed
    When I check the TTL for key "bdd-s-ttl-key" in <adapter_type>
    Then the sync TTL should be between 1 and 60
    When I check the PTTL for key "bdd-s-ttl-key" in <adapter_type>
    Then the sync PTTL should be positive

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  Scenario Outline: GetSet returns old value
    Given a configured <adapter_type>
    When I store the key "bdd-s-gs-key" with value "old" in <adapter_type>
    And I getset key "bdd-s-gs-key" to value "new" in <adapter_type>
    Then the sync getset old value should be "old"
    When I retrieve the value for key "bdd-s-gs-key" from <adapter_type>
    Then the sync retrieved value should be "new"

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  Scenario Outline: GetDel returns value and removes key
    Given a configured <adapter_type>
    When I store the key "bdd-s-gd-key" with value "gone" in <adapter_type>
    And I getdel key "bdd-s-gd-key" in <adapter_type>
    Then the sync getdel value should be "gone"
    When I check if "bdd-s-gd-key" exists in <adapter_type>
    Then the sync key should not exist

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  Scenario Outline: Append extends string value
    Given a configured <adapter_type>
    When I store the key "bdd-s-app-key" with value "hello" in <adapter_type>
    And I append " world" to key "bdd-s-app-key" in <adapter_type>
    Then the sync append length should be 11
    When I retrieve the value for key "bdd-s-app-key" from <adapter_type>
    Then the sync retrieved value should be "hello world"

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  Scenario Outline: Report key type
    Given a configured <adapter_type>
    When I create a <redis_type> key "bdd-s-<redis_type>-key" in <adapter_type>
    And I check the type of key "bdd-s-<redis_type>-key" in <adapter_type>
    Then the sync key type should be "<redis_type>"

    Examples: Key types
      | adapter_type | redis_type |
      | mock         | string     |
      | mock         | list       |
      | mock         | hash       |
      | mock         | set        |
      | mock         | zset       |
      | container    | string     |
      | container    | list       |
      | container    | hash       |
      | container    | set        |
      | container    | zset       |
      | cluster      | string     |
      | cluster      | list       |
      | cluster      | hash       |
      | cluster      | set        |
      | cluster      | zset       |

  Scenario Outline: Increment and decrement counter
    Given a configured <adapter_type>
    When I increment key "bdd-s-counter" by 5 in <adapter_type>
    Then the sync counter value should be 5
    When I increment key "bdd-s-counter" by -2 in <adapter_type>
    Then the sync counter value should be 3

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  Scenario Outline: Mset and mget multiple keys
    Given a configured <adapter_type>
    When I mset "{bdd-s-m}:1" to "val1" and "{bdd-s-m}:2" to "val2" in <adapter_type>
    And I mget keys "{bdd-s-m}:1" and "{bdd-s-m}:2" from <adapter_type>
    Then the sync mget values should be "val1,val2"

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  Scenario Outline: Find keys by pattern and scan
    Given a configured <adapter_type>
    When I mset "{bdd-s-scan}:1" to "a" and "{bdd-s-scan}:2" to "b" in <adapter_type>
    And I find keys matching "{bdd-s-scan}:*" in <adapter_type>
    Then the found keys should include "{bdd-s-scan}:1" and "{bdd-s-scan}:2"
    When I scan keys matching "{bdd-s-scan}:*" in <adapter_type>
    Then the scanned keys should include "{bdd-s-scan}:1" and "{bdd-s-scan}:2"

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  Scenario Outline: Lpush and lpop preserve order
    Given a configured <adapter_type>
    When I lpush "first, second" to list "bdd-s-mylist" in <adapter_type>
    Then the sync list "bdd-s-mylist" should have 2 items
    When I lpop from list "bdd-s-mylist" in <adapter_type>
    Then the sync popped value should be "second"

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  Scenario Outline: Rpop and lrem modify list
    Given a configured <adapter_type>
    When I add "a, b, a, c" to the list "bdd-s-rlist" in <adapter_type>
    When I rpop from list "bdd-s-rlist" in <adapter_type>
    Then the sync popped value should be "c"
    When I lrem 1 "a" from list "bdd-s-rlist" in <adapter_type>
    Then the sync list "bdd-s-rlist" should have 2 items
    When I lset index 0 to "x" in list "bdd-s-rlist" in <adapter_type>
    And I fetch all items from the list "bdd-s-rlist" in <adapter_type>
    Then the sync list "bdd-s-rlist" should contain "x, a"

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  Scenario Outline: Set membership and removal
    Given a configured <adapter_type>
    When I add "alpha, beta" to the set "bdd-s-myset" in <adapter_type>
    When I check if "alpha" is a member of set "bdd-s-myset" in <adapter_type>
    Then the sync set membership should be true
    When I check if "gamma" is a member of set "bdd-s-myset" in <adapter_type>
    Then the sync set membership should be false
    When I remove "alpha" from set "bdd-s-myset" in <adapter_type>
    Then the sync set "bdd-s-myset" should have 1 members
    When I spop from set "bdd-s-myset" in <adapter_type>
    Then the sync set "bdd-s-myset" should have 0 members

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  Scenario Outline: Set union across hash-tagged sets
    Given a configured <adapter_type>
    When I add "a, b" to the set "{bdd-s-su}:1" in <adapter_type>
    And I add "b, c" to the set "{bdd-s-su}:2" in <adapter_type>
    When I union sets "{bdd-s-su}:1" and "{bdd-s-su}:2" in <adapter_type>
    Then the sync set union should contain "a, b, c"

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  Scenario Outline: Manage sorted set members
    Given a configured <adapter_type>
    When I zadd members "alice=10,bob=20" to sorted set "bdd-s-leaderboard" in <adapter_type>
    Then the sync sorted set "bdd-s-leaderboard" should have 2 members
    When I get zscore of "alice" in sorted set "bdd-s-leaderboard" in <adapter_type>
    Then the sync zscore should be 10.0
    When I get zrank of "bob" in sorted set "bdd-s-leaderboard" in <adapter_type>
    Then the sync zrank should be 1
    When I zrange sorted set "bdd-s-leaderboard" from 0 to -1 in <adapter_type>
    Then the sync zrange members should be "alice, bob"
    When I zrevrange sorted set "bdd-s-leaderboard" from 0 to -1 in <adapter_type>
    Then the sync zrange members should be "bob, alice"
    When I zrangebyscore sorted set "bdd-s-leaderboard" from 10 to 20 in <adapter_type>
    Then the sync zrange members should be "alice, bob"
    When I zcount sorted set "bdd-s-leaderboard" from 10 to 15 in <adapter_type>
    Then the sync zcount should be 1
    When I zincrby 5 "alice" in sorted set "bdd-s-leaderboard" in <adapter_type>
    Then the sync zscore should be 15.0
    When I zrem "bob" from sorted set "bdd-s-leaderboard" in <adapter_type>
    Then the sync sorted set "bdd-s-leaderboard" should have 1 members
    When I zpopmax from sorted set "bdd-s-leaderboard" in <adapter_type>
    Then the sync zpop result should be "alice"

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  Scenario Outline: Hash field operations
    Given a configured <adapter_type>
    When I hset mapping "name=Alice,email=alice@test.com" in hash "bdd-s-user" in <adapter_type>
    Then the sync hash "bdd-s-user" should have 2 fields
    When I check if field "name" exists in hash "bdd-s-user" in <adapter_type>
    Then the sync hash field exists should be true
    When I hmget fields "name,email" from hash "bdd-s-user" in <adapter_type>
    Then the sync hmget values should be "Alice,alice@test.com"
    When I fetch all fields from hash "bdd-s-user" in <adapter_type>
    Then the sync hash keys should be "email, name"
    And the sync hash values should be "alice@test.com, Alice"
    When I delete field "email" from hash "bdd-s-user" in <adapter_type>
    Then the sync hash "bdd-s-user" should have 1 fields

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  Scenario Outline: Publish message to channel
    Given a configured <adapter_type>
    When I publish "hello" to channel "bdd-s-test-channel" in <adapter_type>
    Then the sync publish count should be at least 0

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  Scenario Outline: Subscribe and receive published message
    Given a configured <adapter_type>
    When I subscribe to channel "bdd-s-pubsub-<adapter_type>-channel" in <adapter_type>
    And I publish "greeting" to channel "bdd-s-pubsub-<adapter_type>-channel" in <adapter_type>
    Then the sync subscribed message should be "greeting"

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |

  Scenario Outline: Pipeline executes commands atomically
    Given a configured <adapter_type>
    When I run pipeline setting "{<pipe_tag>}:k" to "v" and incrementing "{<pipe_tag>}:cnt" by 1 in <adapter_type>
    Then the sync pipeline results should be "True, 1, v"
    When I retrieve the value for key "{<pipe_tag>}:k" from <adapter_type>
    Then the sync retrieved value should be "v"

    Examples: Pipeline keys
      | adapter_type | pipe_tag      |
      | mock         | bdd-s-p-mock  |
      | container    | bdd-s-p-cont  |
      | cluster      | bdd-s-p-clust |

  @async
  Scenario Outline: Store key with expiry and verify TTL asynchronously
    Given a configured async <adapter_type>
    When I store the key "bdd-a-ttl-key" with value "expires" and expiry 60 seconds in async <adapter_type>
    Then the async store with expiry should succeed
    When I check the TTL for key "bdd-a-ttl-key" in async <adapter_type>
    Then the async TTL should be between 1 and 60
    When I check the PTTL for key "bdd-a-ttl-key" in async <adapter_type>
    Then the async PTTL should be positive

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  @async
  Scenario Outline: GetSet returns old value asynchronously
    Given a configured async <adapter_type>
    When I store the key "bdd-a-gs-key" with value "old" in async <adapter_type>
    And I getset key "bdd-a-gs-key" to value "new" in async <adapter_type>
    Then the async getset old value should be "old"
    When I retrieve the value for key "bdd-a-gs-key" from async <adapter_type>
    Then the async retrieved value should be "new"

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  @async
  Scenario Outline: GetDel returns value and removes key asynchronously
    Given a configured async <adapter_type>
    When I store the key "bdd-a-gd-key" with value "gone" in async <adapter_type>
    And I getdel key "bdd-a-gd-key" in async <adapter_type>
    Then the async getdel value should be "gone"
    When I check if "bdd-a-gd-key" exists in async <adapter_type>
    Then the async key should not exist

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  @async
  Scenario Outline: Append extends string value asynchronously
    Given a configured async <adapter_type>
    When I store the key "bdd-a-app-key" with value "hello" in async <adapter_type>
    And I append " world" to key "bdd-a-app-key" in async <adapter_type>
    Then the async append length should be 11
    When I retrieve the value for key "bdd-a-app-key" from async <adapter_type>
    Then the async retrieved value should be "hello world"

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  @async
  Scenario Outline: Report key type asynchronously
    Given a configured async <adapter_type>
    When I create a <redis_type> key "bdd-a-<redis_type>-key" in async <adapter_type>
    And I check the type of key "bdd-a-<redis_type>-key" in async <adapter_type>
    Then the async key type should be "<redis_type>"

    Examples: Key types
      | adapter_type | redis_type |
      | mock         | string     |
      | mock         | list       |
      | mock         | hash       |
      | mock         | set        |
      | mock         | zset       |
      | container    | string     |
      | container    | list       |
      | container    | hash       |
      | container    | set        |
      | container    | zset       |
      | cluster      | string     |
      | cluster      | list       |
      | cluster      | hash       |
      | cluster      | set        |
      | cluster      | zset       |

  @async
  Scenario Outline: Increment and decrement counter asynchronously
    Given a configured async <adapter_type>
    When I increment key "bdd-a-counter" by 5 in async <adapter_type>
    Then the async counter value should be 5
    When I increment key "bdd-a-counter" by -2 in async <adapter_type>
    Then the async counter value should be 3

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  @async
  Scenario Outline: Mset and mget multiple keys asynchronously
    Given a configured async <adapter_type>
    When I mset "{bdd-a-m}:1" to "val1" and "{bdd-a-m}:2" to "val2" in async <adapter_type>
    And I mget keys "{bdd-a-m}:1" and "{bdd-a-m}:2" from async <adapter_type>
    Then the async mget values should be "val1,val2"

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  @async
  Scenario Outline: Find keys by pattern and scan asynchronously
    Given a configured async <adapter_type>
    When I mset "{bdd-a-scan}:1" to "a" and "{bdd-a-scan}:2" to "b" in async <adapter_type>
    And I find keys matching "{bdd-a-scan}:*" in async <adapter_type>
    Then the found keys should include "{bdd-a-scan}:1" and "{bdd-a-scan}:2"
    When I scan keys matching "{bdd-a-scan}:*" in async <adapter_type>
    Then the scanned keys should include "{bdd-a-scan}:1" and "{bdd-a-scan}:2"

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  @async
  Scenario Outline: Lpush and lpop preserve order asynchronously
    Given a configured async <adapter_type>
    When I lpush "first, second" to list "bdd-a-mylist" in async <adapter_type>
    Then the async list "bdd-a-mylist" should have 2 items
    When I lpop from list "bdd-a-mylist" in async <adapter_type>
    Then the async popped value should be "second"

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  @async
  Scenario Outline: Rpop and lrem modify list asynchronously
    Given a configured async <adapter_type>
    When I add "a, b, a, c" to the list "bdd-a-rlist" in async <adapter_type>
    When I rpop from list "bdd-a-rlist" in async <adapter_type>
    Then the async popped value should be "c"
    When I lrem 1 "a" from list "bdd-a-rlist" in async <adapter_type>
    Then the async list "bdd-a-rlist" should have 2 items
    When I lset index 0 to "x" in list "bdd-a-rlist" in async <adapter_type>
    And I fetch all items from the list "bdd-a-rlist" in async <adapter_type>
    Then the async list "bdd-a-rlist" should contain "x, a"

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  @async
  Scenario Outline: Set membership and removal asynchronously
    Given a configured async <adapter_type>
    When I add "alpha, beta" to the set "bdd-a-myset" in async <adapter_type>
    When I check if "alpha" is a member of set "bdd-a-myset" in async <adapter_type>
    Then the async set membership should be true
    When I check if "gamma" is a member of set "bdd-a-myset" in async <adapter_type>
    Then the async set membership should be false
    When I remove "alpha" from set "bdd-a-myset" in async <adapter_type>
    Then the async set "bdd-a-myset" should have 1 members
    When I spop from set "bdd-a-myset" in async <adapter_type>
    Then the async set "bdd-a-myset" should have 0 members

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  @async
  Scenario Outline: Set union across hash-tagged sets asynchronously
    Given a configured async <adapter_type>
    When I add "a, b" to the set "{bdd-a-su}:1" in async <adapter_type>
    And I add "b, c" to the set "{bdd-a-su}:2" in async <adapter_type>
    When I union sets "{bdd-a-su}:1" and "{bdd-a-su}:2" in async <adapter_type>
    Then the async set union should contain "a, b, c"

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  @async
  Scenario Outline: Manage sorted set members asynchronously
    Given a configured async <adapter_type>
    When I zadd members "alice=10,bob=20" to sorted set "bdd-a-leaderboard" in async <adapter_type>
    Then the async sorted set "bdd-a-leaderboard" should have 2 members
    When I get zscore of "alice" in sorted set "bdd-a-leaderboard" in async <adapter_type>
    Then the async zscore should be 10.0
    When I get zrank of "bob" in sorted set "bdd-a-leaderboard" in async <adapter_type>
    Then the async zrank should be 1
    When I zrange sorted set "bdd-a-leaderboard" from 0 to -1 in async <adapter_type>
    Then the async zrange members should be "alice, bob"
    When I zrevrange sorted set "bdd-a-leaderboard" from 0 to -1 in async <adapter_type>
    Then the async zrange members should be "bob, alice"
    When I zrangebyscore sorted set "bdd-a-leaderboard" from 10 to 20 in async <adapter_type>
    Then the async zrange members should be "alice, bob"
    When I zcount sorted set "bdd-a-leaderboard" from 10 to 15 in async <adapter_type>
    Then the async zcount should be 1
    When I zincrby 5 "alice" in sorted set "bdd-a-leaderboard" in async <adapter_type>
    Then the async zscore should be 15.0
    When I zrem "bob" from sorted set "bdd-a-leaderboard" in async <adapter_type>
    Then the async sorted set "bdd-a-leaderboard" should have 1 members
    When I zpopmax from sorted set "bdd-a-leaderboard" in async <adapter_type>
    Then the async zpop result should be "alice"

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  @async
  Scenario Outline: Hash field operations asynchronously
    Given a configured async <adapter_type>
    When I hset mapping "name=Alice,email=alice@test.com" in hash "bdd-a-user" in async <adapter_type>
    Then the async hash "bdd-a-user" should have 2 fields
    When I check if field "name" exists in hash "bdd-a-user" in async <adapter_type>
    Then the async hash field exists should be true
    When I hmget fields "name,email" from hash "bdd-a-user" in async <adapter_type>
    Then the async hmget values should be "Alice,alice@test.com"
    When I fetch all fields from hash "bdd-a-user" in async <adapter_type>
    Then the async hash keys should be "email, name"
    And the async hash values should be "alice@test.com, Alice"
    When I delete field "email" from hash "bdd-a-user" in async <adapter_type>
    Then the async hash "bdd-a-user" should have 1 fields

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  @async
  Scenario Outline: Publish message to channel asynchronously
    Given a configured async <adapter_type>
    When I publish "hello" to channel "bdd-a-test-channel" in async <adapter_type>
    Then the async publish count should be at least 0

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  @async
  Scenario Outline: Subscribe and receive published message asynchronously
    Given a configured async <adapter_type>
    When I subscribe to channel "bdd-a-pubsub-container-channel" in async <adapter_type>
    And I publish "greeting" to channel "bdd-a-pubsub-container-channel" in async <adapter_type>
    Then the async subscribed message should be "greeting"

    Examples: Adapter Types
      | adapter_type |
      | container    |

  @async
  Scenario Outline: Pipeline executes commands asynchronously
    Given a configured async <adapter_type>
    When I run pipeline setting "{<pipe_tag>}:k" to "v" and incrementing "{<pipe_tag>}:cnt" by 1 in async <adapter_type>
    Then the async pipeline results should be "True, 1, v"
    When I retrieve the value for key "{<pipe_tag>}:k" from async <adapter_type>
    Then the async retrieved value should be "v"

    Examples: Pipeline keys
      | adapter_type | pipe_tag       |
      | container    | bdd-a-p-cont   |
      | cluster      | bdd-a-p-clust  |

  # Redis 8.8 — Array data structure
  Scenario Outline: Store and retrieve array elements
    Given a configured <adapter_type>
    When I arset index 0 to "alpha, beta, gamma" in array "bdd-s-array" in <adapter_type>
    Then the sync array "bdd-s-array" should have 3 elements
    When I get array index 1 from "bdd-s-array" in <adapter_type>
    Then the sync array value should be "beta"
    When I delete array index 0 from "bdd-s-array" in <adapter_type>
    And I get array index 0 from "bdd-s-array" in <adapter_type>
    Then the sync array value should be "None"

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  Scenario Outline: Array ring buffer retains last N elements
    Given a configured <adapter_type>
    When I arring size 2 with "first, second, third" into array "bdd-s-ring" in <adapter_type>
    And I get array index 0 from "bdd-s-ring" in <adapter_type>
    Then the sync array value should be "third"
    When I get array index 1 from "bdd-s-ring" in <adapter_type>
    Then the sync array value should be "second"

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  @async
  Scenario Outline: Store and retrieve array elements asynchronously
    Given a configured async <adapter_type>
    When I arset index 0 to "alpha, beta, gamma" in array "bdd-a-array" in async <adapter_type>
    Then the async array "bdd-a-array" should have 3 elements
    When I get array index 1 from "bdd-a-array" in async <adapter_type>
    Then the async array value should be "beta"

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  @async
  Scenario Outline: Array ring buffer retains last N elements asynchronously
    Given a configured async <adapter_type>
    When I arring size 2 with "first, second, third" into array "bdd-a-ring" in async <adapter_type>
    And I get array index 0 from "bdd-a-ring" in async <adapter_type>
    Then the async array value should be "third"
    When I get array index 1 from "bdd-a-ring" in async <adapter_type>
    Then the async array value should be "second"

    Examples: Adapter Types
      | adapter_type |
      | mock         |
      | container    |
      | cluster      |

  # Redis 8.8 — INCREX window counter rate limiter (requires Redis 8.8+)
  Scenario Outline: INCREX respects upper bound for rate limiting
    Given a configured <adapter_type>
    When I increx key "bdd-s-rl" by 1 with upper bound 3 and expiry 60 seconds in <adapter_type>
    Then the sync increx counter should be 1
    And the sync increx applied increment should be 1
    When I increx key "bdd-s-rl" by 1 with upper bound 3 and expiry 60 seconds in <adapter_type>
    Then the sync increx counter should be 2
    When I increx key "bdd-s-rl" by 1 with upper bound 3 and expiry 60 seconds in <adapter_type>
    Then the sync increx counter should be 3
    When I increx key "bdd-s-rl" by 1 with upper bound 3 and expiry 60 seconds in <adapter_type>
    Then the sync increx counter should be 3
    And the sync increx applied increment should be 0

    Examples: Adapter Types
      | adapter_type |
      | container    |
      | cluster      |

  @async
  Scenario Outline: INCREX respects upper bound for rate limiting asynchronously
    Given a configured async <adapter_type>
    When I increx key "bdd-a-rl" by 1 with upper bound 3 and expiry 60 seconds in async <adapter_type>
    Then the async increx counter should be 1
    And the async increx applied increment should be 1
    When I increx key "bdd-a-rl" by 1 with upper bound 3 and expiry 60 seconds in async <adapter_type>
    Then the async increx counter should be 2
    When I increx key "bdd-a-rl" by 1 with upper bound 3 and expiry 60 seconds in async <adapter_type>
    Then the async increx counter should be 3
    When I increx key "bdd-a-rl" by 1 with upper bound 3 and expiry 60 seconds in async <adapter_type>
    Then the async increx applied increment should be 0

    Examples: Adapter Types
      | adapter_type |
      | container    |
      | cluster      |

  # Redis 8.8 — ZUNION/ZINTER COUNT aggregator (requires Redis 8.8+)
  Scenario Outline: ZUNION COUNT aggregator scores by set membership
    Given a configured <adapter_type>
    When I zadd members "a=1,b=2" to sorted set "{bdd-s-zc}:1" in <adapter_type>
    And I zadd members "b=3,c=4" to sorted set "{bdd-s-zc}:2" in <adapter_type>
    When I zunion sets "{bdd-s-zc}:1" and "{bdd-s-zc}:2" with COUNT aggregator in <adapter_type>
    Then the sync zunion COUNT score for "b" should be 2.0
    And the sync zunion COUNT score for "a" should be 1.0

    Examples: Adapter Types
      | adapter_type |
      | container    |
      | cluster      |

  Scenario Outline: ZINTER COUNT aggregator scores by set membership
    Given a configured <adapter_type>
    When I zadd members "a=1,b=2" to sorted set "{bdd-s-zi}:1" in <adapter_type>
    And I zadd members "b=3,c=4" to sorted set "{bdd-s-zi}:2" in <adapter_type>
    When I zinter sets "{bdd-s-zi}:1" and "{bdd-s-zi}:2" with COUNT aggregator in <adapter_type>
    Then the sync zinter COUNT score for "b" should be 2.0

    Examples: Adapter Types
      | adapter_type |
      | container    |
      | cluster      |

  @async
  Scenario Outline: ZUNION COUNT aggregator scores by set membership asynchronously
    Given a configured async <adapter_type>
    When I zadd members "a=1,b=2" to sorted set "{bdd-a-zc}:1" in async <adapter_type>
    And I zadd members "b=3,c=4" to sorted set "{bdd-a-zc}:2" in async <adapter_type>
    When I zunion sets "{bdd-a-zc}:1" and "{bdd-a-zc}:2" with COUNT aggregator in async <adapter_type>
    Then the async zunion COUNT score for "b" should be 2.0

    Examples: Adapter Types
      | adapter_type |
      | container    |
      | cluster      |

  # Redis 8.8 — Hash subkey notifications (requires Redis 8.8+)
  Scenario Outline: Receive hash subkey notification on field update
    Given a configured <adapter_type>
    When I enable hash subkey notifications in <adapter_type>
    And I psubscribe to subkeyevent hset channel in <adapter_type>
    And I assign "name" to "Alice" in the hash "bdd-s-subhash" in <adapter_type>
    Then the sync subkey notification should include field "name"

    Examples: Adapter Types
      | adapter_type |
      | container    |

  @async
  Scenario Outline: Receive hash subkey notification on field update asynchronously
    Given a configured async <adapter_type>
    When I enable hash subkey notifications in async <adapter_type>
    And I psubscribe to subkeyevent hset channel in async <adapter_type>
    And I assign "email" to "bob@test.com" in the hash "bdd-a-subhash" in async <adapter_type>
    Then the async subkey notification should include field "email"

    Examples: Adapter Types
      | adapter_type |
      | container    |

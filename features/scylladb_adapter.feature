Feature: ScyllaDB Adapter
  As a developer
  I want to interact with ScyllaDB using the adapter
  So that I can perform database operations in a consistent manner

  Background:
    Given a ScyllaDB test container is running

  @needs-scylladb
  Scenario: Create and use keyspace
    Given a ScyllaDB adapter is configured
    When I create a keyspace "test_keyspace" with replication factor 1
    Then the keyspace "test_keyspace" should be created successfully
    When I use keyspace "test_keyspace"
    Then the keyspace context should be "test_keyspace"

  @needs-scylladb
  Scenario: Create table and insert single row
    Given a ScyllaDB adapter is configured
    And a keyspace "test_ks" with replication factor 1 exists
    When I create a table "users" with schema "CREATE TABLE IF NOT EXISTS users (id int PRIMARY KEY, name text, age int)"
    And I insert data into table "users" with id 1, name "Alice", age 30
    Then the table "users" should contain 1 row

  @needs-scylladb
  Scenario: Insert multiple rows and select all
    Given a ScyllaDB adapter is configured
    And a keyspace "test_ks" with replication factor 1 exists
    And a table "products" with schema "CREATE TABLE IF NOT EXISTS products (id int PRIMARY KEY, name text, price double)"
    When I insert data into table "products" with id 1, name "Laptop", price 999.99
    And I insert data into table "products" with id 2, name "Mouse", price 25.50
    And I insert data into table "products" with id 3, name "Keyboard", price 75.00
    Then the table "products" should contain 3 rows

  @needs-scylladb
  Scenario: Select data with WHERE conditions
    Given a ScyllaDB adapter is configured
    And a keyspace "test_ks" with replication factor 1 exists
    And a table "employees" with schema "CREATE TABLE IF NOT EXISTS employees (id int PRIMARY KEY, name text, department text)"
    And data exists in table "employees":
      | id | name | department |
      | 1  | John | IT         |
      | 2  | Jane | HR         |
      | 3  | Bob  | IT         |
    When I select from table "employees" where id equals 2
    Then the result should contain 1 row
    And the result row should have name "Jane" and department "HR"

  @needs-scylladb
  Scenario: Update data in table
    Given a ScyllaDB adapter is configured
    And a keyspace "test_ks" with replication factor 1 exists
    And a table "inventory" with schema "CREATE TABLE IF NOT EXISTS inventory (id int PRIMARY KEY, item text, quantity int)"
    And data exists in table "inventory":
      | id | item   | quantity |
      | 1  | Widget | 100      |
    When I update table "inventory" setting quantity to 150 where id equals 1
    And I select from table "inventory" where id equals 1
    Then the result row should have quantity 150

  @needs-scylladb
  Scenario: Delete data from table
    Given a ScyllaDB adapter is configured
    And a keyspace "test_ks" with replication factor 1 exists
    And a table "sessions_delete" with schema "CREATE TABLE IF NOT EXISTS sessions_delete (id int PRIMARY KEY, user_id int, active boolean)"
    And data exists in table "sessions_delete":
      | id | user_id | active |
      | 1  | 101     | true   |
      | 2  | 102     | true   |
    When I delete from table "sessions_delete" where id equals 1
    Then the table "sessions_delete" should contain 1 row

  @needs-scylladb
  Scenario: Execute prepared statement
    Given a ScyllaDB adapter is configured
    And a keyspace "test_ks" with replication factor 1 exists
    And a table "logs" with schema "CREATE TABLE IF NOT EXISTS logs (id int PRIMARY KEY, message text, level text)"
    When I prepare statement "INSERT INTO logs (id, message, level) VALUES (:id, :message, :level)"
    And I execute prepared statement with id 1, message "Test log", level "INFO"
    Then the table "logs" should contain 1 row

  @needs-scylladb
  Scenario: Batch insert operations
    Given a ScyllaDB adapter is configured
    And a keyspace "test_ks" with replication factor 1 exists
    And a table "orders" with schema "CREATE TABLE IF NOT EXISTS orders (id int PRIMARY KEY, customer text, amount double)"
    When I execute batch statements:
      | INSERT INTO orders (id, customer, amount) VALUES (1, 'Customer A', 100.00) |
      | INSERT INTO orders (id, customer, amount) VALUES (2, 'Customer B', 200.00) |
      | INSERT INTO orders (id, customer, amount) VALUES (3, 'Customer C', 300.00) |
    Then the table "orders" should contain 3 rows

  @needs-scylladb
  Scenario: Drop table
    Given a ScyllaDB adapter is configured
    And a keyspace "test_ks" with replication factor 1 exists
    And a table "temp_data" with schema "CREATE TABLE IF NOT EXISTS temp_data (id int PRIMARY KEY, data text)"
    When I drop table "temp_data"
    Then the table "temp_data" should not exist

  @needs-scylladb
  Scenario: Drop keyspace
    Given a ScyllaDB adapter is configured
    And a keyspace "temp_keyspace" with replication factor 1 exists
    When I drop keyspace "temp_keyspace"
    Then the keyspace "temp_keyspace" should not exist

  @needs-scylladb @async
  Scenario: Async create keyspace and table
    Given an async ScyllaDB adapter is configured
    When I async create a keyspace "async_ks" with replication factor 1
    And I async use keyspace "async_ks"
    And I async create a table "async_users" with schema "CREATE TABLE IF NOT EXISTS async_users (id int PRIMARY KEY, name text)"
    And I async insert data into table "async_users" with id 1, name "AsyncUser"
    Then the async table "async_users" should contain 1 row

  @needs-scylladb @async
  Scenario: Async batch operations
    Given an async ScyllaDB adapter is configured
    And an async keyspace "async_ks" with replication factor 1 exists
    And an async table "async_orders" with schema "CREATE TABLE IF NOT EXISTS async_orders (id int PRIMARY KEY, total double)"
    When I async execute batch statements:
      | INSERT INTO async_orders (id, total) VALUES (1, 50.00)  |
      | INSERT INTO async_orders (id, total) VALUES (2, 100.00) |
    Then the async table "async_orders" should contain 2 rows

  @needs-scylladb @async
  Scenario: Async prepared statement
    Given an async ScyllaDB adapter is configured
    And an async keyspace "async_ks" with replication factor 1 exists
    And an async table "async_logs" with schema "CREATE TABLE IF NOT EXISTS async_logs (id int PRIMARY KEY, msg text)"
    When I async prepare statement "INSERT INTO async_logs (id, msg) VALUES (:id, :msg)"
    And I async execute prepared statement with id 1, msg "Async log message"
    Then the async table "async_logs" should contain 1 row

  @needs-scylladb
  Scenario: Count rows in table
    Given a ScyllaDB adapter is configured
    And a keyspace "test_ks" with replication factor 1 exists
    And a table "items" with schema "CREATE TABLE IF NOT EXISTS items (id int PRIMARY KEY, name text, category text)"
    And data exists in table "items":
      | id | name   | category |
      | 1  | Item A | cat1     |
      | 2  | Item B | cat1     |
      | 3  | Item C | cat2     |
    When I count rows in table "items"
    Then the count result should be 3
    When I count rows in table "items" with conditions category "cat1"
    Then the count result should be 2

  @needs-scylladb
  Scenario: Check if row exists
    Given a ScyllaDB adapter is configured
    And a keyspace "test_ks" with replication factor 1 exists
    And a table "users_exists" with schema "CREATE TABLE IF NOT EXISTS users_exists (id int PRIMARY KEY, username text, active boolean)"
    And data exists in table "users_exists":
      | id | username | active |
      | 1  | alice    | true   |
      | 2  | bob      | false  |
    When I check if row exists in table "users_exists" with id 1
    Then the row should exist
    When I check if row exists in table "users_exists" with id 999
    Then the row should not exist

  @needs-scylladb @async
  Scenario: Async count rows in table
    Given an async ScyllaDB adapter is configured
    And an async keyspace "async_ks" with replication factor 1 exists
    And an async table "async_items" with schema "CREATE TABLE IF NOT EXISTS async_items (id int PRIMARY KEY, name text)"
    When I async insert data into table "async_items" with id 1, name "Item1"
    And I async insert data into table "async_items" with id 2, name "Item2"
    And I async insert data into table "async_items" with id 3, name "Item3"
    When I async count rows in table "async_items"
    Then the async count result should be 3

  @needs-scylladb @async
  Scenario: Async check if row exists
    Given an async ScyllaDB adapter is configured
    And an async keyspace "async_ks" with replication factor 1 exists
    And an async table "async_users" with schema "CREATE TABLE IF NOT EXISTS async_users (id int PRIMARY KEY, name text)"
    When I async insert data into table "async_users" with id 1, name "User1"
    When I async check if row exists in table "async_users" with id 1
    Then the async row should exist
    When I async check if row exists in table "async_users" with id 999
    Then the async row should not exist

  @needs-scylladb
  Scenario: Insert with TTL
    Given a ScyllaDB adapter is configured
    And a keyspace "test_ks" with replication factor 1 exists
    And a table "cache" with schema "CREATE TABLE IF NOT EXISTS cache (key text PRIMARY KEY, value text)"
    When I insert data into table "cache" with key "temp_key", value "temp_value", ttl 3600
    Then the table "cache" should contain 1 row

  @needs-scylladb
  Scenario: Update with TTL
    Given a ScyllaDB adapter is configured
    And a keyspace "test_ks" with replication factor 1 exists
    And a table "sessions_ttl" with schema "CREATE TABLE IF NOT EXISTS sessions_ttl (session_id text PRIMARY KEY, data text)"
    And data exists in table "sessions_ttl":
      | session_id | data     |
      | sess1      | old_data |
    When I update table "sessions_ttl" setting data to "new_data" with ttl 7200 where session_id equals "sess1"
    And I select from table "sessions_ttl" where session_id equals "sess1"
    Then the result row should have data "new_data"

  @needs-scylladb @async
  Scenario: Async insert with TTL
    Given an async ScyllaDB adapter is configured
    And an async keyspace "async_ks" with replication factor 1 exists
    And an async table "async_cache" with schema "CREATE TABLE IF NOT EXISTS async_cache (key text PRIMARY KEY, value text)"
    When I async insert data into table "async_cache" with key "temp", value "data", ttl 3600
    Then the async table "async_cache" should contain 1 row

  @needs-scylladb
  Scenario: Get connection pool statistics
    Given a ScyllaDB adapter is configured
    When I get pool statistics
    Then the pool statistics should be returned

  @needs-scylladb
  Scenario: Insert with If Not Exists
    Given a ScyllaDB adapter is configured
    And a keyspace "test_ks" with replication factor 1 exists
    And a table "inventory" with schema "CREATE TABLE IF NOT EXISTS inventory (id int PRIMARY KEY, item text, quantity int)"
    And data exists in table "inventory":
      | id | item   | quantity |
      | 1  | Widget | 100      |
    When I insert data into table "inventory" with id 1, item "some_item", quantity 500
    Then the table "inventory" should contain 1 row

  @needs-scylladb @async
  Scenario: Async Insert with If Not Exists
    Given an async ScyllaDB adapter is configured
    And an async keyspace "test_ks" with replication factor 1 exists
    And an async table "async_inventory" with schema "CREATE TABLE IF NOT EXISTS async_inventory (id int PRIMARY KEY, item text, quantity int)"
    And data exists in table "async_inventory":
      | id | item   | quantity |
      | 1  | Widget | 100      |
    When I async insert data into table "async_inventory" with id 1, item "some_item", quantity 500
    Then the async table "async_inventory" should contain 1 row

  @needs-scylladb @needs-otel-collector
  Scenario: ScyllaDB queries emit Cassandra spans
    Given adapter spans are exported to the collector
    When I run a query through the ScyllaDB adapter
    Then the collector should have a span with attribute "db.system" containing "cassandra"

  @async @needs-scylladb @needs-otel-collector
  Scenario: Async ScyllaDB queries emit Cassandra spans
    Given adapter spans are exported to the collector
    When I run a query through the async ScyllaDB adapter
    Then the collector should have a span with attribute "db.system" containing "cassandra"

  @needs-scylladb
  Scenario Outline: CRUD round trip through the adapter
    Given a ScyllaDB adapter with keyspace "hot_ks" and a users table "<table>"
    When I run ScyllaDB operation "insert" on table "<table>"
    And I run ScyllaDB operation "select" on table "<table>"
    Then the ScyllaDB result should be "alpha"
    When I run ScyllaDB operation "select columns" on table "<table>"
    Then the ScyllaDB result should be "alpha:False"
    When I run ScyllaDB operation "update" on table "<table>"
    And I run ScyllaDB operation "select" on table "<table>"
    Then the ScyllaDB result should be "beta"
    When I run ScyllaDB operation "insert if not exists" on table "<table>"
    And I run ScyllaDB operation "select" on table "<table>"
    Then the ScyllaDB result should be "beta"
    When I run ScyllaDB operation "count" on table "<table>"
    Then the ScyllaDB result should be "1"
    When I run ScyllaDB operation "exists" on table "<table>"
    Then the ScyllaDB result should be "True"
    When I run ScyllaDB operation "delete" on table "<table>"
    And I run ScyllaDB operation "select" on table "<table>"
    Then the ScyllaDB result should be empty
    When I run ScyllaDB operation "exists" on table "<table>"
    Then the ScyllaDB result should be "False"

    Examples: Sync
      | table    |
      | crud_syn |

    @async
    Examples: Async
      | table     |
      | crud_asyn |

  @needs-scylladb
  Scenario Outline: Operations on a missing table fail with NotFoundError
    Given a ScyllaDB adapter with keyspace "hot_ks" and a users table "present_<mode>"
    When I run ScyllaDB operation "<operation>" on table "missing_<mode>"
    Then the ScyllaDB call should raise NotFoundError

    Examples: Sync
      | mode | operation |
      | syn  | select    |
      | syn  | insert    |
      | syn  | update    |
      | syn  | delete    |
      | syn  | count     |
      | syn  | exists    |

    @async
    Examples: Async
      | mode | operation |
      | asyn | select    |
      | asyn | insert    |
      | asyn | update    |
      | asyn | delete    |
      | asyn | count     |
      | asyn | exists    |

  @needs-scylladb
  Scenario Outline: Invalid CQL and identifiers are translated to ArchiPy errors
    Given a ScyllaDB adapter with keyspace "hot_ks" and a users table "bad_<mode>"
    When I run ScyllaDB <kind> with CQL "<cql>"
    Then the ScyllaDB call should raise <error>

    Examples: Sync
      | mode | kind    | cql                                           | error                |
      | syn  | execute | SELECT * FROM missing_table_syn               | NotFoundError        |
      | syn  | prepare | SELECT * FROM missing_table_syn               | NotFoundError        |
      | syn  | batch   | INSERT INTO missing_table_syn (id) VALUES (1) | NotFoundError        |
      | syn  | execute | SELECT FROM WHERE                             | InvalidArgumentError |

    @async
    Examples: Async
      | mode | kind    | cql                                            | error                |
      | asyn | execute | SELECT * FROM missing_table_asyn               | NotFoundError        |
      | asyn | prepare | SELECT * FROM missing_table_asyn               | NotFoundError        |
      | asyn | batch   | INSERT INTO missing_table_asyn (id) VALUES (1) | NotFoundError        |
      | asyn | execute | SELECT FROM WHERE                              | InvalidArgumentError |

  @needs-scylladb
  Scenario Outline: Values interpolated into CQL are rejected unless they are non-negative integers
    Given a ScyllaDB adapter with keyspace "hot_ks" and a users table "inj_<mode>"
    When I run ScyllaDB operation "<operation>" on table "inj_<mode>"
    Then the ScyllaDB call should raise InvalidArgumentError

    Examples: Sync
      | mode | operation                                        |
      | syn  | insert with injected ttl                         |
      | syn  | update with injected ttl                         |
      | syn  | insert with negative ttl                         |
      | syn  | create keyspace with injected replication factor |

    @async
    Examples: Async
      | mode | operation                                        |
      | asyn | insert with injected ttl                         |
      | asyn | update with injected ttl                         |
      | asyn | insert with negative ttl                         |
      | asyn | create keyspace with injected replication factor |

  @needs-scylladb
  Scenario Outline: CRUD helpers prepare their statements and reuse them
    Given a ScyllaDB adapter with keyspace "hot_ks" and a users table "prep_<mode>"
    When I run ScyllaDB operation "insert" on table "prep_<mode>"
    Then the ScyllaDB driver should hold 1 prepared statements
    When I run ScyllaDB operation "select" on table "prep_<mode>"
    And I run ScyllaDB operation "select" on table "prep_<mode>"
    Then the ScyllaDB result should be "alpha"
    And the ScyllaDB driver should hold 2 prepared statements

  Scenario Outline: Select honours an optional limit and rejects invalid ones
    Given a ScyllaDB adapter with keyspace "hot_ks" and a users table "lim_<mode>"
    When I run ScyllaDB operation "select with limit" on table "lim_<mode>"
    Then the ScyllaDB result should be "2"
    When I run ScyllaDB operation "<operation>" on table "lim_<mode>"
    Then the ScyllaDB call should raise InvalidArgumentError

    Examples: Sync
      | mode | operation                  |
      | syn  | select with zero limit     |
      | syn  | select with injected limit |

    @async
    Examples: Async
      | mode | operation                  |
      | asyn | select with zero limit     |
      | asyn | select with injected limit |

  Scenario Outline: Driver exceptions are mapped by type
    When I map the ScyllaDB driver exception "<exception>"
    Then the ScyllaDB call should raise <error>

    Examples: Exceptions
      | exception                                      | error                   |
      | OperationTimedOut                              | ConnectionTimeoutError  |
      | ReadTimeout                                    | ConnectionTimeoutError  |
      | Unavailable                                    | ServiceUnavailableError |
      | NoHostAvailable                                | ServiceUnavailableError |
      | AuthenticationFailed                           | InvalidCredentialsError |
      | ProtocolVersionUnsupported                     | ConfigurationError      |
      | ConnectionShutdown                             | NetworkError            |
      | unrelated message about timeout and connection | DatabaseQueryError      |

  @needs-scylladb
  Scenario: A driver timeout reports its value
    When I map the ScyllaDB driver exception "OperationTimedOut"
    Then the ScyllaDB error should carry timeout 7

  @needs-scylladb
  Scenario Outline: A missing table error names the table
    Given a ScyllaDB adapter with keyspace "hot_ks" and a users table "named_<mode>"
    When I run ScyllaDB operation "select" on table "absent_<mode>"
    Then the NotFoundError should name table "absent_<mode>"

    Examples: Sync
      | mode |
      | syn  |

    @async
    Examples: Async
      | mode |
      | asyn |

  @needs-scylladb
  Scenario Outline: Prepared statements are cached and executed with bound parameters
    Given a ScyllaDB adapter with keyspace "hot_ks" and a users table "<table>"
    When I execute a prepared ScyllaDB insert into "<table>" twice
    Then the prepared ScyllaDB statement should have been reused
    And the table "<table>" should contain 2 rows

    Examples: Sync
      | table    |
      | prep_syn |

  @needs-scylladb @async
  Scenario: Async prepared statements are cached and executed with bound parameters
    Given a ScyllaDB adapter with keyspace "hot_ks" and a users table "prep_asyn"
    When I execute a prepared ScyllaDB insert into "prep_asyn" twice
    Then the prepared ScyllaDB statement should have been reused
    And the async table "prep_asyn" should contain 2 rows

  @needs-scylladb
  Scenario Outline: Closed adapter reports unhealthy and rejects queries
    Given a ScyllaDB adapter with keyspace "hot_ks" and a users table "life_<mode>"
    When I check the ScyllaDB adapter health
    Then the ScyllaDB adapter should report connected "True" and health "healthy"
    When I read the ScyllaDB pool statistics with monitoring enabled
    Then the ScyllaDB pool statistics should list the connected host
    When I close the ScyllaDB adapter
    And I check the ScyllaDB adapter health
    Then the ScyllaDB adapter should report connected "False" and health "unhealthy"
    When I run ScyllaDB operation "select" on table "life_<mode>"
    Then the ScyllaDB call should raise ServiceUnavailableError

    Examples: Sync
      | mode |
      | syn  |

    @async
    Examples: Async
      | mode |
      | asyn |

  @needs-scylladb
  Scenario Outline: Failing probes do not reveal driver errors or hosts
    Given a ScyllaDB adapter is configured
    When I check the health and pool statistics of an adapter whose session fails
    Then the ScyllaDB probe responses should not contain the driver error text

    Examples: Sync
      | mode |
      | syn  |

    @async
    Examples: Async
      | mode |
      | asyn |

  @needs-scylladb
  Scenario Outline: The default execution profile uses the configured consistency level
    Given a ScyllaDB adapter is configured
    When I build a ScyllaDB cluster with consistency level <level>
    Then the default execution profile should use consistency level <level>

    Examples: Levels
      | level        |
      | ONE          |
      | LOCAL_ONE    |
      | LOCAL_QUORUM |
      | QUORUM       |

  @needs-scylladb
  Scenario Outline: The cluster applies policies and timeout through the default execution profile with <setting> set
    When I build a ScyllaDB cluster with <setting> set to <value>
    Then the default execution profile should use the configured request timeout and retry policy
    And a DeprecationWarning should <warning>

    Examples: Pool settings
      | setting                     | value | warning                         |
      | MAX_CONNECTIONS_PER_HOST    | 4     | name "MAX_CONNECTIONS_PER_HOST" |
      | MAX_REQUESTS_PER_CONNECTION | 100   | not be raised                   |

  @needs-scylladb
  Scenario Outline: The cluster and default profile apply the <profile> resilience settings
    When I build a ScyllaDB cluster with the resilience profile <profile>
    Then the cluster and default profile should reflect the <profile> resilience profile

    Examples: Resilience profiles
      | profile                |
      | driver defaults        |
      | constant reconnect     |
      | exponential reconnect  |
      | heartbeat and timeouts |
      | serial consistency     |
      | speculative execution  |

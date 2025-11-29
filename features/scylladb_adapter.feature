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
      | id | name    | department |
      | 1  | John    | IT         |
      | 2  | Jane    | HR         |
      | 3  | Bob     | IT         |
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
    And a table "sessions" with schema "CREATE TABLE IF NOT EXISTS sessions (id int PRIMARY KEY, user_id int, active boolean)"
    And data exists in table "sessions":
      | id | user_id | active |
      | 1  | 101     | true   |
      | 2  | 102     | true   |
    When I delete from table "sessions" where id equals 1
    Then the table "sessions" should contain 1 row

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

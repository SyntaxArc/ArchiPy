# features/elasticsearch.feature
Feature: Elasticsearch Operations Testing
  As a developer
  I want to test Elasticsearch operations using the adapter pattern
  So that I can ensure proper interaction with the Elasticsearch cluster through our standardized interface

  Background:
    Given an Elasticsearch cluster is running
    And document type "test-doc" is configured for index "test-index"

  Scenario: Index a new document synchronously
    Given a valid Elasticsearch client connection
    And index "test-index" exists
    When I index a document with id "1" and content '{"title": "Test Document", "content": "This is a test"}' into "test-index"
    Then the indexing operation should succeed
    And the document should be retrievable by id "1" from "test-index"

  Scenario: Search for documents synchronously
    Given a valid Elasticsearch client connection
    And index "test-index" exists
    And a document exists in "test-index" with id "1" and content '{"title": "Test Document", "content": "This is a test"}'
    When I search for "Test Document" in "test-index"
    Then the search should return at least 1 hit
    And the hit should contain field "title" with value "Test Document"

  Scenario: Update a document synchronously
    Given a valid Elasticsearch client connection
    And index "test-index" exists
    And a document exists in "test-index" with id "1" and content '{"title": "Test Document", "content": "This is a test"}'
    When I update document "1" in "test-index" with content '{"doc": {"title": "Updated Document", "content": "This is an update"}}'
    Then the update operation should succeed
    And the document should reflect the updated content when retrieved

  Scenario: Delete a document synchronously
    Given a valid Elasticsearch client connection
    And index "test-index" exists
    And a document exists in "test-index" with id "1" and content '{"title": "Test Document", "content": "This is a test"}'
    When I delete document "1" from "test-index"
    Then the delete operation should succeed
    And the document should not exist when searched for

  Scenario: Create a new index synchronously
    Given a valid Elasticsearch client connection
    When I create index "new-test-index" with 1 shard and 1 replica
    Then the index creation should succeed
    And index "new-test-index" should exist in the cluster

  Scenario: Delete an index synchronously
    Given a valid Elasticsearch client connection
    And index "temp-index" exists
    When I delete index "temp-index"
    Then the index deletion should succeed
    And index "temp-index" should not exist in the cluster

  Scenario: Perform bulk operations synchronously
    Given a valid Elasticsearch client connection
    And index "test-index" exists
    And a document exists in "test-index" with id "1" and content '{"title": "Test Document", "content": "This is a test"}'
    When I perform a bulk operation with:
      | action  | id | index       | document                                  |
      | index   | 2  | test-index  | {"title": "Doc 2", "content": "Second"}  |
      | index   | 3  | test-index  | {"title": "Doc 3", "content": "Third"}   |
      | update  | 1  | test-index  | {"doc": {"content": "Bulk updated"}}     |
      | delete  | 4  | test-index  |                                          |
    Then the bulk operation should succeed
    And all operations should be reflected in the index

  @async
  Scenario: Index a new document asynchronously
    Given a valid Elasticsearch client connection
    And index "test-index" exists
    When I index a document with id "10" and content '{"title": "Async Doc", "content": "Async test"}' into "test-index"
    Then the indexing operation should succeed
    And the document should be retrievable by id "10" from "test-index"

  @async
  Scenario: Search for documents asynchronously
    Given a valid Elasticsearch client connection
    And index "test-index" exists
    And a document exists in "test-index" with id "10" and content '{"title": "Async Doc", "content": "Async test"}'
    When I search for "Async Doc" in "test-index"
    Then the search should return at least 1 hit
    And the hit should contain field "title" with value "Async Doc"

  @async
  Scenario: Update a document asynchronously
    Given a valid Elasticsearch client connection
    And index "test-index" exists
    And a document exists in "test-index" with id "10" and content '{"title": "Async Doc", "content": "Async test"}'
    When I update document "10" in "test-index" with content '{"doc": {"title": "Updated Async", "content": "Updated async"}}'
    Then the update operation should succeed
    And the document should reflect the updated content when retrieved

  @async
  Scenario: Delete a document asynchronously
    Given a valid Elasticsearch client connection
    And index "test-index" exists
    And a document exists in "test-index" with id "10" and content '{"title": "Async Doc", "content": "Async test"}'
    When I delete document "10" from "test-index"
    Then the delete operation should succeed
    And the document should not exist when searched for

  @async
  Scenario: Create a new index asynchronously
    Given a valid Elasticsearch client connection
    When I create index "new-async-index" with 1 shard and 1 replica
    Then the index creation should succeed
    And index "new-async-index" should exist in the cluster

  @async
  Scenario: Delete an index asynchronously
    Given a valid Elasticsearch client connection
    And index "temp-async-index" exists
    When I delete index "temp-async-index"
    Then the index deletion should succeed
    And index "temp-async-index" should not exist in the cluster

  @async
  Scenario: Perform bulk operations asynchronously
    Given a valid Elasticsearch client connection
    And index "test-index" exists
    And a document exists in "test-index" with id "10" and content '{"title": "Async Doc", "content": "Async test"}'
    When I perform a bulk operation with:
      | action  | id | index            | document                                  |
      | index   | 20 | test-index       | {"title": "Async 2", "content": "Second"} |
      | index   | 30 | test-index       | {"title": "Async 3", "content": "Third"}  |
      | update  | 10 | test-index       | {"doc": {"content": "Bulk async update"}} |
      | delete  | 40 | test-index       |                                          |
    Then the bulk operation should succeed
    And all operations should be reflected in the index

  Scenario: Connect with authenticated user
    Given an Elasticsearch cluster with security enabled
    When I connect with username "elastic-user" and password "elastic-pass"
    Then the connection should be successful
    And I should be able to perform operations on the cluster

# features/vespa_adapter.feature
Feature: Vespa Operations Testing
  As a developer
  I want to test Vespa operations using the adapter pattern
  So that I can ensure proper interaction with the Vespa cluster through our standardized interface

  Background:
    Given a Vespa cluster is running
    And document type "testapp" exists

  Scenario: Feed a new document synchronously
    Given a valid Vespa client connection
    When I feed a document with id "1" and content '{"title": "Test Document"}' into "testapp"
    Then the feed operation should succeed
    And the document should be retrievable by id "1" from document type "testapp"

  Scenario: Query for documents synchronously
    Given a valid Vespa client connection
    And a document exists in Vespa "testapp" with id "1" and content '{"title": "Test Document"}'
    When I query for "select * from testapp where true" in "testapp"
    Then the query should return at least 1 hit

  Scenario: Deploy application to Vespa Docker
    Given a valid Vespa client connection
    When I deploy a test application to Vespa Docker
    Then the deployment should succeed

  Scenario: Get a document by ID synchronously
    Given a valid Vespa client connection
    And a document exists in Vespa "testapp" with id "2" and content '{"title": "Get Test Document"}'
    When I get document "2" from "testapp"
    Then the document should be retrievable by id "2" from document type "testapp"

  Scenario: Update a document synchronously
    Given a valid Vespa client connection
    And a document exists in Vespa "testapp" with id "3" and content '{"title": "Original Document"}'
    When I update document "3" in document type "testapp" with content '{"title": "Updated Document"}'
    Then the Vespa update operation should succeed
    And the Vespa document should reflect the updated content when retrieved

  Scenario: Delete a document synchronously
    Given a valid Vespa client connection
    And a document exists in Vespa "testapp" with id "4" and content '{"title": "Document to Delete"}'
    When I delete document "4" from document type "testapp"
    Then the Vespa delete operation should succeed
    And the Vespa document should not exist when searched for

  Scenario: Feed a new document asynchronously
    Given a valid Vespa client connection
    And the scenario is tagged as "async"
    When I feed a document with id "5" and content '{"title": "Async Test Document"}' into "testapp"
    Then the feed operation should succeed
    And the document should be retrievable by id "5" from document type "testapp"

  Scenario: Query for documents asynchronously
    Given a valid Vespa client connection
    And the scenario is tagged as "async"
    And a document exists in Vespa "testapp" with id "5" and content '{"title": "Async Test Document"}'
    When I query for "select * from testapp where title contains 'Async'" in "testapp"
    Then the query should return at least 1 hit

  Scenario: Get a document by ID asynchronously
    Given a valid Vespa client connection
    And the scenario is tagged as "async"
    And a document exists in Vespa "testapp" with id "5" and content '{"title": "Async Get Test Document"}'
    When I get document "6" from "testapp"
    Then the document should be retrievable by id "5" from document type "testapp"

  Scenario: Update a document asynchronously
    Given a valid Vespa client connection
    And the scenario is tagged as "async"
    And a document exists in Vespa "testapp" with id "5" and content '{"title": "Async Original Document"}'
    When I update document "5" in document type "testapp" with content '{"title": "Async Updated Document"}'
    Then the Vespa update operation should succeed
    And the Vespa document should reflect the updated content when retrieved

  Scenario: Delete a document asynchronously
    Given a valid Vespa client connection
    And the scenario is tagged as "async"
    And a document exists in Vespa "testapp" with id "5" and content '{"title": "Async Document to Delete"}'
    When I delete document "5" from document type "testapp"
    Then the Vespa delete operation should succeed
    And the Vespa document should not exist when searched for

  Scenario: Deploy application to Vespa Docker asynchronously
    Given a valid Vespa client connection
    And the scenario is tagged as "async"
    When I deploy a test application to Vespa Docker
    Then the deployment should succeed

  Scenario: Feed and query documents using HTTP/2
    Given a valid Vespa client connection
    And I use HTTP/2 for Vespa connections
    Then the Vespa adapter should be using HTTP/2
    When I feed a document with id "9" and content '{"title": "HTTP2 Test Document"}' into "testapp"
    Then the feed operation should succeed
    And the document should be retrievable by id "9" from document type "testapp"
    When I query for "select * from testapp where title contains 'HTTP2'" in "testapp"
    Then the query should return at least 1 hit

  Scenario: Feed and query documents using HTTP/1.1
    Given a valid Vespa client connection
    And I use HTTP/1.1 for Vespa connections
    Then the Vespa adapter should be using HTTP/1.1
    When I feed a document with id "10" and content '{"title": "HTTP1 Test Document"}' into "testapp"
    Then the feed operation should succeed
    And the document should be retrievable by id "10" from document type "testapp"
    When I query for "select * from testapp where title contains 'HTTP1'" in "testapp"
    Then the query should return at least 1 hit

  Scenario: Feed and query documents asynchronously using HTTP/2
    Given a valid Vespa client connection
    And the scenario is tagged as "async"
    And I use HTTP/2 for Vespa connections
    Then the Vespa adapter should be using HTTP/2
    When I feed a document with id "11" and content '{"title": "Async HTTP2 Test Document"}' into "testapp"
    Then the feed operation should succeed
    And the document should be retrievable by id "11" from document type "testapp"
    When I query for "select * from testapp where title contains 'Async HTTP2'" in "testapp"
    Then the query should return at least 1 hit

  Scenario: Feed and query documents asynchronously using HTTP/1.1
    Given a valid Vespa client connection
    And the scenario is tagged as "async"
    And I use HTTP/1.1 for Vespa connections
    Then the Vespa adapter should be using HTTP/1.1
    When I feed a document with id "12" and content '{"title": "Async HTTP1 Test Document"}' into "testapp"
    Then the feed operation should succeed
    And the document should be retrievable by id "12" from document type "testapp"
    When I query for "select * from testapp where title contains 'Async HTTP1'" in "testapp"
    Then the query should return at least 1 hit

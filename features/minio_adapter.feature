# features/minio_operations.feature
@needs-minio
Feature: MinIO Operations Testing
  As a developer
  I want to test MinIO storage operations
  So that I can ensure reliable object storage functionality

  Background:
    Given a configured MinIO adapter

  Scenario: Create and verify a bucket
    When I create a bucket named "test-bucket"
    Then the bucket "test-bucket" should exist
    And the bucket list should include "test-bucket"

  Scenario: Upload and retrieve object
    Given a bucket named "test-bucket" exists
    When I upload a file "test.txt" with content "Hello World" to bucket "test-bucket"
    Then the object "test.txt" should exist in bucket "test-bucket"
    And downloading "test.txt" from "test-bucket" should return content "Hello World"

  Scenario: Generate and use presigned URL
    Given a bucket named "test-bucket" exists
    And an object "test.txt" exists with content "Hello World" in bucket "test-bucket"
    When I generate a presigned GET URL for "test.txt" in "test-bucket"
    Then the presigned URL should be valid
    And accessing the presigned URL should return "Hello World"

  Scenario: Set and get bucket policy
    Given a bucket named "test-bucket" exists
    When I set a read-only policy on bucket "test-bucket"
    Then the bucket policy for "test-bucket" should be read-only

  Scenario: Delete object and bucket
    Given a bucket named "test-bucket" exists
    And an object "test.txt" exists with content "Hello World" in bucket "test-bucket"
    When I delete object "test.txt" from bucket "test-bucket"
    And I delete bucket "test-bucket"
    Then the object "test.txt" should not exist in bucket "test-bucket"
    And the bucket "test-bucket" should not exist

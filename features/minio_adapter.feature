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

  Scenario: Copy object within same bucket
    Given a bucket named "test-bucket" exists
    And an object "test.txt" exists with content "Hello World" in bucket "test-bucket"
    When I copy object "test.txt" from bucket "test-bucket" to "test-copy.txt" in the same bucket
    Then the object "test-copy.txt" should exist in bucket "test-bucket"
    And downloading "test-copy.txt" from "test-bucket" should return content "Hello World"

  Scenario Outline: Upload via <input_kind> and retrieve via stream
    Given a bucket named "test-bucket" exists
    When I upload <input_kind> "<content>" as "<object>" to bucket "test-bucket"
    Then the object "<object>" should exist in bucket "test-bucket"
    And the streaming download of "<object>" from "test-bucket" should return "<content>"

    Examples:
      | input_kind      | content               | object           |
      | the bytes       | Hello Streaming World | stream-bytes.txt |
      | a binary stream | Binary Stream Data    | stream-bio.txt   |

  Scenario: Streaming download enforces a maximum size
    Given a bucket named "stream-limit-bucket" exists
    And an object "large.txt" exists with content "1234567890" in bucket "stream-limit-bucket"
    When I stream download "large.txt" from "stream-limit-bucket" with max bytes 5
    Then the MinIO call should raise ResourceExhaustedError
    When I stream download "large.txt" from "stream-limit-bucket" with max bytes 10
    Then the downloaded stream content should be "1234567890"

  Scenario: Upload file with tags and verify tags
    Given a bucket named "test-bucket" exists
    When I upload a tagged file "tagged.txt" with content "Tagged Content" and tags "ttl-days=7,env=test" to bucket "test-bucket"
    Then the object "tagged.txt" should exist in bucket "test-bucket"
    And the tags on object "tagged.txt" in bucket "test-bucket" should include "ttl-days" with value "7"

  Scenario: Set tags on existing object
    Given a bucket named "test-bucket" exists
    And an object "existing.txt" exists with content "Some Content" in bucket "test-bucket"
    When I set tags "ttl-days=30,tier=archive" on object "existing.txt" in bucket "test-bucket"
    Then the tags on object "existing.txt" in bucket "test-bucket" should include "ttl-days" with value "30"

  Scenario: Set and get bucket lifecycle rules
    Given a bucket named "lifecycle-bucket" exists
    When I set a lifecycle rule on "lifecycle-bucket" with id "expire-7d" expiring after 7 days with prefix "tmp/"
    Then the lifecycle for "lifecycle-bucket" should have a rule with id "expire-7d"
    When I delete the lifecycle configuration from "lifecycle-bucket"
    Then the lifecycle for "lifecycle-bucket" should be empty

  Scenario: Check object existence
    Given a bucket named "test-bucket" exists
    And an object "exists.txt" exists with content "Present" in bucket "test-bucket"
    Then object "exists.txt" should exist in bucket "test-bucket"
    When I delete object "exists.txt" from bucket "test-bucket"
    Then object "exists.txt" should not exist in bucket "test-bucket"

  Scenario: Remove object tags
    Given a bucket named "test-bucket" exists
    When I upload a tagged file "tagged-remove.txt" with content "Tagged" and tags "env=test,tier=hot" to bucket "test-bucket"
    And I remove all tags from object "tagged-remove.txt" in bucket "test-bucket"
    Then object "tagged-remove.txt" in bucket "test-bucket" should have no tags

  Scenario: Batch delete objects
    Given a bucket named "batch-bucket" exists
    And an object "batch-a.txt" exists with content "A" in bucket "batch-bucket"
    And an object "batch-b.txt" exists with content "B" in bucket "batch-bucket"
    And an object "batch-c.txt" exists with content "C" in bucket "batch-bucket"
    When I batch delete objects "batch-a.txt,batch-b.txt,batch-c.txt" from bucket "batch-bucket"
    Then object "batch-a.txt" should not exist in bucket "batch-bucket"
    And object "batch-b.txt" should not exist in bucket "batch-bucket"
    And object "batch-c.txt" should not exist in bucket "batch-bucket"

  Scenario: Object versioning
    Given a bucket named "version-bucket" exists
    When I enable versioning on bucket "version-bucket"
    Then versioning on bucket "version-bucket" should be enabled
    When I upload a file "versioned.txt" with content "Version 1" to bucket "version-bucket"
    And I upload a file "versioned.txt" with content "Version 2" to bucket "version-bucket"
    Then bucket "version-bucket" should have at least 2 versions of object "versioned.txt"
    When I permanently delete the oldest version of "versioned.txt" in bucket "version-bucket"
    Then downloading "versioned.txt" from "version-bucket" should return content "Version 2"

  Scenario: Stat object returns size, content type and etag
    Given a bucket named "stat-bucket" exists
    And an object "stat.txt" exists with content "Hello World" in bucket "stat-bucket"
    When I stat object "stat.txt" in bucket "stat-bucket"
    Then the object stats should show size 11 and a non-empty etag

  Scenario: List objects by prefix
    Given a bucket named "list-bucket" exists
    And an object "logs/a.txt" exists with content "A" in bucket "list-bucket"
    And an object "logs/b.txt" exists with content "B" in bucket "list-bucket"
    And an object "other/c.txt" exists with content "C" in bucket "list-bucket"
    And an object "root.txt" exists with content "R" in bucket "list-bucket"
    When I list objects in bucket "list-bucket" with prefix "logs/" recursively
    Then the listed object names should be "logs/a.txt,logs/b.txt"
    When I list the top level of bucket "list-bucket"
    Then the listed object names should be "logs/,other/,root.txt"

  Scenario: Upload through a presigned PUT URL
    Given a bucket named "presigned-put-bucket" exists
    When I generate a presigned PUT URL for "uploaded.txt" in "presigned-put-bucket"
    And I upload "Uploaded By URL" to the presigned PUT URL
    Then downloading "uploaded.txt" from "presigned-put-bucket" should return content "Uploaded By URL"

  Scenario Outline: Missing resources raise <error>
    Given a bucket named "errors-bucket" exists
    When I <operation>
    Then the MinIO call should raise <error>

    Examples:
      | operation                                                | error                |
      | stat missing object "nope.txt" in bucket "errors-bucket" | NotFoundError        |
      | list objects in missing bucket "no-such-bucket-xyz"      | NotFoundError        |
      | create bucket "errors-bucket" again                      | AlreadyExistsError   |
      | check existence of an object with an empty bucket name   | InvalidArgumentError |

  Scenario Outline: Botocore connection failures map to <error>
    When I check bucket existence while the S3 client raises botocore "<raised_error>"
    Then the MinIO call should raise <error>

    Examples:
      | raised_error          | error                  |
      | ReadTimeoutError      | ConnectionTimeoutError |
      | ConnectTimeoutError   | ConnectionTimeoutError |
      | ConnectionClosedError | NetworkError           |

  Scenario Outline: Checksum settings <request>/<response> and CA bundle <ca_bundle> reach the S3 client
    Given a MinIO adapter with request checksum "<request>", response checksum "<response>" and CA bundle "<ca_bundle>"
    And a bucket named "checksum-bucket" exists
    When I upload a file "sum.txt" with content "Checksum" to bucket "checksum-bucket"
    Then downloading "sum.txt" from "checksum-bucket" should return content "Checksum"
    And the S3 client should use request checksum "<request>" and response checksum "<response>"

    Examples:
      | request        | response       | ca_bundle |
      | when_supported | when_supported | none      |
      | when_required  | when_required  | certifi   |

  Scenario Outline: Client options <keepalive>/<agent>/<proxy> reach the S3 client
    Given a MinIO adapter with TCP keepalive "<keepalive>", user agent extra "<agent>", proxy "<proxy>" and client certificate "<cert>"
    And a bucket named "options-bucket" exists
    When I upload a file "opt.txt" with content "Options" to bucket "options-bucket"
    Then downloading "opt.txt" from "options-bucket" should return content "Options"
    And the S3 client should use the configured client options

    Examples:
      | keepalive | agent    | proxy | cert |
      | none      | none     | none  | none |
      | true      | archipy1 | none  | none |

  Scenario: Proxy and client certificate are wired into the S3 client
    Given a MinIO adapter with TCP keepalive "true", user agent extra "none", proxy "http://proxy.invalid:3128" and client certificate "pair"
    Then the S3 client should use the configured client options

  Scenario: Unknown profile is rejected
    When I create a MinIO adapter with profile "no-such-profile"
    Then the adapter creation should fail with InternalError

  Scenario: Object existence is not served stale after an upload
    Given a bucket named "cache-bucket" exists
    Then object "late.txt" should not exist in bucket "cache-bucket"
    When I upload a file "late.txt" with content "Now Here" to bucket "cache-bucket"
    Then object "late.txt" should exist in bucket "cache-bucket"

  Scenario: Clearing all caches keeps results correct
    Given a bucket named "clear-bucket" exists
    And an object "keep.txt" exists with content "Keep" in bucket "clear-bucket"
    When I clear all adapter caches
    Then object "keep.txt" should exist in bucket "clear-bucket"

  Scenario: Caches are not shared between adapter instances
    Given a second MinIO adapter has cached that bucket "iso-bucket" is missing
    When I create a bucket named "iso-bucket"
    Then the second MinIO adapter should still serve bucket "iso-bucket" as missing from its own cache
    When I clear all caches of the second MinIO adapter
    Then the second MinIO adapter should report bucket "iso-bucket" exists

  Scenario: Object stat is not served stale after an overwrite
    Given a bucket named "fresh-bucket" exists
    And an object "f.txt" exists with content "a" in bucket "fresh-bucket"
    When I stat object "f.txt" in bucket "fresh-bucket"
    Then the object stats should show size 1 and a non-empty etag
    When I upload a file "f.txt" with content "ninety-nine" to bucket "fresh-bucket"
    And I stat object "f.txt" in bucket "fresh-bucket"
    Then the object stats should show size 11 and a non-empty etag

  Scenario Outline: Bucket <setting> is not served stale after it is changed
    Given a bucket named "fresh-bucket" exists
    When I read the <setting> of bucket "fresh-bucket"
    And I change the <setting> of bucket "fresh-bucket" to "<new_value>"
    Then the <setting> of bucket "fresh-bucket" should be "<new_value>"

    Examples:
      | setting    | new_value    |
      | policy     | s3:PutObject |
      | versioning | Enabled      |

  Scenario Outline: Mutating the returned <kind> does not corrupt the cache
    Given a bucket named "copy-bucket" exists
    And an object "c.txt" exists with content "C" in bucket "copy-bucket"
    When I read the cached <kind> of bucket "copy-bucket" and mutate the result
    Then reading the <kind> of bucket "copy-bucket" again should show the original data

    Examples:
      | kind        |
      | object list |
      | bucket list |
      | object stat |

  @needs-otel-collector
  Scenario: MinIO adapter calls emit boto spans
    Given adapter spans are exported to the collector
    When I upload and download an object through the MinIO adapter
    Then the collector should have a span named "S3.PutObject" with attribute "rpc.service" containing "S3"
    And the collector should have a span named "S3.GetObject" with attribute "rpc.service" containing "S3"

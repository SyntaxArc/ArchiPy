@needs-minio
Feature: FastAPI MinIO large file upload
  As a developer
  I want to upload a large file through a FastAPI endpoint backed by the MinIO adapter
  So that streaming uploads work end-to-end

  Scenario Outline: Upload a <size_mb> MB file through a FastAPI endpoint to MinIO
    Given a bucket named "uploads-bucket" exists
    And a FastAPI app with a MinIO upload endpoint
    And a temporary file of <size_mb> MB
    When I POST the file as "<object>" to the upload endpoint targeting bucket "uploads-bucket"
    Then the upload response status should be 201
    And the object "<object>" in bucket "uploads-bucket" should have size of at least <size_mb> MB

    Examples:
      | size_mb | object         |
      | 50      | file-50mb.bin  |
      | 75      | file-75mb.bin  |
      | 100     | file-100mb.bin |

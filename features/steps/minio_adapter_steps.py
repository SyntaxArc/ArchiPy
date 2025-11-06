# features/steps/minio_steps.py
import json
import os
import tempfile

import requests
from behave import given, then, when
from features.test_helpers import get_current_scenario_context

from archipy.adapters.minio.adapters import MinioAdapter
from archipy.configs.base_config import BaseConfig


def get_minio_adapter(context):
    """Get or initialize the MinIO adapter."""
    scenario_context = get_current_scenario_context(context)
    if not hasattr(scenario_context, "adapter") or scenario_context.adapter is None:
        test_config = BaseConfig.global_config()
        context.logger.info(f"Initializing MinIO adapter with endpoint: {test_config.MINIO.ENDPOINT}")
        scenario_context.adapter = MinioAdapter(test_config.MINIO)
    return scenario_context.adapter


# Given steps
@given("a configured MinIO adapter")
def step_configured_adapter(context):
    adapter = get_minio_adapter(context)
    try:
        adapter.list_buckets()
        context.logger.info("Successfully connected to MinIO server")
    except Exception as e:
        context.logger.exception(f"Failed to connect to MinIO: {e!s}")
        raise


@given('a bucket named "{bucket_name}" exists')
def step_bucket_exists(context, bucket_name):
    adapter = get_minio_adapter(context)
    if not adapter.bucket_exists(bucket_name):
        adapter.make_bucket(bucket_name)
    context.logger.info(f"Ensured bucket '{bucket_name}' exists")


@given('an object "{object_name}" exists with content "{content}" in bucket "{bucket_name}"')
def step_object_exists(context, object_name, bucket_name, content):
    adapter = get_minio_adapter(context)
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        adapter.put_object(bucket_name, object_name, tmp_path)
    finally:
        os.unlink(tmp_path)
    context.logger.info(f"Created object '{object_name}' in '{bucket_name}'")


# When steps
@when('I create a bucket named "{bucket_name}"')
def step_create_bucket(context, bucket_name):
    adapter = get_minio_adapter(context)
    if not adapter.bucket_exists(bucket_name):
        adapter.make_bucket(bucket_name)
        context.logger.info(f"Created bucket '{bucket_name}'")
    else:
        context.logger.info(f"Bucket '{bucket_name}' already exists, skipping creation")


@when('I upload a file "{object_name}" with content "{content}" to bucket "{bucket_name}"')
def step_upload_file(context, object_name, bucket_name, content):
    adapter = get_minio_adapter(context)
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        adapter.put_object(bucket_name, object_name, tmp_path)
    finally:
        os.unlink(tmp_path)
    context.logger.info(f"Uploaded '{object_name}' to '{bucket_name}'")


@when('I generate a presigned GET URL for "{object_name}" in "{bucket_name}"')
def step_generate_presigned_url(context, object_name, bucket_name):
    adapter = get_minio_adapter(context)
    url = adapter.presigned_get_object(bucket_name, object_name)
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("presigned_url", url)
    context.logger.info(f"Generated presigned URL for '{object_name}': {url}")


@when('I set a read-only policy on bucket "{bucket_name}"')
def step_set_policy(context, bucket_name):
    adapter = get_minio_adapter(context)
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{bucket_name}/*"],
            },
        ],
    }
    policy_json = json.dumps(policy)
    context.logger.info(f"Setting policy for '{bucket_name}': {policy_json}")
    adapter.set_bucket_policy(bucket_name, policy_json)
    context.logger.info(f"Set read-only policy on '{bucket_name}'")


@when('I delete object "{object_name}" from bucket "{bucket_name}"')
def step_delete_object(context, object_name, bucket_name):
    adapter = get_minio_adapter(context)
    adapter.remove_object(bucket_name, object_name)
    context.logger.info(f"Deleted '{object_name}' from '{bucket_name}'")


@when('I delete bucket "{bucket_name}"')
def step_delete_bucket(context, bucket_name):
    adapter = get_minio_adapter(context)
    adapter.remove_bucket(bucket_name)
    context.logger.info(f"Deleted bucket '{bucket_name}'")


# Then steps
@then('the bucket "{bucket_name}" should exist')
def step_bucket_should_exist(context, bucket_name):
    adapter = get_minio_adapter(context)
    assert adapter.bucket_exists(bucket_name), f"Bucket '{bucket_name}' does not exist"
    context.logger.info(f"Verified bucket '{bucket_name}' exists")


@then('the bucket "{bucket_name}" should not exist')
def step_bucket_should_not_exist(context, bucket_name):
    adapter = get_minio_adapter(context)
    assert not adapter.bucket_exists(bucket_name), f"Bucket '{bucket_name}' still exists"
    context.logger.info(f"Verified bucket '{bucket_name}' does not exist")


@then('the bucket list should include "{bucket_name}"')
def step_bucket_list_includes(context, bucket_name):
    adapter = get_minio_adapter(context)
    buckets = adapter.list_buckets()
    bucket_names = [b["name"] for b in buckets]
    assert bucket_name in bucket_names, f"Bucket '{bucket_name}' not in bucket list"
    context.logger.info(f"Verified '{bucket_name}' in bucket list")


@then('the object "{object_name}" should exist in bucket "{bucket_name}"')
def step_object_exists(context, object_name, bucket_name):
    adapter = get_minio_adapter(context)
    objects = adapter.list_objects(bucket_name)
    object_names = [obj["object_name"] for obj in objects]
    assert object_name in object_names, f"Object '{object_name}' not found in '{bucket_name}'"
    context.logger.info(f"Verified '{object_name}' exists in '{bucket_name}'")


@then('the object "{object_name}" should not exist in bucket "{bucket_name}"')
def step_object_not_exists(context, object_name, bucket_name):
    adapter = get_minio_adapter(context)
    if adapter.bucket_exists(bucket_name):
        objects = adapter.list_objects(bucket_name)
        object_names = [obj["object_name"] for obj in objects]
        assert object_name not in object_names, f"Object '{object_name}' still exists in '{bucket_name}'"
        context.logger.info(f"Verified '{object_name}' does not exist in '{bucket_name}'")
    else:
        context.logger.info(f"Bucket '{bucket_name}' does not exist, assuming object '{object_name}' is deleted")


@then('downloading "{object_name}" from "{bucket_name}" should return content "{expected_content}"')
def step_download_verify(context, object_name, bucket_name, expected_content):
    adapter = get_minio_adapter(context)
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        adapter.get_object(bucket_name, object_name, tmp_path)
        with open(tmp_path) as f:
            content = f.read()
        assert content == expected_content, f"Content mismatch: expected '{expected_content}', got '{content}'"
        context.logger.info(f"Verified downloaded content from '{object_name}'")
    finally:
        os.unlink(tmp_path)


@then("the presigned URL should be valid")
def step_presigned_url_valid(context):
    scenario_context = get_current_scenario_context(context)
    url = scenario_context.get("presigned_url")
    assert url is not None and url.startswith("http"), "Invalid presigned URL"
    context.logger.info("Verified presigned URL is valid")


@then('accessing the presigned URL should return "{expected_content}"')
def step_access_presigned_url(context, expected_content):
    scenario_context = get_current_scenario_context(context)
    url = scenario_context.get("presigned_url")
    response = requests.get(url)
    assert response.status_code == 200, f"Failed to access presigned URL: {response.status_code}"
    assert response.text == expected_content, f"Content mismatch: expected '{expected_content}', got '{response.text}'"
    context.logger.info("Verified presigned URL content")


@then('the bucket policy for "{bucket_name}" should be read-only')
def step_verify_policy(context, bucket_name):
    adapter = get_minio_adapter(context)
    policy = adapter.get_bucket_policy(bucket_name)["policy"]
    assert "s3:GetObject" in policy, "Policy doesn't contain read permission"
    assert "s3:PutObject" not in policy, "Policy contains write permission"
    context.logger.info(f"Verified read-only policy for '{bucket_name}'")

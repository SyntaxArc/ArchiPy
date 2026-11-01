# features/steps/minio_steps.py
import io
import json
import os
import tempfile
from unittest import mock

import certifi
import httpx2
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


@given('a MinIO adapter with request checksum "{request}", response checksum "{response}" and CA bundle "{ca_bundle}"')
def step_adapter_with_checksum_settings(context, request, response, ca_bundle):
    scenario_context = get_current_scenario_context(context)
    bundle_path = certifi.where() if ca_bundle == "certifi" else None
    minio_config = BaseConfig.global_config().MINIO.model_copy(
        update={
            "REQUEST_CHECKSUM_CALCULATION": request,
            "RESPONSE_CHECKSUM_VALIDATION": response,
            "CA_BUNDLE": bundle_path,
        },
    )
    scenario_context.adapter = MinioAdapter(minio_config)
    scenario_context.store("expected_verify", bundle_path or minio_config.VERIFY_SSL)


@then('the S3 client should use request checksum "{request}" and response checksum "{response}"')
def step_s3_client_checksum_settings(context, request, response):
    scenario_context = get_current_scenario_context(context)
    client = get_minio_adapter(context)._client
    assert client.meta.config.request_checksum_calculation == request
    assert client.meta.config.response_checksum_validation == response
    verify = client._endpoint.http_session._verify
    expected_verify = scenario_context.get("expected_verify")
    assert verify == expected_verify, f"Expected verify {expected_verify!r}, got {verify!r}"


@given(
    'a MinIO adapter with TCP keepalive "{keepalive}", user agent extra "{agent}", proxy "{proxy}" '
    'and client certificate "{cert}"',
)
def step_adapter_with_client_options(context, keepalive, agent, proxy, cert):
    scenario_context = get_current_scenario_context(context)
    update = {
        "TCP_KEEPALIVE": None if keepalive == "none" else keepalive == "true",
        "USER_AGENT_EXTRA": None if agent == "none" else agent,
        "PROXIES": None if proxy == "none" else {"http": proxy, "https": proxy},
        "CLIENT_CERT": None if cert == "none" else "/nonexistent/client.pem",
        "CLIENT_KEY": "/nonexistent/client.key" if cert == "pair" else None,
    }
    minio_config = BaseConfig.global_config().MINIO.model_copy(update=update)
    scenario_context.adapter = MinioAdapter(minio_config)
    scenario_context.store("client_options", update)


@then("the S3 client should use the configured client options")
def step_s3_client_options(context):
    scenario_context = get_current_scenario_context(context)
    options = scenario_context.get("client_options")
    client = get_minio_adapter(context)._client
    config = client.meta.config
    assert config.tcp_keepalive == options["TCP_KEEPALIVE"]
    assert config.proxies == options["PROXIES"]
    if options["USER_AGENT_EXTRA"]:
        assert options["USER_AGENT_EXTRA"] in config.user_agent_extra
    expected_cert = options["CLIENT_CERT"]
    if expected_cert and options["CLIENT_KEY"]:
        expected_cert = (expected_cert, options["CLIENT_KEY"])
    assert config.client_cert == expected_cert, f"Expected cert {expected_cert!r}, got {config.client_cert!r}"


@when('I create a MinIO adapter with profile "{profile}"')
def step_create_adapter_with_profile(context, profile):
    scenario_context = get_current_scenario_context(context)
    minio_config = BaseConfig.global_config().MINIO.model_copy(update={"PROFILE_NAME": profile})
    try:
        MinioAdapter(minio_config)
    except Exception as exc:  # noqa: BLE001
        scenario_context.store("adapter_creation_error", exc)


@then("the adapter creation should fail with {error_name}")
def step_adapter_creation_failed(context, error_name):
    scenario_context = get_current_scenario_context(context)
    error = scenario_context.get("adapter_creation_error")
    assert error is not None, "Expected adapter creation to fail"
    assert type(error).__name__ == error_name, f"Expected {error_name}, got {type(error).__name__}"


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


@when('I copy object "{src_object}" from bucket "{src_bucket}" to "{dest_object}" in the same bucket')
def step_copy_object_same_bucket(context, src_object, src_bucket, dest_object):
    adapter = get_minio_adapter(context)
    adapter.copy_object(
        src_bucket_name=src_bucket,
        src_object_name=src_object,
        dest_bucket_name=src_bucket,
        dest_object_name=dest_object,
    )
    context.logger.info(f"Copied '{src_object}' to '{dest_object}' in '{src_bucket}'")


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
def step_then_object_exists(context, object_name, bucket_name):
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
    response = httpx2.get(url)
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


@when('I upload {input_kind} "{content}" as "{object_name}" to bucket "{bucket_name}"')
def step_upload_stream(context, input_kind, content, object_name, bucket_name):
    adapter = get_minio_adapter(context)
    raw = content.encode("utf-8")
    if input_kind == "a binary stream":
        adapter.put_object_stream(
            bucket_name,
            object_name,
            io.BytesIO(raw),
            length=len(raw),
            content_type="text/plain; charset=utf-8",
        )
    else:
        adapter.put_object_stream(bucket_name, object_name, raw, content_type="text/plain; charset=utf-8")
    context.logger.info(f"Uploaded {input_kind} '{object_name}' to '{bucket_name}'")


@then('the streaming download of "{object_name}" from "{bucket_name}" should return "{expected_content}"')
def step_stream_download_verify(context, object_name, bucket_name, expected_content):
    adapter = get_minio_adapter(context)
    content_bytes = adapter.get_object_stream(bucket_name, object_name)
    content = content_bytes.decode("utf-8")
    assert content == expected_content, f"Content mismatch: expected '{expected_content}', got '{content}'"
    context.logger.info(f"Verified streaming download content of '{object_name}'")


@when('I stream download "{object_name}" from "{bucket_name}" with max bytes {max_bytes:d}')
def step_stream_download_with_limit(context, object_name, bucket_name, max_bytes):
    adapter = get_minio_adapter(context)
    scenario_context = get_current_scenario_context(context)
    try:
        content = adapter.get_object_stream(bucket_name, object_name, max_bytes=max_bytes)
    except Exception as error:  # noqa: BLE001
        scenario_context.store("raised_error", error)
        scenario_context.store("streamed_content", None)
    else:
        scenario_context.store("raised_error", None)
        scenario_context.store("streamed_content", content)


@then('the downloaded stream content should be "{expected_content}"')
def step_stream_download_content(context, expected_content):
    scenario_context = get_current_scenario_context(context)
    content = scenario_context.get("streamed_content")
    assert content is not None, "Expected streamed content"
    assert content.decode("utf-8") == expected_content, f"Content mismatch: expected '{expected_content}'"


@when('I upload a tagged file "{object_name}" with content "{content}" and tags "{tags_str}" to bucket "{bucket_name}"')
def step_upload_file_with_tags(context, object_name, content, tags_str, bucket_name):
    adapter = get_minio_adapter(context)
    tags = dict(pair.split("=", 1) for pair in tags_str.split(","))
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        adapter.put_object(bucket_name, object_name, tmp_path, tags=tags)
    finally:
        os.unlink(tmp_path)
    context.logger.info(f"Uploaded '{object_name}' with tags {tags} to '{bucket_name}'")


@when('I set tags "{tags_str}" on object "{object_name}" in bucket "{bucket_name}"')
def step_set_object_tags(context, tags_str, object_name, bucket_name):
    adapter = get_minio_adapter(context)
    tags = dict(pair.split("=", 1) for pair in tags_str.split(","))
    adapter.set_object_tags(bucket_name, object_name, tags)
    context.logger.info(f"Set tags {tags} on '{object_name}' in '{bucket_name}'")


@then('the tags on object "{object_name}" in bucket "{bucket_name}" should include "{key}" with value "{value}"')
def step_verify_object_tag(context, object_name, bucket_name, key, value):
    adapter = get_minio_adapter(context)
    tags = adapter.get_object_tags(bucket_name, object_name)
    assert key in tags, f"Tag '{key}' not found on '{object_name}'; got {tags}"
    assert tags[key] == value, f"Tag '{key}' expected '{value}', got '{tags[key]}'"
    context.logger.info(f"Verified tag '{key}={value}' on '{object_name}'")


@when(
    'I set a lifecycle rule on "{bucket_name}" with id "{rule_id}" expiring after {days:d} days with prefix "{prefix}"',
)
def step_set_lifecycle_rule(context, bucket_name, rule_id, days, prefix):
    adapter = get_minio_adapter(context)
    rule = {
        "ID": rule_id,
        "Status": "Enabled",
        "Filter": {"Prefix": prefix},
        "Expiration": {"Days": days},
    }
    adapter.set_bucket_lifecycle(bucket_name, [rule])
    context.logger.info(f"Set lifecycle rule '{rule_id}' on '{bucket_name}' (expires after {days}d, prefix='{prefix}')")


@then('the lifecycle for "{bucket_name}" should have a rule with id "{rule_id}"')
def step_verify_lifecycle_rule(context, bucket_name, rule_id):
    adapter = get_minio_adapter(context)
    rules = adapter.get_bucket_lifecycle(bucket_name)
    rule_ids = [r.get("ID") for r in rules]
    assert rule_id in rule_ids, f"Rule '{rule_id}' not found in lifecycle; got {rule_ids}"
    context.logger.info(f"Verified lifecycle rule '{rule_id}' exists on '{bucket_name}'")


@when('I delete the lifecycle configuration from "{bucket_name}"')
def step_delete_lifecycle(context, bucket_name):
    adapter = get_minio_adapter(context)
    adapter.delete_bucket_lifecycle(bucket_name)
    context.logger.info(f"Deleted lifecycle configuration from '{bucket_name}'")


@then('the lifecycle for "{bucket_name}" should be empty')
def step_verify_lifecycle_empty(context, bucket_name):
    adapter = get_minio_adapter(context)
    rules = adapter.get_bucket_lifecycle(bucket_name)
    assert rules == [], f"Expected empty lifecycle for '{bucket_name}', got {rules}"
    context.logger.info(f"Verified lifecycle is empty for '{bucket_name}'")


@then('object "{object_name}" should exist in bucket "{bucket_name}"')
def step_object_should_exist(context, object_name, bucket_name):
    adapter = get_minio_adapter(context)
    assert adapter.object_exists(bucket_name, object_name), f"Object '{object_name}' does not exist in '{bucket_name}'"
    context.logger.info(f"Verified object '{object_name}' exists in '{bucket_name}' via object_exists")


@then('object "{object_name}" should not exist in bucket "{bucket_name}"')
def step_object_should_not_exist(context, object_name, bucket_name):
    adapter = get_minio_adapter(context)
    assert not adapter.object_exists(bucket_name, object_name), (
        f"Object '{object_name}' still exists in '{bucket_name}'"
    )
    context.logger.info(f"Verified object '{object_name}' does not exist in '{bucket_name}' via object_exists")


@when('I remove all tags from object "{object_name}" in bucket "{bucket_name}"')
def step_remove_object_tags(context, object_name, bucket_name):
    adapter = get_minio_adapter(context)
    adapter.remove_object_tags(bucket_name, object_name)
    context.logger.info(f"Removed all tags from '{object_name}' in '{bucket_name}'")


@then('object "{object_name}" in bucket "{bucket_name}" should have no tags')
def step_verify_no_object_tags(context, object_name, bucket_name):
    adapter = get_minio_adapter(context)
    tags = adapter.get_object_tags(bucket_name, object_name)
    assert tags == {}, f"Expected no tags on '{object_name}', got {tags}"
    context.logger.info(f"Verified '{object_name}' has no tags in '{bucket_name}'")


@when('I batch delete objects "{object_names}" from bucket "{bucket_name}"')
def step_batch_delete_objects(context, object_names, bucket_name):
    adapter = get_minio_adapter(context)
    names = [name.strip() for name in object_names.split(",")]
    adapter.remove_objects(bucket_name, names)
    context.logger.info(f"Batch deleted {names} from '{bucket_name}'")


@given('{count:d} objects named "{prefix}" exist in bucket "{bucket_name}"')
def step_many_objects_exist(context, count, prefix, bucket_name):
    adapter = get_minio_adapter(context)
    for index in range(count):
        adapter.put_object_stream(bucket_name, f"{prefix}{index:04d}.txt", b"x")
    context.logger.info(f"Created {count} objects named '{prefix}*' in '{bucket_name}'")


@when('I batch delete {count:d} objects named "{prefix}" from bucket "{bucket_name}"')
def step_batch_delete_many_objects(context, count, prefix, bucket_name):
    adapter = get_minio_adapter(context)
    names = [f"{prefix}{index:04d}.txt" for index in range(count)]
    adapter.remove_objects(bucket_name, names)
    context.logger.info(f"Batch deleted {count} objects named '{prefix}*' from '{bucket_name}'")


@when('I batch delete "{object_names}" from bucket "{bucket_name}" while storage reports failures')
def step_batch_delete_with_failure(context, object_names, bucket_name):
    adapter = get_minio_adapter(context)
    failed_key = object_names.split(",")[-1]
    response = {"Errors": [{"Key": failed_key, "Code": "AccessDenied", "Message": "denied"}]}
    with mock.patch.object(adapter._client, "delete_objects", return_value=response):
        _capture_error(context, lambda: adapter.remove_objects(bucket_name, object_names.split(",")))


@then('the raised error should list failed key "{failed_key}"')
def step_verify_failed_keys(context, failed_key):
    scenario_context = get_current_scenario_context(context)
    error = scenario_context.get("raised_error")
    assert failed_key in error.additional_data.get("failed_keys", []), (
        f"Failed key '{failed_key}' not in {error.additional_data}"
    )


@when('I enable versioning on bucket "{bucket_name}"')
def step_enable_versioning(context, bucket_name):
    adapter = get_minio_adapter(context)
    adapter.set_bucket_versioning(bucket_name, enabled=True)
    context.logger.info(f"Enabled versioning on '{bucket_name}'")


@then('versioning on bucket "{bucket_name}" should be enabled')
def step_verify_versioning_enabled(context, bucket_name):
    adapter = get_minio_adapter(context)
    status = adapter.get_bucket_versioning(bucket_name)
    assert status == "Enabled", f"Expected versioning Enabled on '{bucket_name}', got '{status}'"
    context.logger.info(f"Verified versioning is enabled on '{bucket_name}'")


@then('bucket "{bucket_name}" should have at least {count:d} versions of object "{object_name}"')
def step_verify_object_version_count(context, bucket_name, count, object_name):
    adapter = get_minio_adapter(context)
    versions = adapter.list_object_versions(bucket_name, prefix=object_name)
    object_versions = [v for v in versions if v["object_name"] == object_name and not v.get("is_delete_marker", False)]
    assert len(object_versions) >= count, (
        f"Expected at least {count} versions of '{object_name}', got {len(object_versions)}"
    )
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("object_versions", object_versions)
    context.logger.info(f"Verified at least {count} versions of '{object_name}' in '{bucket_name}'")


@when('I permanently delete the oldest version of "{object_name}" in bucket "{bucket_name}"')
def step_delete_oldest_version(context, object_name, bucket_name):
    adapter = get_minio_adapter(context)
    scenario_context = get_current_scenario_context(context)
    versions = scenario_context.get("object_versions")
    if not versions:
        versions = [
            v
            for v in adapter.list_object_versions(bucket_name, prefix=object_name)
            if v["object_name"] == object_name and not v.get("is_delete_marker", False)
        ]
    oldest = min(versions, key=lambda v: v["last_modified"])
    adapter.remove_object_version(bucket_name, object_name, oldest["version_id"])
    context.logger.info(
        f"Deleted oldest version {oldest['version_id']} of '{object_name}' in '{bucket_name}'",
    )


@when('I stat object "{object_name}" in bucket "{bucket_name}"')
def step_stat_object(context, object_name, bucket_name):
    adapter = get_minio_adapter(context)
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("object_stat", adapter.stat_object(bucket_name, object_name))


@then("the object stats should show size {size:d} and a non-empty etag")
def step_verify_object_stat(context, size):
    scenario_context = get_current_scenario_context(context)
    stat = scenario_context.get("object_stat")
    assert stat["size"] == size, f"Expected size {size}, got {stat['size']}"
    assert stat["etag"], "Expected a non-empty etag"
    assert stat["last_modified"] is not None, "Expected last_modified to be set"


@when('I list objects in bucket "{bucket_name}" with prefix "{prefix}" {mode}')
def step_list_objects(context, bucket_name, prefix, mode):
    assert mode in ("recursively", "non-recursively"), f"Unknown listing mode: {mode}"
    adapter = get_minio_adapter(context)
    scenario_context = get_current_scenario_context(context)
    objects = adapter.list_objects(bucket_name, prefix, recursive=mode == "recursively")
    scenario_context.store("listed_names", sorted(obj["object_name"] for obj in objects))


@when('I list the top level of bucket "{bucket_name}"')
def step_list_top_level(context, bucket_name):
    adapter = get_minio_adapter(context)
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("listed_names", sorted(obj["object_name"] for obj in adapter.list_objects(bucket_name)))


@then('the listed object names should be "{names}"')
def step_verify_listed_names(context, names):
    scenario_context = get_current_scenario_context(context)
    assert scenario_context.get("listed_names") == sorted(names.split(",")), (
        f"Unexpected listing: {scenario_context.get('listed_names')}"
    )


@then("no object names should be listed")
def step_verify_no_listed_names(context):
    scenario_context = get_current_scenario_context(context)
    assert scenario_context.get("listed_names") == [], f"Unexpected listing: {scenario_context.get('listed_names')}"


@when('I generate a presigned PUT URL for "{object_name}" in "{bucket_name}"')
def step_generate_presigned_put_url(context, object_name, bucket_name):
    adapter = get_minio_adapter(context)
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("presigned_put_url", adapter.presigned_put_object(bucket_name, object_name))


@when('I upload "{content}" to the presigned PUT URL')
def step_upload_to_presigned_url(context, content):
    scenario_context = get_current_scenario_context(context)
    response = httpx2.put(scenario_context.get("presigned_put_url"), content=content.encode())
    assert response.status_code == 200, f"Presigned PUT failed: {response.status_code} {response.text}"


def _capture_error(context, action) -> None:
    scenario_context = get_current_scenario_context(context)
    try:
        action()
    except Exception as error:
        scenario_context.store("raised_error", error)
    else:
        scenario_context.store("raised_error", None)


@when('I stat missing object "{object_name}" in bucket "{bucket_name}"')
def step_stat_missing_object(context, object_name, bucket_name):
    adapter = get_minio_adapter(context)
    _capture_error(context, lambda: adapter.stat_object(bucket_name, object_name))


@when('I list objects in missing bucket "{bucket_name}"')
def step_list_missing_bucket(context, bucket_name):
    adapter = get_minio_adapter(context)
    _capture_error(context, lambda: adapter.list_objects(bucket_name))


@when('I create bucket "{bucket_name}" again')
def step_create_bucket_again(context, bucket_name):
    adapter = get_minio_adapter(context)
    _capture_error(context, lambda: adapter.make_bucket(bucket_name))


@when('I check bucket existence while the S3 client raises botocore "{error_name}"')
def step_bucket_exists_with_client_error(context, error_name):
    from botocore.exceptions import (
        ConnectionClosedError,
        ConnectTimeoutError,
        ReadTimeoutError,
    )

    adapter = get_minio_adapter(context)
    error_classes = {
        "ReadTimeoutError": ReadTimeoutError,
        "ConnectTimeoutError": ConnectTimeoutError,
        "ConnectionClosedError": ConnectionClosedError,
    }
    error = error_classes[error_name](endpoint_url="http://localhost:9000")
    with mock.patch.object(adapter._client, "head_bucket", side_effect=error):
        _capture_error(context, lambda: adapter.bucket_exists("errors-bucket"))


@when("I check existence of an object with an empty bucket name")
def step_object_exists_empty_bucket(context):
    adapter = get_minio_adapter(context)
    _capture_error(context, lambda: adapter.object_exists("", "any.txt"))


@then("the MinIO call should raise {error_name}")
def step_verify_raised_error(context, error_name):
    scenario_context = get_current_scenario_context(context)
    error = scenario_context.get("raised_error")
    assert error is not None, f"Expected {error_name} but no error was raised"
    assert type(error).__name__ == error_name, f"Expected {error_name}, got {type(error).__name__}: {error}"


@when("I clear all adapter caches")
def step_clear_all_caches(context):
    get_minio_adapter(context).clear_all_caches()


@given('a second MinIO adapter has cached that bucket "{bucket_name}" is missing')
def step_second_adapter_cached_missing(context, bucket_name):
    scenario_context = get_current_scenario_context(context)
    second = MinioAdapter(BaseConfig.global_config().MINIO)
    assert second.bucket_exists(bucket_name) is False
    scenario_context.store("second_adapter", second)


@then('the second MinIO adapter should still serve bucket "{bucket_name}" as missing from its own cache')
def step_second_adapter_still_missing(context, bucket_name):
    second = get_current_scenario_context(context).get("second_adapter")
    assert second.bucket_exists(bucket_name) is False


@when("I clear all caches of the second MinIO adapter")
def step_clear_second_adapter_caches(context):
    get_current_scenario_context(context).get("second_adapter").clear_all_caches()


@then('the second MinIO adapter should report bucket "{bucket_name}" exists')
def step_second_adapter_bucket_exists(context, bucket_name):
    second = get_current_scenario_context(context).get("second_adapter")
    assert second.bucket_exists(bucket_name) is True


def _policy_json(bucket_name, action):
    return json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": [action],
                    "Resource": [f"arn:aws:s3:::{bucket_name}/*"],
                },
            ],
        },
    )


@when('I read the {setting} of bucket "{bucket_name}"')
def step_read_bucket_setting(context, setting, bucket_name):
    adapter = get_minio_adapter(context)
    if setting == "policy":
        adapter.set_bucket_policy(bucket_name, _policy_json(bucket_name, "s3:GetObject"))
        assert "s3:GetObject" in adapter.get_bucket_policy(bucket_name)["policy"]
    else:
        adapter.get_bucket_versioning(bucket_name)


@when('I change the {setting} of bucket "{bucket_name}" to "{new_value}"')
def step_change_bucket_setting(context, setting, bucket_name, new_value):
    adapter = get_minio_adapter(context)
    if setting == "policy":
        adapter.set_bucket_policy(bucket_name, _policy_json(bucket_name, new_value))
    else:
        adapter.set_bucket_versioning(bucket_name, enabled=new_value == "Enabled")


@then('the {setting} of bucket "{bucket_name}" should be "{expected}"')
def step_verify_bucket_setting(context, setting, bucket_name, expected):
    adapter = get_minio_adapter(context)
    if setting == "policy":
        actual = adapter.get_bucket_policy(bucket_name)["policy"]
        assert expected in actual and "s3:GetObject" not in actual, f"Stale policy: {actual}"
    else:
        actual = adapter.get_bucket_versioning(bucket_name)
        assert actual == expected, f"Expected {expected}, got {actual}"


def _read_cached(adapter, kind, bucket_name):
    if kind == "object list":
        return adapter.list_objects(bucket_name)
    if kind == "bucket list":
        return adapter.list_buckets()
    return adapter.stat_object(bucket_name, "c.txt")


@when('I read the cached {kind} of bucket "{bucket_name}" and mutate the result')
def step_mutate_cached_result(context, kind, bucket_name):
    adapter = get_minio_adapter(context)
    first = _read_cached(adapter, kind, bucket_name)
    get_current_scenario_context(context).store("original_snapshot", json.loads(json.dumps(first, default=str)))
    if isinstance(first, list):
        first.clear()
    else:
        first["size"] = -1


@then('reading the {kind} of bucket "{bucket_name}" again should show the original data')
def step_verify_cache_not_corrupted(context, kind, bucket_name):
    adapter = get_minio_adapter(context)
    again = json.loads(json.dumps(_read_cached(adapter, kind, bucket_name), default=str))
    original = get_current_scenario_context(context).get("original_snapshot")
    assert again == original, f"Cache was corrupted: {again} != {original}"
    assert original, "Expected a non-empty result"

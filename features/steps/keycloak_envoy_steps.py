import re

import requests
from behave import given, then, when
from behave.runner import Context
from features.test_containers import KEYCLOAK_ADMIN_HOSTNAME, KEYCLOAK_PUBLIC_HOSTNAME, ContainerManager

HOSTS: dict[str, str] = {
    "public": KEYCLOAK_PUBLIC_HOSTNAME.removeprefix("https://"),
    "admin": KEYCLOAK_ADMIN_HOSTNAME.removeprefix("https://"),
}


def _envoy_url() -> str:
    return ContainerManager.get_container("envoy").url


def _send(method: str, host: str, path: str, **kwargs) -> requests.Response:
    return requests.request(
        method,
        f"{_envoy_url()}{path}",
        headers={"Host": HOSTS[host]},
        allow_redirects=False,
        timeout=30,
        **kwargs,
    )


@given('the Keycloak realms "{first}" and "{second}" exist')
def step_realms_exist(context: Context, first: str, second: str) -> None:
    admin = ContainerManager.get_container("keycloak")._container.get_client()
    existing = {realm["realm"] for realm in admin.get_realms()}
    for realm in (first, second):
        if realm not in existing:
            admin.create_realm({"realm": realm, "enabled": True})


@when('I request "{path}" on the "{host}" host')
def step_request(context: Context, path: str, host: str) -> None:
    context.response = _send("GET", host, path)


@when('I request the first resource linked from the response on the "{host}" host')
def step_request_linked_resource(context: Context, host: str) -> None:
    match = re.search(r'(?:src|href)="[^"]*?(/resources/[^"]+\.(?:js|css))"', context.response.text)
    assert match, context.response.text[:500]
    context.response = _send("GET", host, match.group(1))


@when('I request an admin token for the "{realm}" realm on the "{host}" host')
def step_request_admin_token(context: Context, realm: str, host: str) -> None:
    keycloak = ContainerManager.get_container("keycloak")
    context.response = _send(
        "POST",
        host,
        f"/realms/{realm}/protocol/openid-connect/token",
        data={
            "client_id": "admin-cli",
            "grant_type": "password",
            "username": keycloak.admin_username or "admin",
            "password": keycloak.admin_password or "admin",
        },
    )


@then("the response status is {status:d}")
def step_status(context: Context, status: int) -> None:
    assert context.response.status_code == status, (context.response.status_code, context.response.text[:300])


@then("the response access token is {presence}")
def step_access_token(context: Context, presence: str) -> None:
    token = context.response.json().get("access_token") if context.response.status_code == 200 else None
    assert bool(token) == (presence == "present"), (presence, context.response.status_code, context.response.text[:300])


@then("the response body contains the {name} host")
def step_body_contains(context: Context, name: str) -> None:
    assert f"https://{HOSTS[name]}" in context.response.text


@then("the response body does not contain the {name} host")
def step_body_not_contains(context: Context, name: str) -> None:
    assert f"https://{HOSTS[name]}" not in context.response.text


@then('the "{realm}" realm issuer on the "{host}" host is the {expected} host')
def step_issuer(context: Context, realm: str, host: str, expected: str) -> None:
    response = _send("GET", host, f"/realms/{realm}/.well-known/openid-configuration")
    assert response.status_code == 200, (response.status_code, response.text[:300])
    assert response.json()["issuer"] == f"https://{HOSTS[expected]}/realms/{realm}", response.json()["issuer"]

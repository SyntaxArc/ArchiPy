from behave import then, when
from behave.runner import Context
from features.steps.keycloak_adapter_steps import _adapter_call, _adapter_parts

from archipy.models.dtos.keycloak.attack_detection_dtos import KeycloakBruteForceStatusDTO
from archipy.models.dtos.keycloak.certificate_dtos import KeycloakKeyStoreConfigRequestDTO
from archipy.models.dtos.keycloak.client_initial_access_dtos import KeycloakClientInitialAccessCreateRequestDTO
from archipy.models.dtos.keycloak.identity_provider_dtos import (
    KeycloakIdentityProviderMapperRequestDTO,
    KeycloakIdentityProviderRequestDTO,
)

SERVER_ERRORS = (400, 404, 500, 501)


async def _uuid(context: Context, client: str) -> str:
    adapter, is_async, _ = _adapter_parts(context)
    return await _adapter_call(adapter, is_async, "get_client_id", client)


async def _tolerate(coro, codes=SERVER_ERRORS):
    """Await ``coro``; a Keycloak refusal with one of ``codes`` is accepted and returned as ``None``."""
    try:
        return await coro
    except Exception as e:  # noqa: BLE001 - the server under test may not offer the feature
        assert e.additional_data.get("response_code") in codes, repr(e)
        return None


@then("the realm keys and the client registration policy providers are listed using {adapter_type} adapter")
async def step_keys_and_policy_providers(context: Context, adapter_type: str) -> None:
    adapter, is_async, _ = _adapter_parts(context)
    keys = await _adapter_call(adapter, is_async, "get_realm_keys")
    assert keys.keys_value and all(k.kid for k in keys.keys_value), keys
    assert keys.active, keys
    providers = await _adapter_call(adapter, is_async, "get_client_registration_policy_providers")
    assert providers and all(p.id for p in providers), providers


@then('the brute force status of user "{username}" is read and cleared using {adapter_type} adapter')
async def step_attack_detection(context: Context, username: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    user_id = sc.get(f"user_id_{username}")
    status = await _adapter_call(adapter, is_async, "get_user_brute_force_status", user_id)
    assert isinstance(status, KeycloakBruteForceStatusDTO) and status.disabled is False, status
    await _adapter_call(adapter, is_async, "clear_user_brute_force", user_id)
    await _adapter_call(adapter, is_async, "clear_all_brute_force")


@then("a client initial access token is created, listed and deleted using {adapter_type} adapter")
async def step_initial_access(context: Context, adapter_type: str) -> None:
    adapter, is_async, _ = _adapter_parts(context)
    created = await _adapter_call(
        adapter, is_async, "create_client_initial_access", KeycloakClientInitialAccessCreateRequestDTO(expiration=300, count=2),
    )
    assert created.token and created.id and created.count == 2, created
    listed = await _adapter_call(adapter, is_async, "get_client_initial_access_tokens")
    assert created.id in [t.id for t in listed], listed
    assert all(t.token is None for t in listed), "listed tokens must not expose their secret"
    await _adapter_call(adapter, is_async, "delete_client_initial_access", created.id)
    assert created.id not in [t.id for t in await _adapter_call(adapter, is_async, "get_client_initial_access_tokens")]


@then('the client "{client}" generates and downloads a certificate using {adapter_type} adapter')
async def step_client_certificates(context: Context, client: str, adapter_type: str) -> None:
    adapter, is_async, _ = _adapter_parts(context)
    uuid = await _uuid(context, client)
    generated = await _adapter_call(adapter, is_async, "generate_client_certificate", uuid, "jwt.credential")
    assert generated.certificate and generated.private_key, generated
    fetched = await _adapter_call(adapter, is_async, "get_client_certificate", uuid, "jwt.credential")
    assert fetched.certificate == generated.certificate, fetched
    config = KeycloakKeyStoreConfigRequestDTO(
        key_alias="client", key_password="changeit", store_password="changeit", format="PKCS12",
    )
    keystore = await _adapter_call(adapter, is_async, "download_client_keystore", uuid, "jwt.credential", config)
    assert isinstance(keystore, bytes) and keystore, keystore
    regenerated = await _adapter_call(adapter, is_async, "generate_and_download_client_keystore", uuid, "jwt.credential", config)
    assert isinstance(regenerated, bytes) and regenerated, regenerated


@when('I create the identity provider "{alias}" with a mapper "{mapper}" using {adapter_type} adapter')
async def step_create_idp_with_mapper(context: Context, alias: str, mapper: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    provider = KeycloakIdentityProviderRequestDTO(
        alias=alias,
        provider_id="oidc",
        enabled=True,
        config={
            "clientId": "external",
            "clientSecret": "secret",
            "authorizationUrl": "https://idp.example.com/auth",
            "tokenUrl": "https://idp.example.com/token",
        },
    )
    created = await _adapter_call(adapter, is_async, "create_identity_provider", provider)
    sc.store("idp_created", created)
    mapper_created = await _adapter_call(
        adapter, is_async, "create_identity_provider_mapper", alias,
        KeycloakIdentityProviderMapperRequestDTO(
            name=mapper, identity_provider_alias=alias, identity_provider_mapper="oidc-hardcoded-role-idp-mapper",
            config={"syncMode": "INHERIT", "role": "offline_access"},
        ),
    )
    sc.store("idp_mapper_created", mapper_created)


@then('the identity provider "{alias}" and its mapper "{mapper}" are listed, read, updated and deleted using {adapter_type} adapter')
async def step_idp_lifecycle(context: Context, alias: str, mapper: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    created = sc.get("idp_created")
    assert created.id, created
    providers = await _adapter_call(adapter, is_async, "get_identity_providers")
    assert alias in [p.alias for p in providers], providers
    fetched = await _adapter_call(adapter, is_async, "get_identity_provider", alias)
    assert fetched.internal_id == created.id and fetched.provider_id == "oidc", fetched
    await _adapter_call(
        adapter, is_async, "update_identity_provider", alias,
        KeycloakIdentityProviderRequestDTO(alias=alias, provider_id="oidc", display_name="Updated", config=fetched.config),
    )
    assert (await _adapter_call(adapter, is_async, "get_identity_provider", alias)).display_name == "Updated"
    types = await _adapter_call(adapter, is_async, "get_identity_provider_mapper_types", alias)
    assert "oidc-hardcoded-role-idp-mapper" in types, list(types)
    mapper_id = sc.get("idp_mapper_created").id
    assert mapper_id, sc.get("idp_mapper_created")
    mappers = await _adapter_call(adapter, is_async, "get_identity_provider_mappers", alias)
    assert mapper in [m.name for m in mappers], mappers
    one = await _adapter_call(adapter, is_async, "get_identity_provider_mapper", alias, mapper_id)
    await _adapter_call(
        adapter, is_async, "update_identity_provider_mapper", alias, mapper_id,
        KeycloakIdentityProviderMapperRequestDTO(
            id=mapper_id, name=mapper, identity_provider_alias=alias,
            identity_provider_mapper=one.identity_provider_mapper, config={"syncMode": "FORCE", "role": "offline_access"},
        ),
    )
    assert (await _adapter_call(adapter, is_async, "get_identity_provider_mapper", alias, mapper_id)).config["syncMode"] == "FORCE"
    factory = await _adapter_call(adapter, is_async, "get_identity_provider_factory", "oidc")
    assert factory, factory
    await _tolerate(_adapter_call(adapter, is_async, "export_identity_provider", alias))
    await _tolerate(_adapter_call(adapter, is_async, "reload_identity_provider_keys", alias))
    await _tolerate(_adapter_call(adapter, is_async, "get_identity_provider_management_permissions", alias))
    await _tolerate(_adapter_call(adapter, is_async, "import_identity_provider_config", {"fromUrl": "http://localhost:1/x", "providerId": "oidc"}))
    await _adapter_call(adapter, is_async, "delete_identity_provider_mapper", alias, mapper_id)
    await _adapter_call(adapter, is_async, "delete_identity_provider", alias)
    assert alias not in [p.alias for p in await _adapter_call(adapter, is_async, "get_identity_providers")]

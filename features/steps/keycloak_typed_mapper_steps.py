from behave import then, when
from behave.runner import Context
from features.steps.keycloak_adapter_steps import _adapter_call, _adapter_parts

from archipy.models.dtos.keycloak.client_scope_dtos import KeycloakClientScopeRequestDTO
from archipy.models.dtos.keycloak.protocol_mapper_config_dtos import (
    KeycloakOidcAudienceMapperConfigDTO,
    KeycloakOidcHardcodedClaimMapperConfigDTO,
)


async def _example_claims(context: Context, client: str):
    adapter, is_async, _ = _adapter_parts(context)
    uuid = await _adapter_call(adapter, is_async, "get_client_id", client)
    account = await _adapter_call(adapter, is_async, "get_client_service_account_user", uuid)
    token = await _adapter_call(adapter, is_async, "get_client_example_access_token", uuid, {"userId": account.id})
    return token.model_extra or {}, token


@when('I add a typed hardcoded claim mapper "{mapper}" with claim "{claim}" and value "{value}" to the client scope "{scope}" assigned to client "{client}" using {adapter_type} adapter')
async def step_typed_scope_mapper(
    context: Context, mapper: str, claim: str, value: str, scope: str, client: str, adapter_type: str,
) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    scope_id = await _adapter_call(adapter, is_async, "create_client_scope", KeycloakClientScopeRequestDTO(name=scope, protocol="openid-connect"), skip_exists=True)
    config = KeycloakOidcHardcodedClaimMapperConfigDTO(claim_name=claim, claim_value=value, json_type_label="String")
    created = await _adapter_call(adapter, is_async, "add_client_scope_mapper_with_config", scope_id, mapper, config)
    sc.store("typed_scope_id", scope_id)
    sc.store("typed_mapper_created", created)
    uuid = await _adapter_call(adapter, is_async, "get_client_id", client)
    await _adapter_call(adapter, is_async, "add_client_default_client_scope", uuid, scope_id, KeycloakClientScopeRequestDTO())


@then('the typed mapper config is read back and the example token of client "{client}" carries claim "{claim}" as "{value}" using {adapter_type} adapter')
async def step_typed_scope_mapper_effect(context: Context, client: str, claim: str, value: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    created = sc.get("typed_mapper_created")
    assert created.id, created
    config = await _adapter_call(adapter, is_async, "get_client_scope_mapper_config", sc.get("typed_scope_id"), created.id)
    assert isinstance(config, KeycloakOidcHardcodedClaimMapperConfigDTO), config
    assert config.claim_name == claim and config.claim_value == value and config.access_token_claim is True, config
    extra, _ = await _example_claims(context, client)
    assert extra.get(claim) == value, extra


@when('I change the typed mapper to value "{value}" using {adapter_type} adapter')
async def step_update_typed_mapper(context: Context, value: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    config = await _adapter_call(adapter, is_async, "get_client_scope_mapper_config", sc.get("typed_scope_id"), sc.get("typed_mapper_created").id)
    changed = config.model_copy(update={"claim_value": value})
    await _adapter_call(adapter, is_async, "update_client_scope_mapper_config", sc.get("typed_scope_id"), sc.get("typed_mapper_created").id, "typed-claim-mapper", changed)


@when('I add a typed audience mapper for client "{audience}" and a typed claim mapper "{mapper}" with claim "{claim}" and value "{value}" to client "{client}" using {adapter_type} adapter')
async def step_typed_client_mappers(
    context: Context, audience: str, mapper: str, claim: str, value: str, client: str, adapter_type: str,
) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    uuid = await _adapter_call(adapter, is_async, "get_client_id", client)
    sc.store("typed_client_uuid", uuid)
    audience_result = await _adapter_call(
        adapter, is_async, "add_client_mapper_with_config", uuid, "typed-audience",
        KeycloakOidcAudienceMapperConfigDTO(included_client_audience=audience),
    )
    claim_result = await _adapter_call(
        adapter, is_async, "add_client_mapper_with_config", uuid, mapper,
        KeycloakOidcHardcodedClaimMapperConfigDTO(claim_name=claim, claim_value=value, json_type_label="String"),
    )
    sc.store("typed_client_mappers", (audience_result, claim_result))


@then('the typed client mappers are read back, updated and the example token of client "{client}" shows claim "{claim}" as "{value}" and audience "{audience}" using {adapter_type} adapter')
async def step_typed_client_mappers_effect(
    context: Context, client: str, claim: str, value: str, audience: str, adapter_type: str,
) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    uuid = sc.get("typed_client_uuid")
    audience_result, claim_result = sc.get("typed_client_mappers")
    assert audience_result.id and claim_result.id, sc.get("typed_client_mappers")
    audience_config = await _adapter_call(adapter, is_async, "get_client_mapper_config", uuid, audience_result.id)
    assert isinstance(audience_config, KeycloakOidcAudienceMapperConfigDTO), audience_config
    assert audience_config.included_client_audience == audience, audience_config
    extra, token = await _example_claims(context, client)
    assert extra.get(claim) == value, extra
    assert audience in ([token.aud] if isinstance(token.aud, str) else token.aud or []), token.aud
    updated = KeycloakOidcHardcodedClaimMapperConfigDTO(claim_name=claim, claim_value="changed", json_type_label="String")
    await _adapter_call(adapter, is_async, "update_client_mapper_config", uuid, claim_result.id, "typed-claim", updated)
    extra_after, _ = await _example_claims(context, client)
    assert extra_after.get(claim) == "changed", extra_after

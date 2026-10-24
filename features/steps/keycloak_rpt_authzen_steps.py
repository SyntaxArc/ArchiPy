from behave import then, when
from behave.runner import Context
from features.steps.keycloak_adapter_steps import _adapter_call, _adapter_parts

from archipy.models.dtos.keycloak.authz_dtos import KeycloakAuthzResourceRequestDTO, KeycloakAuthzScopeRequestDTO
from archipy.models.dtos.keycloak.authz_policy_dtos import KeycloakAuthzPolicyRoleDTO, KeycloakAuthzRolePolicyRequestDTO
from archipy.models.dtos.keycloak.authzen_dtos import (
    KeycloakAuthzenActionDTO,
    KeycloakAuthzenEvaluationItemDTO,
    KeycloakAuthzenEvaluationRequestDTO,
    KeycloakAuthzenEvaluationsRequestDTO,
    KeycloakAuthzenResourceDTO,
    KeycloakAuthzenSubjectDTO,
)
from archipy.models.dtos.keycloak.authz_dtos import KeycloakAuthzPolicyRequestDTO


@when('I protect the resource "{resource}" with scope "{scope}" for the realm role "{role}" on client "{client}" using {adapter_type} adapter')
async def step_protect_resource(context: Context, resource: str, scope: str, role: str, client: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    cid = await _adapter_call(adapter, is_async, "get_client_id", client)
    scope_created = await _adapter_call(adapter, is_async, "create_client_authz_scopes", cid, KeycloakAuthzScopeRequestDTO(name=scope))
    resource_created = await _adapter_call(
        adapter, is_async, "create_client_authz_resource", cid,
        KeycloakAuthzResourceRequestDTO(name=resource, type="document", scopes=[KeycloakAuthzScopeRequestDTO(name=scope)]),
    )
    realm_role = await _adapter_call(adapter, is_async, "get_realm_role", role)
    policy = await _adapter_call(
        adapter, is_async, "create_client_authz_role_based_policy", cid,
        KeycloakAuthzRolePolicyRequestDTO(
            name=f"{role}-policy", logic="POSITIVE", decision_strategy="UNANIMOUS",
            roles=[KeycloakAuthzPolicyRoleDTO(id=realm_role.id, required=False)],
        ),
    )
    await _adapter_call(
        adapter, is_async, "create_client_authz_scope_permission",
        KeycloakAuthzPolicyRequestDTO(
            name=f"{resource}-{scope}", type="scope", logic="POSITIVE", decision_strategy="UNANIMOUS",
            resources=[resource_created.internal_id], scopes=[scope_created.id], policies=[policy.id],
        ),
        cid,
    )


@then('the user "{username}" with password "{password}" gets a requesting party token for "{resource}#{scope}" using {adapter_type} adapter')
async def step_request_rpt(context: Context, username: str, password: str, resource: str, scope: str, adapter_type: str) -> None:
    adapter, is_async, _ = _adapter_parts(context)
    token = await _adapter_call(adapter, is_async, "get_token", username, password)
    rpt = await _adapter_call(adapter, is_async, "request_rpt", token.access_token, adapter.configs.CLIENT_ID, [f"{resource}#{scope}"])
    assert rpt.access_token and rpt.access_token != token.access_token, rpt
    claims = await _adapter_call(adapter, is_async, "get_token_info", rpt.access_token)
    permissions = (claims.model_extra or {}).get("authorization", {}).get("permissions", [])
    assert [p["rsname"] for p in permissions] == [resource], permissions
    assert permissions[0]["scopes"] == [scope], permissions


@then('AuthZEN decides access to "{resource}" for "{username}" as granted for "{scope}" and denied for "{denied_scope}" using {adapter_type} adapter')
async def step_authzen(context: Context, resource: str, username: str, scope: str, denied_scope: str, adapter_type: str) -> None:
    adapter, is_async, _ = _adapter_parts(context)
    client_token = await _adapter_call(adapter, is_async, "get_client_credentials_token")
    configuration = await _adapter_call(adapter, is_async, "get_authzen_configuration")
    assert configuration.access_evaluation_endpoint, configuration

    def request(action: str) -> KeycloakAuthzenEvaluationRequestDTO:
        return KeycloakAuthzenEvaluationRequestDTO(
            subject=KeycloakAuthzenSubjectDTO(type="user", id=username),
            resource=KeycloakAuthzenResourceDTO(type="document", id=resource),
            action=KeycloakAuthzenActionDTO(name=action),
        )

    granted = await _adapter_call(adapter, is_async, "authzen_evaluation", client_token.access_token, request(scope))
    denied = await _adapter_call(adapter, is_async, "authzen_evaluation", client_token.access_token, request(denied_scope))
    assert granted.decision is True and denied.decision is False, (granted, denied)
    batch = await _adapter_call(
        adapter, is_async, "authzen_evaluations", client_token.access_token,
        KeycloakAuthzenEvaluationsRequestDTO(
            subject=KeycloakAuthzenSubjectDTO(type="user", id=username),
            resource=KeycloakAuthzenResourceDTO(type="document", id=resource),
            evaluations=[
                KeycloakAuthzenEvaluationItemDTO(action=KeycloakAuthzenActionDTO(name=scope)),
                KeycloakAuthzenEvaluationItemDTO(action=KeycloakAuthzenActionDTO(name=denied_scope)),
            ],
        ),
    )
    assert [e.decision for e in batch.evaluations or []] == [True, False], batch

from uuid import uuid4

from behave import given, then, when

from archipy.adapters.keycloak.auth import AuthContextManager, require_selected_organization
from archipy.models.dtos.keycloak.token_dtos import KeycloakTokenClaimsDTO, KeycloakUserInfoDTO
from archipy.models.dtos.keycloak_dtos import AuthenticatedUserDTO
from archipy.models.errors import PermissionDeniedError, UnauthenticatedError
from features.test_helpers import get_current_scenario_context


def _set_auth_context(scenario_context, token_info: KeycloakTokenClaimsDTO) -> None:
    auth_context = AuthenticatedUserDTO(
        user_id=str(uuid4()),
        username="user",
        email="user@example.com",
        roles=[],
        token="token",
        raw_user_info=KeycloakUserInfoDTO(),
        token_info=token_info,
    )
    reset_token = AuthContextManager.set_auth_context(auth_context)
    scenario_context.store("reset_token", reset_token)


@given('an auth context of kind "{kind}"')
def step_given_auth_context_of_kind(context, kind):
    scenario_context = get_current_scenario_context(context)
    if kind == "none":
        AuthContextManager.clear_auth_context()
    elif kind == "one organization":
        organization_uuid = uuid4()
        scenario_context.store("expected_uuid", organization_uuid)
        token_info = KeycloakTokenClaimsDTO.model_validate({"organization": {"acme": {"id": str(organization_uuid)}}})
        _set_auth_context(scenario_context, token_info)
    else:
        _set_auth_context(scenario_context, KeycloakTokenClaimsDTO(scope="openid"))


@when("the organization dependency is called")
def step_when_dependency_called(context):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("result", None)
    scenario_context.store("error", None)
    try:
        scenario_context.store("result", require_selected_organization())
    except (PermissionDeniedError, UnauthenticatedError) as e:
        scenario_context.store("error", e)
    finally:
        reset_token = scenario_context.get("reset_token")
        if reset_token is not None:
            AuthContextManager.clear_auth_context(reset_token)


@then('the dependency outcome should be "{outcome}"')
def step_then_dependency_outcome(context, outcome):
    scenario_context = get_current_scenario_context(context)
    error = scenario_context.get("error")
    if outcome == "selected":
        assert error is None, error
        assert scenario_context.get("result") == scenario_context.get("expected_uuid")
    elif outcome == "permission denied":
        assert isinstance(error, PermissionDeniedError), error
    else:
        assert isinstance(error, UnauthenticatedError), error

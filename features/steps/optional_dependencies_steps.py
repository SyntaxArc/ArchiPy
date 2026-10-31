"""Step definitions for optional dependency scenarios."""

import subprocess
import sys

from behave import given, then, when
from features.test_helpers import get_current_scenario_context

_BLOCK_JINJA2 = """
import sys
from types import SimpleNamespace

class _Blocker:
    def find_spec(self, name, path=None, target=None):
        if name == "jinja2" or name.startswith("jinja2."):
            raise ModuleNotFoundError(f"No module named {name!r}")

sys.meta_path.insert(0, _Blocker())
from archipy.adapters.email.adapters import EmailAdapter

adapter = EmailAdapter.__new__(EmailAdapter)
adapter.config = SimpleNamespace(USERNAME="sender@example.com")
adapter._create_message("a@example.com", "subject", "plain body")
print("PLAIN_OK")
try:
    adapter._create_message("a@example.com", "subject", "", template="Hello {{ name }}", template_vars={"name": "x"})
except Exception as exception:
    print(type(exception).__name__, exception.additional_data)
"""


@given("jinja2 is not installed")
def step_given_no_jinja2(context):
    get_current_scenario_context(context).store("block_jinja2", True)


@when("I build an email message without and with a template")
def step_when_build_messages(context):
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", _BLOCK_JINJA2],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    get_current_scenario_context(context).store("jinja2_result", result)


@then("the plain message should be built")
def step_then_plain_built(context):
    result = get_current_scenario_context(context).get("jinja2_result")
    assert "PLAIN_OK" in result.stdout, f"{result.stdout} {result.stderr[-500:]}"


@then('the template message should fail with a message mentioning "{text}"')
def step_then_template_fails(context, text):
    result = get_current_scenario_context(context).get("jinja2_result")
    assert "ConfigurationError" in result.stdout and text in result.stdout, f"{result.stdout} {result.stderr[-500:]}"


@when('I read the "{extra}" extra of the "{package}" package')
def step_read_package_extra(context, extra, package):
    import tomllib
    from pathlib import Path

    project = tomllib.loads(Path(f"packages/{package}/pyproject.toml").read_text())["project"]
    requirements = project["dependencies"] if extra == "base" else project["optional-dependencies"][extra]
    get_current_scenario_context(context).store("package_requirements", requirements)


@then('it should require "{requirement}"')
def step_requires(context, requirement):
    requirements = get_current_scenario_context(context).get("package_requirements")
    assert any(item.startswith(requirement) for item in requirements), f"{requirement} not in {requirements}"


@then('it should not require "{requirement}"')
def step_does_not_require(context, requirement):
    requirements = get_current_scenario_context(context).get("package_requirements")
    assert not any(item.startswith(requirement) for item in requirements), f"{requirement} found in {requirements}"

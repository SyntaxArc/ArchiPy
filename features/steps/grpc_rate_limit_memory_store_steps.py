import asyncio
import time

from behave import given, then, when

from archipy.helpers.interceptors.grpc.rate_limit import AsyncInMemoryRateLimitStore, InMemoryRateLimitStore
from features.test_helpers import get_current_scenario_context


def _call(scenario_context, method: str, *args, **kwargs):
    store = scenario_context.get("memory_store")
    if scenario_context.get("memory_store_mode") == "async":
        return asyncio.run(getattr(store, method)(*args, **kwargs))
    return getattr(store, method)(*args, **kwargs)


@given("a {mode} in-memory rate limit store")
def step_given_memory_store(context, mode):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("memory_store_mode", mode)
    scenario_context.store("memory_store", AsyncInMemoryRateLimitStore() if mode == "async" else InMemoryRateLimitStore())


@when('the counter "{name}" is incremented {times:d} times with a limit of {limit:d} per {window:d} ms')
def step_when_increment(context, name, times, limit, window):
    scenario_context = get_current_scenario_context(context)
    results = [
        _call(scenario_context, "increx", name, byint=1, ubound=limit, saturate=True, px=window, enx=True)
        for _ in range(times)
    ]
    scenario_context.store("memory_store_results", results)


@when("{milliseconds:d} ms pass")
def step_when_ms_pass(context, milliseconds):
    time.sleep(milliseconds / 1000)


@when('the counter "{name}" is refunded {times:d} times')
def step_when_refund(context, name, times):
    scenario_context = get_current_scenario_context(context)
    for _ in range(times):
        _call(scenario_context, "increx", name, byint=-1, lbound=0, saturate=True)


@then("the increments should apply {first:d}, {second:d} and {third:d}")
def step_then_applied(context, first, second, third):
    results = get_current_scenario_context(context).get("memory_store_results")
    assert [applied for _, applied in results] == [first, second, third], results


@then("the last increment should apply {applied:d}")
def step_then_last_applied(context, applied):
    results = get_current_scenario_context(context).get("memory_store_results")
    assert results[-1][1] == applied, results


@then('the counter "{name}" should have a time to live below {limit:d} ms')
def step_then_ttl_below(context, name, limit):
    ttl = _call(get_current_scenario_context(context), "pttl", name)
    assert 0 < ttl < limit, ttl


@then('the counter "{name}" should hold {value:d}')
def step_then_holds(context, name, value):
    result = _call(get_current_scenario_context(context), "increx", name, byint=0)
    assert result[0] == value, result


@then('the counter "{name}" should have no time to live record')
def step_then_no_ttl(context, name):
    assert _call(get_current_scenario_context(context), "pttl", name) == -2

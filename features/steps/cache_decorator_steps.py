import time

from behave import given, then, when

from archipy.helpers.decorators import ttl_cache_decorator
from features.test_helpers import get_current_scenario_context


# Test helper classes and functions
class ExecutionCounter:
    """Helper class to track function executions."""

    def __init__(self) -> None:
        """Initialize the execution counter."""
        self.count = 0

    def increment(self) -> None:
        """Increment the execution counter."""
        self.count += 1

    def reset(self) -> None:
        """Reset the execution counter."""
        self.count = 0


class TestClass:
    """Test class with cached methods."""

    def __init__(self, counter: ExecutionCounter) -> None:
        """Initialize the test class.

        Args:
            counter: Execution counter to track method calls.
        """
        self.counter = counter

    @ttl_cache_decorator(ttl_seconds=300, maxsize=100)
    def cached_method(self, x: int) -> int:
        """A cached method that doubles the input.

        Args:
            x: Input value.

        Returns:
            Double of the input value.
        """
        self.counter.increment()
        return x * 2

    @ttl_cache_decorator(ttl_seconds=300, maxsize=100)
    def cached_method_1(self, x: int) -> int:
        """First cached method.

        Args:
            x: Input value.

        Returns:
            Double of the input value.
        """
        self.counter.increment()
        return x * 2

    @ttl_cache_decorator(ttl_seconds=300, maxsize=100)
    def cached_method_2(self, x: int) -> int:
        """Second cached method.

        Args:
            x: Input value.

        Returns:
            Triple of the input value.
        """
        self.counter.increment()
        return x * 3

    def clear_all_caches(self) -> None:
        """Clear all cached methods."""
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, "clear_cache"):
                attr.clear_cache()


# Step implementations


@given("a function decorated with ttl_cache_decorator")
def step_given_cached_function(context):
    """Create a cached function."""
    scenario_context = get_current_scenario_context(context)
    counter = ExecutionCounter()

    @ttl_cache_decorator(ttl_seconds=300, maxsize=100)
    def test_function(x: int) -> int:
        counter.increment()
        return x * 2

    scenario_context.store("counter", counter)
    scenario_context.store("function", test_function)


@given("a function decorated with ttl_cache_decorator with TTL {ttl:d} seconds")
def step_given_cached_function_with_ttl(context, ttl):
    """Create a cached function with specific TTL."""
    scenario_context = get_current_scenario_context(context)
    counter = ExecutionCounter()

    @ttl_cache_decorator(ttl_seconds=ttl, maxsize=100)
    def test_function(x: int) -> int:
        counter.increment()
        return x * 2

    scenario_context.store("counter", counter)
    scenario_context.store("function", test_function)


@given("a function decorated with ttl_cache_decorator with maxsize {maxsize:d}")
def step_given_cached_function_with_maxsize(context, maxsize):
    """Create a cached function with specific maxsize."""
    scenario_context = get_current_scenario_context(context)
    counter = ExecutionCounter()

    @ttl_cache_decorator(ttl_seconds=300, maxsize=maxsize)
    def test_function(x: int) -> int:
        counter.increment()
        return x * 2

    scenario_context.store("counter", counter)
    scenario_context.store("function", test_function)


@given("a class with a cached method")
def step_given_class_with_cached_method(context):
    """Create a class with cached method."""
    scenario_context = get_current_scenario_context(context)
    counter = ExecutionCounter()

    # Clear any existing cache from previous scenarios
    # Create a temporary instance to access the cached method
    temp_instance = TestClass(counter)
    if hasattr(temp_instance.cached_method, "clear_cache"):
        temp_instance.cached_method.clear_cache()

    scenario_context.store("counter", counter)
    scenario_context.store("test_class", TestClass)


@given("a class with multiple cached methods")
def step_given_class_with_multiple_cached_methods(context):
    """Create a class with multiple cached methods."""
    scenario_context = get_current_scenario_context(context)
    counter = ExecutionCounter()
    test_instance = TestClass(counter)
    scenario_context.store("counter", counter)
    scenario_context.store("test_instance", test_instance)


@given("a function that returns None decorated with ttl_cache_decorator")
def step_given_cached_function_returning_none(context):
    """Create a cached function that returns None."""
    scenario_context = get_current_scenario_context(context)
    counter = ExecutionCounter()

    @ttl_cache_decorator(ttl_seconds=300, maxsize=100)
    def test_function(x: int) -> None:
        counter.increment()
        return None

    scenario_context.store("counter", counter)
    scenario_context.store("function", test_function)


@given("a function that raises exceptions decorated with ttl_cache_decorator")
def step_given_cached_function_raising_exceptions(context):
    """Create a cached function that raises exceptions."""
    scenario_context = get_current_scenario_context(context)
    counter = ExecutionCounter()

    @ttl_cache_decorator(ttl_seconds=300, maxsize=100)
    def test_function(x: int) -> int:
        counter.increment()
        raise ValueError("Test exception")

    scenario_context.store("counter", counter)
    scenario_context.store("function", test_function)


@given("a function with multiple parameters decorated with ttl_cache_decorator")
def step_given_cached_function_with_multiple_params(context):
    """Create a cached function with multiple parameters."""
    scenario_context = get_current_scenario_context(context)
    counter = ExecutionCounter()

    @ttl_cache_decorator(ttl_seconds=300, maxsize=100)
    def test_function(x: int, y: int = 0) -> int:
        counter.increment()
        return x + y

    scenario_context.store("counter", counter)
    scenario_context.store("function", test_function)


@when("I call the function with argument {arg:d}")
def step_when_call_function_with_arg(context, arg):
    """Call the function with a specific argument."""
    scenario_context = get_current_scenario_context(context)
    function = scenario_context.get("function")
    counter = scenario_context.get("counter")
    initial_count = counter.count

    try:
        result = function(arg)
        scenario_context.store("result", result)
        scenario_context.store("exception_raised", False)
    except Exception as e:
        scenario_context.store("exception", e)
        scenario_context.store("exception_raised", True)

    scenario_context.store("initial_count", initial_count)


@when("I call the function again with argument {arg:d}")
def step_when_call_function_again_with_arg(context, arg):
    """Call the function again with the same argument."""
    scenario_context = get_current_scenario_context(context)
    function = scenario_context.get("function")
    counter = scenario_context.get("counter")
    initial_count = counter.count

    result = function(arg)

    scenario_context.store("result", result)
    scenario_context.store("initial_count", initial_count)


@when("I call the function with arguments {args}")
def step_when_call_function_with_multiple_args(context, args):
    """Call the function with multiple arguments."""
    scenario_context = get_current_scenario_context(context)
    function = scenario_context.get("function")

    arg_list = [int(x.strip()) for x in args.split(",")]
    for arg in arg_list:
        function(arg)


@when("I wait for {seconds:d} seconds")
def step_when_wait_for_seconds(context, seconds):
    """Wait for a specific number of seconds."""
    time.sleep(seconds)


@when("I create an instance and call the cached method with argument {arg:d}")
def step_when_create_instance_and_call_method(context, arg):
    """Create an instance and call the cached method."""
    scenario_context = get_current_scenario_context(context)
    test_class = scenario_context.get("test_class")
    counter = scenario_context.get("counter")

    test_instance = test_class(counter)
    initial_count = counter.count

    result = test_instance.cached_method(arg)

    scenario_context.store("test_instance", test_instance)
    scenario_context.store("result", result)
    scenario_context.store("initial_count", initial_count)


@when("I call the cached method again with argument {arg:d}")
def step_when_call_cached_method_again(context, arg):
    """Call the cached method again."""
    scenario_context = get_current_scenario_context(context)
    test_instance = scenario_context.get("test_instance")
    counter = scenario_context.get("counter")
    initial_count = counter.count

    result = test_instance.cached_method(arg)

    scenario_context.store("result", result)
    scenario_context.store("initial_count", initial_count)


@when("I create two instances")
def step_when_create_two_instances(context):
    """Create two instances of the test class."""
    scenario_context = get_current_scenario_context(context)
    test_class = scenario_context.get("test_class")
    counter = scenario_context.get("counter")

    instance1 = test_class(counter)
    instance2 = test_class(counter)

    scenario_context.store("instance1", instance1)
    scenario_context.store("instance2", instance2)


@when("I call the cached method on instance 1 with argument {arg:d}")
def step_when_call_method_on_instance1(context, arg):
    """Call the cached method on instance 1."""
    scenario_context = get_current_scenario_context(context)
    instance1 = scenario_context.get("instance1")
    counter = scenario_context.get("counter")

    result1 = instance1.cached_method(arg)

    scenario_context.store("result1", result1)
    scenario_context.store("count_after_instance1", counter.count)


@when("I call the cached method on instance 2 with argument {arg:d}")
def step_when_call_method_on_instance2(context, arg):
    """Call the cached method on instance 2."""
    scenario_context = get_current_scenario_context(context)
    instance2 = scenario_context.get("instance2")
    counter = scenario_context.get("counter")
    initial_count = counter.count

    result2 = instance2.cached_method(arg)

    scenario_context.store("result2", result2)
    scenario_context.store("initial_count", initial_count)


@when("I clear the cache")
def step_when_clear_cache(context):
    """Clear the cache."""
    scenario_context = get_current_scenario_context(context)
    function = scenario_context.get("function")
    function.clear_cache()


@when("I call both cached methods")
def step_when_call_both_cached_methods(context):
    """Call both cached methods."""
    scenario_context = get_current_scenario_context(context)
    test_instance = scenario_context.get("test_instance")
    counter = scenario_context.get("counter")

    initial_count = counter.count
    test_instance.cached_method_1(5)
    test_instance.cached_method_2(5)

    scenario_context.store("initial_count", initial_count)


@when("I clear all caches")
def step_when_clear_all_caches(context):
    """Clear all caches."""
    scenario_context = get_current_scenario_context(context)
    test_instance = scenario_context.get("test_instance")
    test_instance.clear_all_caches()


@when("I call both cached methods again")
def step_when_call_both_cached_methods_again(context):
    """Call both cached methods again."""
    scenario_context = get_current_scenario_context(context)
    test_instance = scenario_context.get("test_instance")
    counter = scenario_context.get("counter")

    initial_count = counter.count
    test_instance.cached_method_1(5)
    test_instance.cached_method_2(5)

    scenario_context.store("second_call_initial_count", initial_count)


@when("I call the function with keyword argument x={arg:d}")
def step_when_call_function_with_keyword_arg(context, arg):
    """Call the function with a keyword argument."""
    scenario_context = get_current_scenario_context(context)
    function = scenario_context.get("function")
    counter = scenario_context.get("counter")
    initial_count = counter.count

    result = function(x=arg)

    scenario_context.store("result", result)
    scenario_context.store("initial_count", initial_count)


@when("I call the function with positional argument {arg:d}")
def step_when_call_function_with_positional_arg(context, arg):
    """Call the function with a positional argument."""
    scenario_context = get_current_scenario_context(context)
    function = scenario_context.get("function")
    counter = scenario_context.get("counter")
    initial_count = counter.count

    result = function(arg)

    scenario_context.store("result", result)
    scenario_context.store("initial_count", initial_count)


@when("I call the function with positional {x:d} and keyword y={y:d}")
def step_when_call_function_with_mixed_args(context, x, y):
    """Call the function with mixed positional and keyword arguments."""
    scenario_context = get_current_scenario_context(context)
    function = scenario_context.get("function")
    counter = scenario_context.get("counter")
    initial_count = counter.count

    result = function(x, y=y)

    scenario_context.store("result", result)
    scenario_context.store("initial_count", initial_count)


@when("I create an instance")
def step_when_create_instance(context):
    """Create an instance of the test class."""
    scenario_context = get_current_scenario_context(context)
    test_class = scenario_context.get("test_class")
    counter = scenario_context.get("counter")

    test_instance = test_class(counter)

    scenario_context.store("test_instance", test_instance)


@when('I call the function with string argument "{arg}"')
def step_when_call_function_with_string_arg(context, arg):
    """Call the function with a string argument."""
    scenario_context = get_current_scenario_context(context)

    # Check if function already exists
    function = scenario_context.get("function")
    counter = scenario_context.get("counter")

    if function is None:
        # Create a new function that accepts both string and int
        counter = ExecutionCounter()

        @ttl_cache_decorator(ttl_seconds=300, maxsize=100)
        def test_function(x: str | int) -> str | int:
            counter.increment()
            return x

        scenario_context.store("counter", counter)
        scenario_context.store("function", test_function)
        function = test_function

    initial_count = counter.count
    result = function(arg)
    scenario_context.store("result", result)
    scenario_context.store("initial_count", initial_count)


@when("I call the function with integer argument {arg:d}")
def step_when_call_function_with_integer_arg(context, arg):
    """Call the function with an integer argument."""
    scenario_context = get_current_scenario_context(context)
    function = scenario_context.get("function")
    counter = scenario_context.get("counter")

    initial_count = counter.count
    result = function(arg)

    scenario_context.store("result", result)
    scenario_context.store("initial_count", initial_count)


@then("the function should be executed")
def step_then_function_should_be_executed(context):
    """Verify the function was executed."""
    scenario_context = get_current_scenario_context(context)
    counter = scenario_context.get("counter")
    initial_count = scenario_context.get("initial_count")

    assert counter.count > initial_count, f"Expected function to be executed, but count remained {counter.count}"


@then("the function should be executed again")
def step_then_function_should_be_executed_again(context):
    """Verify the function was executed again."""
    scenario_context = get_current_scenario_context(context)
    counter = scenario_context.get("counter")
    initial_count = scenario_context.get("initial_count")

    assert counter.count > initial_count, f"Expected function to be executed again, but count remained {counter.count}"


@then("the result should be {expected:d}")
def step_then_result_should_be(context, expected):
    """Verify the result matches the expected value."""
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.get("result")

    assert result == expected, f"Expected result to be {expected}, but got {result}"


@then("the function should not be executed again")
def step_then_function_should_not_be_executed_again(context):
    """Verify the function was not executed again."""
    scenario_context = get_current_scenario_context(context)
    counter = scenario_context.get("counter")
    initial_count = scenario_context.get("initial_count")

    assert (
        counter.count == initial_count
    ), f"Expected function not to be executed again, but count changed from {initial_count} to {counter.count}"


@then("the execution count should be {expected:d}")
def step_then_execution_count_should_be(context, expected):
    """Verify the execution count matches the expected value."""
    scenario_context = get_current_scenario_context(context)
    counter = scenario_context.get("counter")

    assert counter.count == expected, f"Expected execution count to be {expected}, but got {counter.count}"


@then("the method should be executed")
def step_then_method_should_be_executed(context):
    """Verify the method was executed."""
    scenario_context = get_current_scenario_context(context)
    counter = scenario_context.get("counter")
    initial_count = scenario_context.get("initial_count", 0)
    count_after_instance1 = scenario_context.get("count_after_instance1", None)

    # If we have count_after_instance1, use that for comparison
    if count_after_instance1 is not None:
        assert count_after_instance1 > 0, f"Expected method to be executed, but count is {count_after_instance1}"
    else:
        assert counter.count > initial_count, f"Expected method to be executed, but count remained {counter.count}"


@then("the method should not be executed again")
def step_then_method_should_not_be_executed_again(context):
    """Verify the method was not executed again."""
    scenario_context = get_current_scenario_context(context)
    counter = scenario_context.get("counter")
    initial_count = scenario_context.get("initial_count")

    assert (
        counter.count == initial_count
    ), f"Expected method not to be executed again, but count changed from {initial_count} to {counter.count}"


@then("both instances should return the same result")
def step_then_both_instances_return_same_result(context):
    """Verify both instances return the same result."""
    scenario_context = get_current_scenario_context(context)
    result1 = scenario_context.get("result1")
    result2 = scenario_context.get("result2")

    assert result1 == result2, f"Expected both instances to return the same result, but got {result1} and {result2}"


@then("both methods should be executed")
def step_then_both_methods_should_be_executed(context):
    """Verify both methods were executed."""
    scenario_context = get_current_scenario_context(context)
    counter = scenario_context.get("counter")
    initial_count = scenario_context.get("initial_count")

    assert (
        counter.count == initial_count + 2
    ), f"Expected both methods to be executed, but count changed from {initial_count} to {counter.count}"


@then("both methods should be executed again")
def step_then_both_methods_should_be_executed_again(context):
    """Verify both methods were executed again."""
    scenario_context = get_current_scenario_context(context)
    counter = scenario_context.get("counter")
    second_call_initial_count = scenario_context.get("second_call_initial_count")

    assert (
        counter.count == second_call_initial_count + 2
    ), f"Expected both methods to be executed again, but count changed from {second_call_initial_count} to {counter.count}"


@then("the result should be None")
def step_then_result_should_be_none(context):
    """Verify the result is None."""
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.get("result")

    assert result is None, f"Expected result to be None, but got {result}"


@then("an exception should be raised")
def step_then_exception_should_be_raised(context):
    """Verify an exception is raised."""
    scenario_context = get_current_scenario_context(context)
    exception_raised = scenario_context.get("exception_raised", False)

    assert exception_raised, "Expected an exception to be raised, but none was raised"


@then("the cached method should maintain identity consistency")
def step_then_cached_method_maintains_identity(context):
    """Verify the cached method maintains identity consistency."""
    scenario_context = get_current_scenario_context(context)
    test_instance = scenario_context.get("test_instance")

    # Access the method twice and verify it's the same object
    method1 = test_instance.cached_method
    method2 = test_instance.cached_method

    assert method1 is method2, "Expected cached method to maintain identity consistency"

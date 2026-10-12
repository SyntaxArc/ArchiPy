import threading
import time

from behave import given, then, when

from archipy.helpers.decorators.singleton import singleton_decorator
from archipy.helpers.metaclasses.singleton import Singleton
from features.test_helpers import get_current_scenario_context


def _make_class(name, calls, slow=False, **meta_kwargs):
    def init(self, value=None):
        calls["count"] += 1
        if slow:
            time.sleep(0.05)
        self.value = value

    return Singleton(name, (), {"__init__": init}, **meta_kwargs)


@given("a class using the Singleton metaclass")
def step_given_singleton_class(context):
    sc = get_current_scenario_context(context)
    calls = {"count": 0}
    sc.store("singleton_calls", calls)
    sc.store("singleton_cls", _make_class("PlainSingleton", calls))


@given("two classes using the Singleton metaclass")
def step_given_two_singleton_classes(context):
    sc = get_current_scenario_context(context)
    calls = {"count": 0}
    sc.store("singleton_cls", _make_class("FirstSingleton", calls))
    sc.store("singleton_cls_other", _make_class("SecondSingleton", calls))


def _make_decorated_class(name, calls, slow=False, **kwargs):
    def init(self, value=None):
        calls["count"] += 1
        if slow:
            time.sleep(0.05)
        self.value = value

    return singleton_decorator(**kwargs)(type(name, (), {"__init__": init}))


@given("a class using the singleton decorator")
def step_given_decorated_class(context):
    sc = get_current_scenario_context(context)
    calls = {"count": 0}
    sc.store("singleton_calls", calls)
    sc.store("singleton_cls", _make_decorated_class("DecoratedSingleton", calls))


@given("a thread-safe class using the singleton decorator with a slow constructor")
def step_given_decorated_thread_safe(context):
    sc = get_current_scenario_context(context)
    calls = {"count": 0}
    sc.store("singleton_calls", calls)
    sc.store("singleton_cls", _make_decorated_class("SafeDecorated", calls, slow=True, thread_safe=True))


@then("the singleton instances are instances of the decorated class")
def step_then_decorated_isinstance(context):
    sc = get_current_scenario_context(context)
    cls = sc.get("singleton_cls")
    assert isinstance(cls, type), f"Decorated name is {cls!r}, not a class"
    assert all(isinstance(i, cls) for i in sc.get("singleton_instances"))


@given("a subclass of that singleton class")
def step_given_singleton_subclass(context):
    sc = get_current_scenario_context(context)
    parent = sc.get("singleton_cls")
    sc.store("singleton_cls_other", type("ChildSingleton", (parent,), {}))


@given("a thread-safe singleton class with a slow constructor")
def step_given_thread_safe_singleton(context):
    sc = get_current_scenario_context(context)
    calls = {"count": 0}
    sc.store("singleton_calls", calls)
    sc.store("singleton_cls", _make_class("SafeSingleton", calls, slow=True, thread_safe=True))


@given("a singleton class with default thread safety and a slow constructor")
def step_given_default_singleton(context):
    sc = get_current_scenario_context(context)
    calls = {"count": 0}
    sc.store("singleton_calls", calls)
    sc.store("singleton_cls", _make_class("DefaultSingleton", calls, slow=True))


@when("the singleton class is instantiated twice")
def step_when_singleton_twice(context):
    sc = get_current_scenario_context(context)
    cls = sc.get("singleton_cls")
    sc.store("singleton_instances", [cls(), cls()])


@when("the singleton class is instantiated with value {first:d} and then with value {second:d}")
def step_when_singleton_values(context, first, second):
    sc = get_current_scenario_context(context)
    cls = sc.get("singleton_cls")
    sc.store("singleton_instances", [cls(first), cls(second)])


@when("each singleton class is instantiated")
def step_when_each_singleton(context):
    sc = get_current_scenario_context(context)
    sc.store("singleton_instances", [sc.get("singleton_cls")(), sc.get("singleton_cls_other")()])


@when("the singleton class and its subclass are instantiated")
def step_when_singleton_and_subclass(context):
    sc = get_current_scenario_context(context)
    sc.store("singleton_instances", [sc.get("singleton_cls")(), sc.get("singleton_cls_other")()])


@when("{count:d} threads instantiate the singleton class at the same time")
def step_when_threads_instantiate(context, count):
    sc = get_current_scenario_context(context)
    cls = sc.get("singleton_cls")
    barrier = threading.Barrier(count)
    results = [None] * count

    def worker(index):
        barrier.wait()
        results[index] = cls()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)
    sc.store("singleton_instances", results)


@then("both singleton instances are the same object")
def step_then_same_object(context):
    first, second = get_current_scenario_context(context).get("singleton_instances")
    assert first is second


@then("the two singleton instances are different objects")
def step_then_different_objects(context):
    first, second = get_current_scenario_context(context).get("singleton_instances")
    assert first is not second


@then("all threads received the same singleton instance")
def step_then_threads_same(context):
    instances = get_current_scenario_context(context).get("singleton_instances")
    assert all(i is not None for i in instances)
    assert all(i is instances[0] for i in instances)


@then("the singleton constructor ran {count:d} times")
def step_then_singleton_constructor_count(context, count):
    calls = get_current_scenario_context(context).get("singleton_calls")
    assert calls["count"] == count, f"Ran {calls['count']} times"


@then("the singleton instance value is {value:d}")
def step_then_singleton_value(context, value):
    assert get_current_scenario_context(context).get("singleton_instances")[0].value == value

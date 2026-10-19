from datetime import date, datetime, timedelta

from behave import then, when

from archipy.models.dtos.pagination_dto import PaginationDTO
from archipy.models.dtos.range_dtos import (
    DateRangeDTO,
    DatetimeIntervalRangeDTO,
    DatetimeRangeDTO,
    DecimalRangeDTO,
    IntegerRangeDTO,
)
from archipy.models.dtos.search_input_dto import SearchInputDTO
from archipy.models.errors import InvalidArgumentError, OutOfRangeError
from archipy.models.types.time_interval_unit_type import TimeIntervalUnitType
from features.test_helpers import get_current_scenario_context

_RANGE_PARSERS = {
    "integer": (IntegerRangeDTO, int),
    "decimal": (DecimalRangeDTO, str),
    "date": (DateRangeDTO, date.fromisoformat),
    "datetime": (DatetimeRangeDTO, datetime.fromisoformat),
}


def _build(context, factory):
    scenario_context = get_current_scenario_context(context)
    try:
        scenario_context.store("range_result", factory())
        scenario_context.store("range_error", None)
    except (OutOfRangeError, InvalidArgumentError) as error:
        scenario_context.store("range_result", None)
        scenario_context.store("range_error", error)


@when("a {kind} range from {start} to {end} is built")
def step_when_range_built(context, kind, start, end):
    dto, parse = _RANGE_PARSERS[kind]
    _build(context, lambda: dto(from_=parse(start), to=parse(end)))


@when("an integer range with only {open_end} is built")
def step_when_open_range_built(context, open_end):
    arguments = {"a start": {"from_": 1}, "an end": {"to": 5}, "no ends": {}}[open_end]
    _build(context, lambda: IntegerRangeDTO(**arguments))


@when('a decimal range is built from the text "{start}" up to the text "{end}"')
def step_when_decimal_range_built(context, start, end):
    _build(context, lambda: DecimalRangeDTO(from_=start, to=end))


@when("an interval range of {interval} from {hours_ago_from:d} to {hours_ago_to:d} hours ago is built")
def step_when_interval_range_built(context, interval, hours_ago_from, hours_ago_to):
    now = datetime.now()
    _build(
        context,
        lambda: DatetimeIntervalRangeDTO(
            from_=now - timedelta(hours=hours_ago_from),
            to=now - timedelta(hours=hours_ago_to),
            interval=TimeIntervalUnitType[interval],
        ),
    )


@then("the range should be {outcome}")
def step_then_range_outcome(context, outcome):
    scenario_context = get_current_scenario_context(context)
    error = scenario_context.get("range_error")
    if outcome == "accepted":
        assert error is None, error
        assert scenario_context.get("range_result") is not None
    else:
        assert error is not None, "Expected the range to be rejected"


@when("a search input with page {page:d} of size {size:d} and no sort is built")
def step_when_search_input_with_page(context, page, size):
    get_current_scenario_context(context).store(
        "search_input",
        SearchInputDTO(pagination=PaginationDTO(page=page, page_size=size)),
    )


@when("a search input with no page and no sort is built")
def step_when_search_input_empty(context):
    get_current_scenario_context(context).store("search_input", SearchInputDTO())


@then("the search input should hold page {page:d} of size {size:d}")
def step_then_search_input_page(context, page, size):
    pagination = get_current_scenario_context(context).get("search_input").pagination
    assert (pagination.page, pagination.page_size) == (page, size), pagination


@then("the search input should hold no page")
def step_then_search_input_no_page(context):
    search_input = get_current_scenario_context(context).get("search_input")
    assert search_input.pagination is None and search_input.sort_info is None

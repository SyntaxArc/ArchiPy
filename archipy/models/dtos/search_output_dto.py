"""DTOs for paged search outputs."""

from typing import ClassVar

from pydantic import NonNegativeInt, computed_field

from archipy.configs.base_config import BaseConfig
from archipy.models.dtos.base_dtos import BaseDTO


class SearchOutputDTO(BaseDTO):
    """Base for paged search outputs whose total comes from ``execute_search_query``.

    ``execute_search_query`` counts exactly up to the ``COUNT_THRESHOLD`` of the SQLAlchemy config. Past it the total is
    a database estimate, and the estimate is always above the threshold, so a ``total_count`` above the threshold means
    the total is not exact. ``total_count_estimated`` reports that, so an API can show "10000+" instead of a made-up
    number.

    Only PostgreSQL estimates. Other databases count exactly, so this flag is meaningful for PostgreSQL only; use
    ``ExactSearchOutputDTO`` for totals that never come from an estimate.

    Attributes:
        total_count (int): The total number of matching rows, exact up to the threshold and an estimate above it.
        total_count_estimated (bool): True when ``total_count`` is above the configured threshold, False when no
            threshold or no global config is set. Computed.

    Class Attributes:
        count_threshold_config (str): Name of the global config field that holds the SQLAlchemy config to read
            ``COUNT_THRESHOLD`` from. Override it in a subclass for another database.

    Examples:
        >>> from archipy.models.dtos.search_output_dto import SearchOutputDTO
        >>>
        >>> class SearchUsersOutputDTO(SearchOutputDTO):
        ...     items: list[str]
        >>>
        >>> SearchUsersOutputDTO(items=["a"], total_count=1).total_count_estimated
        False
    """

    count_threshold_config: ClassVar[str] = "POSTGRES_SQLALCHEMY"

    total_count: NonNegativeInt

    @computed_field
    @property
    def total_count_estimated(self) -> bool:
        """Whether ``total_count`` is above the configured threshold, so it is a database estimate."""
        try:
            sqlalchemy_config = getattr(BaseConfig.global_config(), self.count_threshold_config, None)
        except AssertionError:
            return False
        threshold: int | None = getattr(sqlalchemy_config, "COUNT_THRESHOLD", None)
        return threshold is not None and self.total_count > threshold


class ExactSearchOutputDTO(SearchOutputDTO):
    """Paged search output whose total is always an exact count, never a database estimate.

    Use it for searches that count on their own, so the output has the same fields as ``SearchOutputDTO`` and
    ``total_count_estimated`` is always False.
    """

    @computed_field
    @property
    def total_count_estimated(self) -> bool:
        """Always False: the total is counted, not estimated."""
        return False

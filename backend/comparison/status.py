from collections import Counter
from typing import Any, Iterable

from .normalizers import is_missing, normalize_value


STATUS_PRIORITY = {
    "match": 0,
    "missing": 1,
    "review": 2,
    "mismatch": 3,
}


def comparison_status(
    work_order_value: Any,
    target_value: Any,
    normalizer_name: str,
    requires_review: bool = False,
) -> str:
    if requires_review:
        return "review"

    if is_missing(work_order_value) or is_missing(target_value):
        return "missing"

    work_order_normalized = normalize_value(
        work_order_value,
        normalizer_name,
    )
    target_normalized = normalize_value(
        target_value,
        normalizer_name,
    )

    return (
        "match"
        if work_order_normalized == target_normalized
        else "mismatch"
    )


def overall_status(statuses: Iterable[str]) -> str:
    status_list = list(statuses)

    if not status_list:
        return "missing"

    return max(status_list, key=lambda status: STATUS_PRIORITY[status])


def status_counts(statuses: Iterable[str]) -> dict[str, int]:
    counts = Counter(statuses)
    return {
        "matched": counts["match"],
        "mismatched": counts["mismatch"],
        "missing": counts["missing"],
        "review": counts["review"],
    }

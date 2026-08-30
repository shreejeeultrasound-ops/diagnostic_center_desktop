"""Indian Rupee currency formatting and human-readable date formatting.

Implemented manually (not via `locale`) because the `hi_IN`/`en_IN`
locale is frequently not installed on a bare Windows/Linux machine, and
we don't want report formatting to depend on the end user's system
locale configuration.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal


def format_inr(amount) -> str:
    """Format using the Indian numbering system, e.g. 1234567.5 ->
    '₹12,34,567.50' (last 3 digits grouped, then groups of 2).
    """
    amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    sign = "-" if amount < 0 else ""
    amount = abs(amount)
    whole, _, frac = f"{amount:.2f}".partition(".")

    if len(whole) <= 3:
        grouped = whole
    else:
        last3 = whole[-3:]
        rest = whole[:-3]
        parts = []
        while len(rest) > 2:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        grouped = ",".join(parts) + "," + last3

    return f"{sign}\u20b9{grouped}.{frac}"


def format_date(value) -> str:
    """29-Aug-2026 style, matching the layout shown in the build brief."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        value = value.date()
    if not isinstance(value, date):
        return str(value)
    return value.strftime("%d-%b-%Y")

from decimal import Decimal, InvalidOperation
from datetime import date as date_class, datetime as datetime_class

from django import template
from django.utils import timezone

from core.bs_date_utils import ad_to_bs_string
from core.calendar_mode import CALENDAR_MODE_BS, get_calendar_mode


register = template.Library()


def _group_indian_digits(integer_part: str) -> str:
    if len(integer_part) <= 3:
        return integer_part

    last_three = integer_part[-3:]
    leading = integer_part[:-3]
    groups = []

    while len(leading) > 2:
        groups.insert(0, leading[-2:])
        leading = leading[:-2]

    if leading:
        groups.insert(0, leading)

    return ",".join(groups + [last_three])


@register.filter
def npr_amount(value):
    """Format numeric values in NPR style with US-grouping commas.

    Examples:
    - 1000 -> 1,000
    - 1250.5 -> 1,250.50
    - 1250.0 -> 1,250
    """
    if value in (None, ""):
        return "0"

    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return value

    amount = amount.quantize(Decimal("0.01"))
    sign = "-" if amount < 0 else ""
    absolute = abs(amount)

    fixed = f"{absolute:.2f}"
    integer_part, fractional_part = fixed.split(".")
    grouped_integer = _group_indian_digits(integer_part)

    if fractional_part == "00":
        return f"{sign}{grouped_integer}"

    return f"{sign}{grouped_integer}.{fractional_part}"


def _as_date(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime_class):
        return value.date()
    if isinstance(value, date_class):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return date_class.fromisoformat(text)
    except ValueError:
        return None


@register.filter
def calendar_date(value, request=None):
    current_date = _as_date(value)
    if current_date is None:
        return ""

    if get_calendar_mode(request) == CALENDAR_MODE_BS:
        bs_value = ad_to_bs_string(current_date)
        return bs_value or current_date.isoformat()

    return current_date.isoformat()


@register.filter
def calendar_datetime(value, request=None):
    if not value:
        return ""

    current_datetime = value
    if not isinstance(current_datetime, datetime_class):
        try:
            current_datetime = datetime_class.fromisoformat(str(value).strip())
        except ValueError:
            return str(value)

    local_dt = timezone.localtime(current_datetime) if timezone.is_aware(current_datetime) else current_datetime
    time_label = local_dt.strftime("%H:%M")

    if get_calendar_mode(request) == CALENDAR_MODE_BS:
        bs_value = ad_to_bs_string(local_dt.date())
        return f"{bs_value} {time_label}" if bs_value else local_dt.strftime("%Y-%m-%d %H:%M")

    return local_dt.strftime("%Y-%m-%d %H:%M")

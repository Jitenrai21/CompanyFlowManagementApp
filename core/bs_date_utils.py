from __future__ import annotations

from datetime import date as date_class, datetime as datetime_class
from typing import Mapping

import nepali_datetime

from .calendar_mode import CALENDAR_MODE_AD, CALENDAR_MODE_BS, normalize_calendar_mode


def ad_to_bs_string(ad_date: date_class | None) -> str | None:
    if not ad_date:
        return None
    if isinstance(ad_date, datetime_class):
        ad_date = ad_date.date()
    elif isinstance(ad_date, str):
        try:
            ad_date = date_class.fromisoformat(ad_date.strip())
        except ValueError:
            return None
    bs_date = nepali_datetime.date.from_datetime_date(ad_date)
    return bs_date.strftime("%Y-%m-%d")


def bs_string_to_ad(bs_value: str | None) -> date_class | None:
    if not bs_value:
        return None
    value = str(bs_value).strip()
    if not value:
        return None
    try:
        year_str, month_str, day_str = value.split("-")
        bs_date = nepali_datetime.date(int(year_str), int(month_str), int(day_str))
    except (TypeError, ValueError):
        return None
    return bs_date.to_datetime_date()


def ad_string_to_date(ad_value: str | None) -> date_class | None:
    if not ad_value:
        return None
    value = str(ad_value).strip()
    if not value:
        return None
    try:
        return date_class.fromisoformat(value)
    except ValueError:
        return None


def date_to_calendar_input(ad_date: date_class | None, calendar_mode: str) -> str:
    if not ad_date:
        return ""
    if normalize_calendar_mode(calendar_mode) == CALENDAR_MODE_BS:
        return ad_to_bs_string(ad_date) or ""
    return ad_date.isoformat()


def parse_calendar_date_input(raw_value: str | None, calendar_mode: str) -> tuple[date_class | None, str | None]:
    value = str(raw_value or "").strip()
    if not value:
        return None, None

    mode = normalize_calendar_mode(calendar_mode)
    if mode == CALENDAR_MODE_BS:
        ad_value = bs_string_to_ad(value)
        if ad_value is None:
            return None, "Enter a valid BS date in YYYY-MM-DD format."
        return ad_value, None

    ad_value = ad_string_to_date(value)
    if ad_value is None:
        return None, "Enter a valid AD date in YYYY-MM-DD format."
    return ad_value, None


def resolve_ad_date_filters(
    params: Mapping[str, object],
    *,
    default_from: str = "",
    default_to: str = "",
    from_key: str = "date_from",
    to_key: str = "date_to",
    bs_from_key: str = "bs_date_from",
    bs_to_key: str = "bs_date_to",
    calendar_mode: str = CALENDAR_MODE_AD,
    errors: list[str] | None = None,
) -> tuple[str, str]:
    date_from = default_from
    date_to = default_to

    mode = normalize_calendar_mode(calendar_mode)
    raw_date_from = str(params.get(from_key, "") or "").strip()
    raw_date_to = str(params.get(to_key, "") or "").strip()

    bs_date_from = str(params.get(bs_from_key, "") or "").strip()
    bs_date_to = str(params.get(bs_to_key, "") or "").strip()

    # Legacy BS query keys continue to work even when inputs use date_from/date_to.
    if mode == CALENDAR_MODE_BS:
        raw_date_from = bs_date_from or raw_date_from
        raw_date_to = bs_date_to or raw_date_to

    if raw_date_from:
        parsed_from, from_error = parse_calendar_date_input(raw_date_from, mode)
        if parsed_from is not None:
            date_from = parsed_from.isoformat()
        elif from_error and errors is not None:
            errors.append(f"From date: {from_error}")

    if raw_date_to:
        parsed_to, to_error = parse_calendar_date_input(raw_date_to, mode)
        if parsed_to is not None:
            date_to = parsed_to.isoformat()
        elif to_error and errors is not None:
            errors.append(f"To date: {to_error}")

    if mode != CALENDAR_MODE_BS:
        ad_from_from_bs = bs_string_to_ad(bs_date_from)
        ad_to_from_bs = bs_string_to_ad(bs_date_to)

        if ad_from_from_bs is not None:
            date_from = ad_from_from_bs.isoformat()
        if ad_to_from_bs is not None:
            date_to = ad_to_from_bs.isoformat()

    return date_from, date_to


def bs_month_day_details(ad_date: date_class | None) -> dict[str, object] | None:
    if not ad_date:
        return None
    bs_date = nepali_datetime.date.from_datetime_date(ad_date)
    return {
        "bs_year": bs_date.year,
        "bs_month": bs_date.month,
        "bs_day": bs_date.day,
        "bs_month_name": bs_date.strftime("%B"),
        "bs_weekday_name": bs_date.strftime("%A"),
    }

from .calendar_mode import CALENDAR_MODE_AD, CALENDAR_MODE_BS, get_calendar_mode


def calendar_mode(request):
    mode = get_calendar_mode(request)
    return {
        "calendar_mode": mode,
        "calendar_mode_is_bs": mode == CALENDAR_MODE_BS,
        "calendar_mode_is_ad": mode == CALENDAR_MODE_AD,
    }

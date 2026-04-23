CALENDAR_MODE_SESSION_KEY = "calendar_mode"
CALENDAR_MODE_AD = "ad"
CALENDAR_MODE_BS = "bs"
CALENDAR_MODE_CHOICES = {CALENDAR_MODE_AD, CALENDAR_MODE_BS}


def normalize_calendar_mode(raw_value):
    value = str(raw_value or "").strip().lower()
    if value in CALENDAR_MODE_CHOICES:
        return value
    return CALENDAR_MODE_AD


def get_calendar_mode(request):
    if request is None:
        return CALENDAR_MODE_AD
    return normalize_calendar_mode(request.session.get(CALENDAR_MODE_SESSION_KEY, CALENDAR_MODE_AD))

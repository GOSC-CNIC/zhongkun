import datetime

from django.utils.timezone import is_aware

from rest_framework.fields import DateTimeField
from rest_framework import ISO_8601

utc = datetime.timezone.utc
GMT_FORMAT = '%a, %d %b %Y %H:%M:%S GMT'
ISO_UTC_FORMAT = '%Y-%m-%dT%H:%M:%S%z'
ISO_UTC_MICRO_FORMAT = '%Y-%m-%dT%H:%M:%S.%f%z'


def iso_to_datetime(iso_time: str):
    try:
        return DateTimeField(input_formats=[ISO_8601]).to_internal_value(iso_time)
    except Exception as e:
        return iso_time


def iso_utc_to_datetime(iso_time: str):
    try:
        return datetime.datetime.strptime(iso_time, ISO_UTC_FORMAT)
    except (ValueError, TypeError) as e:
        return None


def time_to_gmt(value):
    """
    :param value: datetime()
    :return:
        GMT time string
    """
    try:
        return DateTimeField(format=GMT_FORMAT, default_timezone=utc).to_representation(value)
    except Exception as e:
        return ''


def datetime_add_months(dt: datetime.datetime, months: int) -> datetime.datetime:
    dt_year = dt.year
    dt_month = dt.month

    year, month = divmod(months, 12)
    year += dt_year
    month = month + dt_month
    if month > 12:
        month = month - 12
        year += 1

    return dt.replace(year=year, month=month)


def days_after_months(dt: datetime.datetime, months: int) -> int:
    end = datetime_add_months(dt=dt, months=months)
    delta = end - dt
    return delta.days


def datesince_days(d, now=None, _reversed=False) -> int:
    if not isinstance(d, datetime.datetime):
        d = datetime.datetime(d.year, d.month, d.day)
    if now and not isinstance(now, datetime.datetime):
        now = datetime.datetime(now.year, now.month, now.day)

    now = now or datetime.datetime.now(utc if is_aware(d) else None)

    if _reversed:
        d, now = now, d

    delta = now.date() - d.date()
    since_days = delta.days
    if since_days <= 0:
        return 0

    return since_days


def dateuntil_days(d, now=None) -> int:
    """
    Like timesince, but return a string measuring the time until the given time.
    """
    return datesince_days(d, now, _reversed=True)

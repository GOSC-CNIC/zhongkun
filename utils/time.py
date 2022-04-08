from datetime import datetime
from pytz import utc

from rest_framework.fields import DateTimeField
from rest_framework import ISO_8601


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
        return datetime.strptime(iso_time, ISO_UTC_FORMAT)
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


def datetime_add_months(dt: datetime, months: int) -> datetime:
    dt_year = dt.year
    dt_month = dt.month

    year, month = divmod(months, 12)
    year += dt_year
    month = month + dt_month
    if month > 12:
        month = month - 12
        year += 1

    return dt.replace(year=year, month=month)


def days_after_months(dt: datetime, months: int) -> int:
    end = datetime_add_months(dt=dt, months=months)
    delta = end - dt
    return delta.days

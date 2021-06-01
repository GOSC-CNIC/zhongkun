from pytz import utc
from rest_framework.fields import DateTimeField
from rest_framework import ISO_8601


GMT_FORMAT = '%a, %d %b %Y %H:%M:%S GMT'


def iso_to_datetime(iso_time: str):
    try:
        return DateTimeField(input_formats=[ISO_8601]).to_internal_value(iso_time)
    except Exception as e:
        return iso_time


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


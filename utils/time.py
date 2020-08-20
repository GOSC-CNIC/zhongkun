from rest_framework.fields import DateTimeField
from rest_framework import ISO_8601


def iso_to_datetime(iso_time: str):
    try:
        return DateTimeField(input_formats=[ISO_8601]).to_internal_value(iso_time)
    except Exception as e:
        return iso_time

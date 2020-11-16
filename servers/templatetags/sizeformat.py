from django import template
from django.utils import formats
from django.utils.html import avoid_wrapping
from django.utils.translation import ugettext, ungettext

register = template.Library()


@register.filter(is_safe=True)
def sizeformat(value, arg="B"):
    """
    Formats the value like a 'human-readable' file size (i.e. 13 KB, 4.1 MB,
    102 bytes, etc).
    """
    try:
        bytes = float(value)
    except (TypeError, ValueError, UnicodeDecodeError):
        value = ungettext("%(size)d byte", "%(size)d bytes", 0) % {'size': 0}
        return avoid_wrapping(value)

    filesize_number_format = lambda value: formats.number_format(round(value, 1), 1)

    KB = 1 << 10
    MB = 1 << 20
    GB = 1 << 30
    TB = 1 << 40
    PB = 1 << 50

    # 在原函数的基础上，添加了单位参数，使不同量级数据都可以被格式化
    switch = {
        'KB': KB,
        'MB': MB,
        'GB': GB,
        'TB': TB,
        'PB': PB
    }
    if arg in switch:
        bytes *= switch[arg]

    if bytes < KB:
        value = ungettext("%(size)d byte", "%(size)d bytes", bytes) % {'size': bytes}
    elif bytes < MB:
        value = ugettext("%s KB") % filesize_number_format(bytes / KB)
    elif bytes < GB:
        value = ugettext("%s MB") % filesize_number_format(bytes / MB)
    elif bytes < TB:
        value = ugettext("%s GB") % filesize_number_format(bytes / GB)
    elif bytes < PB:
        value = ugettext("%s TB") % filesize_number_format(bytes / TB)
    else:
        value = ugettext("%s PB") % filesize_number_format(bytes / PB)

    return avoid_wrapping(value)


@register.filter
def subtract(value, arg):
    """相减"""
    return value - arg


@register.filter
def subtract_min_0(value, arg):
    """
    相减，最小值为0
    """
    v = value - arg
    return 0 if v < 0 else v


@register.filter
def subtract_ratio(value):
    """
    剩余百分号比率
    :param value: like 66%, 66
    :return:
        str     # xx%
    """
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return '100%'

        v = value.split('%')
        try:
            iv = float(v[0])
        except ValueError:
            return ''

        n = 100 - iv
    elif isinstance(value, (float, int)):
        if value <= 0:
            n = 100
        else:
            n = max(100 - value, 0)
    else:
        return ''

    return f'{n}%'



import string
import random
import uuid

import shortuuid
from django.utils import timezone


def random_string(length: int):
    """
    数字、大小写字母、标点符号 随机字符串
    """
    letters = string.ascii_letters + string.digits + string.punctuation
    items = [random.choice(letters) for _ in range(length)]
    return ''.join(items)


def random_letter_digit_string(length: int):
    """
    数字、大小写字母 随机字符串
    """
    letters = string.ascii_letters + string.digits
    items = [random.choice(letters) for _ in range(length)]
    if items[0] == '0':
        letters = letters.replace('0', '')
        items[0] = random.choice(letters)

    return ''.join(items)


def random_digit_string(length: int):
    """
    数字 随机字符串
    """
    items = [random.choice(string.digits) for _ in range(length)]
    if items[0] == '0':
        items[0] = random.choice('123456789')

    return ''.join(items)


def random_hexdigit_string(length: int):
    """
    十六进制字符 随机字符串
    """
    items = [random.choice(string.hexdigits) for _ in range(length)]
    if items[0] == '0':
        hexdigits = string.hexdigits.replace('0', '')
        items[0] = random.choice(hexdigits)

    return ''.join(items)


def timestamp20_rand4_sn():
    """
    生成时间+随机数的流水号
    长24位: 日期+纳秒+4位随机数
    """
    t = timezone.now()
    rand = random.randint(0, 9999)
    return f"{t.year:04}{t.month:02}{t.day:02}{t.hour:02}{t.minute:02}{t.second:02}{t.microsecond:06}{rand:04}"


def timestamp14_sn():
    t = timezone.now()
    return f"{t.year:04}{t.month:02}{t.day:02}{t.hour:02}{t.minute:02}{t.second:02}"


def timestamp20_sn():
    """
    生成时间的流水号
    长20位: 日期+纳秒
    """
    t = timezone.now()
    return f"{t.year:04}{t.month:02}{t.day:02}{t.hour:02}{t.minute:02}{t.second:02}{t.microsecond:06}"


def date8_random_digit_string(rand_length: int):
    """
    生成日期+随机数的流水号
    长24位: 日期8 + rand_length位随机数
    """
    t = timezone.now()
    s = random_digit_string(rand_length)
    return f"{t.year:04}{t.month:02}{t.day:02}{s}"


def timestamp14_microsecond2_sn():
    """
    生成时间的流水号
    长16位: 日期+2位微妙
    """
    t = timezone.now()
    microsecond = f'{t.microsecond:06}'
    return f"{t.year:04}{t.month:02}{t.day:02}{t.hour:02}{t.minute:02}{t.second:02}{microsecond[0:2]}"


def short_uuid1_25():
    return shortuuid.ShortUUID(alphabet='0123456789abcdefghijkmnopqrstuvwxyz').encode(uuid.uuid1())

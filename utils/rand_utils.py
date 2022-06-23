import string
import random

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
    return ''.join(items)


def random_digit_string(length: int):
    """
    数字 随机字符串
    """
    items = [random.choice(string.digits) for _ in range(length)]
    return ''.join(items)


def random_hexdigit_string(length: int):
    """
    十六进制字符 随机字符串
    """
    items = [random.choice(string.hexdigits) for _ in range(length)]
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


def date8_random_digit_string(rand_length: int):
    """
    生成日期+随机数的流水号
    长24位: 日期8 + rand_length位随机数
    """
    t = timezone.now()
    s = random_digit_string(rand_length)
    return f"{t.year:04}{t.month:02}{t.day:02}{s}"

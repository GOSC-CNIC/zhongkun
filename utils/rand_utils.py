import string
import random


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

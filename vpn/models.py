import random
import string

from django.contrib.auth import get_user_model


User = get_user_model()
app_name = 'vpn'


def rand_string(length=10):
    """
    生成随机字符串

    :param length: 字符串长度
    :return:
        str
    """
    if length <= 0:
        return ''

    return ''.join(random.sample(string.ascii_letters + string.digits, length))

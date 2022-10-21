from core import errors
from .models import UserProfile


def get_user_by_name(username: str):
    user = UserProfile.objects.filter(username=username).first()
    if user is None:
        raise errors.UserNotExist()

    return user


def get_user_by_id(user_id: str):
    user = UserProfile.objects.filter(id=user_id).first()
    if user is None:
        raise errors.UserNotExist()

    return user

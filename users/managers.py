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


def filter_user_queryset(search: str = None, is_federal_admin: bool = None):
    queryset = UserProfile.objects.filter(is_active=True).order_by('-date_joined')

    if search:
        queryset = queryset.filter(username__icontains=search)

    if is_federal_admin:
        queryset = queryset.filter(role__icontains=UserProfile.Roles.FEDERAL.value)

    return queryset

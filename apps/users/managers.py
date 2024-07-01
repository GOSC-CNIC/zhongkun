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


def filter_user_queryset(
        search: str = None, is_federal_admin: bool = None, date_joined_start=None, date_joined_end=None
):
    queryset = UserProfile.objects.filter(is_active=True).order_by('-date_joined')

    if search:
        queryset = queryset.filter(username__icontains=search)

    if is_federal_admin:
        queryset = queryset.filter(is_fed_admin=True)

    if date_joined_start:
        queryset = queryset.filter(date_joined__gte=date_joined_start)

    if date_joined_end:
        queryset = queryset.filter(date_joined__lte=date_joined_end)

    return queryset

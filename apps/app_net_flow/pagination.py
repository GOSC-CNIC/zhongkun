from rest_framework.pagination import LimitOffsetPagination


class LimitOffsetPage(LimitOffsetPagination):
    default_limit = 1000
    max_limit = 3000

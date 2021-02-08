from collections import OrderedDict

from rest_framework.pagination import LimitOffsetPagination, CursorPagination
from rest_framework.response import Response


class ServersPagination(CursorPagination):
    ordering = '-creation_time'
    page_size_query_param = 'page-size'
    page_size = 20

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('servers', data)
        ]))

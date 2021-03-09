from collections import OrderedDict

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class ServersPagination(PageNumberPagination):
    ordering = '-creation_time'
    page_size_query_param = 'page_size'
    page_size = 20

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('servers', data)
        ]))


class DefaultPageNumberPagination(PageNumberPagination):
    page_size_query_param = 'page_size'
    # page_size = 20


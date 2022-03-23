from collections import OrderedDict

from django.utils.translation import gettext_lazy as _
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


class OrderPageNumberPagination(PageNumberPagination):
    page_size_query_param = 'page_size'
    page_size_query_description = _('每页数据数量。')
    page_query_description = _('页码。')
    page_size = 20
    max_page_size = 200

    def get_paginated_response(self, data):
        page_size = self.page.paginator.per_page
        page_num = self.page.number
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('page_num', page_num),
            ('page_size', page_size),
            # ('next', self.get_next_link()),
            # ('previous', self.get_previous_link()),
            ('orders', data)
        ]))

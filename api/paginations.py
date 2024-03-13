from collections import OrderedDict
from urllib import parse

from django.utils.translation import gettext_lazy as _
from rest_framework.pagination import PageNumberPagination, CursorPagination
from rest_framework.response import Response


class ServersPagination(PageNumberPagination):
    ordering = '-creation_time'
    page_size_query_param = 'page_size'
    page_size = 20
    max_page_size = 2000

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('servers', data)
        ]))


class ImagesPagination(PageNumberPagination):
    page_size_query_param = 'page_size'
    page_size = 20
    max_page_size = 2000
    results_key_name = 'results'

    def get_paginated_response(self, data, count: int, page_num: int, page_size: int):
        return Response(OrderedDict([
            ('count', count),
            ('page_num', page_num),
            ('page_size', page_size),
            (self.results_key_name, data)
        ]))


class DefaultPageNumberPagination(PageNumberPagination):
    page_size_query_param = 'page_size'
    # page_size = 20
    max_page_size = 2000


class NewPageNumberPagination(PageNumberPagination):
    page_size_query_param = 'page_size'
    page_size_query_description = _('每页数据数量。')
    page_query_description = _('页码。')
    page_size = 20
    max_page_size = 2000
    results_key_name = 'results'

    def get_paginated_response(self, data):
        page_size = self.page.paginator.per_page
        page_num = self.page.number
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('page_num', page_num),
            ('page_size', page_size),
            # ('next', self.get_next_link()),
            # ('previous', self.get_previous_link()),
            (self.results_key_name, data)
        ]))


class NewPageNumberPagination100(NewPageNumberPagination):
    page_size = 100


class OrderPageNumberPagination(NewPageNumberPagination):
    page_size = 20
    max_page_size = 2000
    results_key_name = 'orders'


class MeteringPageNumberPagination(NewPageNumberPagination):
    page_size = 100
    max_page_size = 2000


class MarkerCursorPagination(CursorPagination):
    cursor_query_param = 'marker'
    cursor_query_description = 'The pagination key-marker value.'
    page_size_query_param = 'page_size'
    page_size = 100
    max_page_size = 2000
    invalid_cursor_message = 'Invalid key-marker'
    ordering = '-creation_time'

    def paginate_queryset(self, queryset, request, view=None):
        self.request = request
        return super().paginate_queryset(queryset=queryset, request=request, view=view)

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('has_next', self.has_next),
            ('page_size', self.page_size),
            ('marker', self.get_marker(self.request)),
            ('next_marker', self.get_next_marker()),
            ('results', data)
        ]))

    def get_marker(self, request):
        return request.query_params.get(self.cursor_query_param, None)

    def get_next_marker(self):
        next_url = self.get_next_link()
        return self.get_query_param(next_url, key=self.cursor_query_param)

    @staticmethod
    def get_query_param(url, key):
        (scheme, netloc, path, query, fragment) = parse.urlsplit(url)
        query_dict = parse.parse_qs(query, keep_blank_values=True)
        marker = query_dict.pop(key, None)
        if marker and isinstance(marker, list):
            marker = marker[0]

        return marker


class PaymentHistoryPagination(MarkerCursorPagination):
    ordering = '-payment_time'


class StatementPageNumberPagination(NewPageNumberPagination):
    page_size = 20
    max_page_size = 2000
    results_key_name = 'statements'


class FollowUpMarkerCursorPagination(MarkerCursorPagination):
    ordering = '-submit_time'


class TradeBillPagination(MarkerCursorPagination):
    page_size = 100
    max_page_size = 2000
    ordering = '-creation_time'


class MonitorPageNumberPagination(NewPageNumberPagination):
    page_size = 100
    max_page_size = 2000


class MonitorWebsiteTaskPagination(MarkerCursorPagination):
    page_size = 2000
    max_page_size = 10000
    ordering = '-creation'
    

class ScanTaskPageNumberPagination(NewPageNumberPagination):
    ordering = '-create_time'

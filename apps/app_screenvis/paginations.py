import base64
from urllib import parse
from collections import OrderedDict, namedtuple

from django.utils.translation import gettext_lazy as _
from django.utils.encoding import force_str
from rest_framework.pagination import PageNumberPagination, BasePagination
from rest_framework.response import Response
from rest_framework.compat import coreapi, coreschema


def _positive_int(integer_string, strict=False, cutoff=None):
    """
    Cast a string to a strictly positive integer.
    """
    ret = int(integer_string)
    if ret < 0 or (ret == 0 and strict):
        raise ValueError()
    if cutoff:
        return min(ret, cutoff)
    return ret


def _reverse_ordering(ordering_tuple):
    """
    Given an order_by tuple such as `('-created', 'uuid')` reverse the
    ordering and return a new tuple, eg. `('created', '-uuid')`.
    """
    def invert(x):
        return x[1:] if x.startswith('-') else '-' + x

    return tuple([invert(item) for item in ordering_tuple])


Marker = namedtuple('Marker', ['position'])


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
            (self.results_key_name, data)
        ]))


class NewPageNumberPagination100(NewPageNumberPagination):
    page_size = 100


class AlertPagination(BasePagination):
    ordering = '-creation'  # 不唯一时，分页可能会跳过一些排序值相同的数据记录
    marker_query_param = 'marker'
    marker_query_description = _('分页标记值')
    page_size = 100
    max_page_size = 2000
    invalid_marker_message = _('分页标记值无效')
    page_size_query_param = 'page_size'
    page_size_query_description = _('每页数据量')

    def paginate_queryset(self, querysets: list, request, view=None):
        self.request = request
        self.page_size = self.get_page_size(request)
        if not self.page_size:
            return None

        self.marker = self.decode_marker(request)
        if self.marker is None:
            current_position = None
        else:
            current_position = self.marker.position

        querysets = [qs.order_by(self.ordering) for qs in querysets]

        # If we have a cursor with a fixed position then filter by that.
        if current_position is not None:
            order = self.ordering
            order_attr = order.lstrip('-')
            kwargs = {order_attr + '__lt': current_position}
            querysets = [qs.filter(**kwargs) for qs in querysets]

        results = self.get_page_results(querysets=querysets, page_size=self.page_size, ordering=self.ordering)
        self.page = list(results[:self.page_size])

        # Determine the position of the final item following the page.
        if len(results) > len(self.page):
            has_following_position = True
            next_position = self._get_position_from_instance(self.page[-1], self.ordering)
            # following_position = self._get_position_from_instance(results[-1], self.ordering)
        else:
            has_following_position = False
            next_position = None
            # following_position = None

        # Determine next and previous positions for forward cursors.
        self.has_next = has_following_position
        self.next_position = next_position

        return self.page

    @staticmethod
    def get_page_results(querysets, page_size: int, ordering: str) -> list:
        if len(querysets) == 1:
            return list(querysets[0][0:page_size + 1])

        results = []
        for qs in querysets:
            results += list(qs[0:page_size + 1])

        is_reversed = ordering.startswith('-')
        order_attr = ordering.lstrip('-')
        results = sorted(results, key=lambda x: getattr(x, order_attr), reverse=is_reversed)
        return results[0:page_size + 1]

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('has_next', self.has_next),
            ('next_marker', self.get_next_marker()),
            ('marker', self.get_marker(self.request)),
            ('results', data)
        ]))

    def get_page_size(self, request):
        if self.page_size_query_param:
            try:
                return _positive_int(
                    request.query_params[self.page_size_query_param],
                    strict=True,
                    cutoff=self.max_page_size
                )
            except (KeyError, ValueError):
                pass

        return self.page_size

    @staticmethod
    def _get_position_from_instance(instance, ordering: str):
        field_name = ordering.lstrip('-')
        if isinstance(instance, dict):
            attr = instance[field_name]
        else:
            attr = getattr(instance, field_name)

        return str(attr)

    def get_next_marker(self):
        if not self.has_next:
            return None

        return self.encode_marker(Marker(position=self.next_position))

    @staticmethod
    def encode_marker(marker: Marker):
        """
        Given a Cursor instance, return an url with encoded cursor.
        """
        tokens = {'p': marker.position}
        querystring = parse.urlencode(tokens, doseq=True)
        encoded = base64.b64encode(querystring.encode('ascii')).decode('ascii')
        return encoded

    def get_marker(self, request):
        return request.query_params.get(self.marker_query_param)

    def decode_marker(self, request):
        """
        Given a request with a cursor, return a `Cursor` instance.
        """
        marker = self.get_marker(request=request)
        if marker is None:
            return None

        try:
            querystring = base64.b64decode(marker.encode('ascii')).decode('ascii')
            tokens = parse.parse_qs(querystring, keep_blank_values=True)

            position = tokens.get('p', [None])[0]
        except (TypeError, ValueError):
            raise Exception(_('标记无效'))

        return Marker(position=position)

    def get_schema_fields(self, view):
        assert coreapi is not None, 'coreapi must be installed to use `get_schema_fields()`'
        assert coreschema is not None, 'coreschema must be installed to use `get_schema_fields()`'
        fields = [
            coreapi.Field(
                name=self.marker_query_param,
                required=False,
                location='query',
                schema=coreschema.String(
                    title='Cursor',
                    description=force_str(self.marker_query_description)
                )
            )
        ]
        if self.page_size_query_param is not None:
            fields.append(
                coreapi.Field(
                    name=self.page_size_query_param,
                    required=False,
                    location='query',
                    schema=coreschema.Integer(
                        title='Page size',
                        description=force_str(self.page_size_query_description)
                    )
                )
            )
        return fields

    def get_schema_operation_parameters(self, view):
        parameters = [
            {
                'name': self.marker_query_param,
                'required': False,
                'in': 'query',
                'description': self.marker_query_description,
                'schema': {
                    'type': 'string',
                },
            }
        ]
        if self.page_size_query_param is not None:
            parameters.append(
                {
                    'name': self.page_size_query_param,
                    'required': False,
                    'in': 'query',
                    'description': self.page_size_query_description,
                    'schema': {
                        'type': 'integer',
                    },
                }
            )
        return parameters

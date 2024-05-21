from rest_framework.pagination import LimitOffsetPagination
from rest_framework.pagination import CursorPagination
from rest_framework.pagination import BasePagination
from rest_framework.utils.urls import remove_query_param, replace_query_param
from django.db.models.query import QuerySet
from base64 import b64decode, b64encode
import json
from django.db.models.functions import Substr


class LimitOffsetPage(LimitOffsetPagination):
    default_limit = 1000
    max_limit = 3000


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


class CustomAlertCursorPagination(BasePagination):
    page_size = 50
    # 默认排序规则：按pk从小到大排序，-pk表示从大到小排序
    cursor_query_param = 'cursor'
    page_size_query_param = 'page_size'
    # Set to an integer to limit the maximum page size the client may request.
    # Only relevant if 'page_size_query_param' has also been set.
    max_page_size = 100

    @staticmethod
    def get_object_count(queryset_list):
        """
        统计数据条数
        """
        if isinstance(queryset_list, QuerySet):
            queryset_list = [queryset_list]
        count = 0
        for queryset in queryset_list:
            count += queryset.count()
        return count

    def _paginate_queryset(self, queryset_list, base_url, page_size, cursor):
        """
        数据按照 creation 字段降序
        backend <--- cursor ---> forward
        """
        total_count = self.get_object_count(queryset_list)

        if cursor is None:  # 是第一页
            forward_list = self.queryset_slice_sort(queryset_list, page_size)
            if len(forward_list) <= page_size:  # 没有下一页
                page_data_list = forward_list
                next_link = None
                previous_link = None
            else:  # 存在下一页
                page_data_list = forward_list[:page_size]  # 截取 page_size 位
                next_link = replace_query_param(
                    url=base_url,
                    key=self.cursor_query_param,
                    val=f'{forward_list[page_size].creation}')
                previous_link = None
            return page_data_list, previous_link, next_link, total_count

        else:  # 不是第一页
            forward_queryset_list = [queryset.filter(creation__lte=cursor, ) for queryset in
                                     queryset_list]  # 游标右边的数据集
            backend_queryset_list = [queryset.filter(creation__gt=cursor, ) for queryset in
                                     queryset_list]  # 游标左边的数据集
            forward_list = self.queryset_slice_sort(forward_queryset_list, page_size)
            if len(forward_list) <= page_size:
                page_data_list = forward_list
                next_link = None
            else:
                page_data_list = forward_list[:page_size]
                next_link = replace_query_param(
                    url=base_url,
                    key=self.cursor_query_param,
                    val=f'{forward_list[page_size].creation}')
            backend_list = self.queryset_slice_sort(backend_queryset_list, page_size, reverse=True)
            if backend_list:
                previous_link = replace_query_param(
                    url=base_url,
                    key=self.cursor_query_param,
                    val=f'{backend_list[0].creation}')
            else:
                previous_link = None
            return page_data_list, previous_link, next_link, total_count

    def queryset_slice_sort(self, queryset_list, page_size, reverse=False):
        objects = []
        for queryset in queryset_list:
            objects.extend(self.queryset_slice(queryset, page_size, reverse=reverse))
        return self.queryset_sort(objects)  # 将整个列表按照creation重新排序

    @staticmethod
    def queryset_sort(queryset_list):
        queryset_list.sort(reverse=True, key=lambda obj: obj.creation)
        return queryset_list

    def queryset_slice(self, queryset, page_size, reverse=False) -> list:
        """
        尝试截取 page_size + 1条数据
        """
        count = self.get_object_count(queryset)
        if reverse is False:
            queryset = queryset if count <= page_size else queryset[:page_size + 1]  # page_size + 1
        else:
            queryset = queryset if count <= page_size else queryset[count - (page_size + 1):]
        return [_ for _ in queryset]

    def paginate_queryset(self, queryset_list, request, view=None):
        page_size = self.get_page_size(request)  # 每页的条目数
        cursor = self.get_cursor(request)  # 时间戳
        base_url = request.build_absolute_uri()
        return self._paginate_queryset(queryset_list, base_url, page_size, cursor)

    def get_cursor(self, request):
        if self.cursor_query_param:
            return request.query_params.get(self.cursor_query_param)
        return None

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

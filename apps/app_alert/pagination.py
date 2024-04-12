from rest_framework.pagination import LimitOffsetPagination


class LimitOffsetPage(LimitOffsetPagination):
    default_limit = 1000
    max_limit = 3000


class AlertCustomLimitOffset(LimitOffsetPage):

    def __init__(self, query_set_list):
        self.query_set_list = query_set_list

    def get_count(self, queryset):
        """
        Determine an object count, supporting either querysets or regular lists.
        """
        count = 0
        for queryset in self.query_set_list:
            count += queryset.count()
        return count

    def paginate_queryset(self, queryset, request, view=None):
        self.limit = self.get_limit(request)
        if self.limit is None:
            return None

        self.count = self.get_count(queryset)
        self.offset = self.get_offset(request)
        self.request = request
        if self.count > self.limit and self.template is not None:
            self.display_page_controls = True

        if self.count == 0 or self.offset > self.count:
            return []
        object_list = []
        for index, item in enumerate(queryset):
            if self.offset <= index < self.offset + self.limit:
                object_list.append(item)
            if index > self.offset + self.limit:
                break
        return object_list

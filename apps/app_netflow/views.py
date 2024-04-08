from django.shortcuts import render
from rest_framework.generics import GenericAPIView
from apps.app_netflow.models import MenuCategoryModel
from apps.app_netflow.models import ChartModel
from apps.app_netflow.models import MenuModel
from apps.app_netflow.serializers import MenuCategorySerializer
from apps.app_netflow.serializers import ChartModelSerializer
from django_filters.rest_framework import DjangoFilterBackend
from apps.app_netflow.filters import MenuCategoryFilter
from apps.app_netflow.filters import ChartFilter
from apps.app_netflow.pagination import LimitOffsetPage
from apps.app_netflow.permission import SubCategoryPermission
from rest_framework.response import Response


# Create your views here.
class MenuAPIView(GenericAPIView):
    queryset = MenuCategoryModel.objects.all()
    serializer_class = MenuCategorySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = MenuCategoryFilter
    pagination_class = LimitOffsetPage
    # permission_classes = [CustomPermission]

    def get(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class ChartAPIView(GenericAPIView):
    queryset = ChartModel.objects.all()
    serializer_class = ChartModelSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ChartFilter
    pagination_class = LimitOffsetPage
    permission_classes = [SubCategoryPermission]

    def get(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from apps.servers.models import Flavor
from apps.servers import serializers
from core.adapters import inputs
from core import errors as exceptions
from apps.api.viewsets import CustomGenericViewSet
from apps.api.paginations import ImagesPagination


class ImageViewSet(CustomGenericViewSet):
    """
    系统镜像视图
    """
    permission_classes = [IsAuthenticated, ]
    pagination_class = ImagesPagination
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'
    serializer_class = Serializer

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举镜像'),
        deprecated=True,
        manual_parameters=[
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description='服务端点id'
            ),
        ],
        responses={
            200: """"""
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举镜像

            200：
            [
              {
                "id": "18",
                "name": "Ubuntu 2004",
                "release": 系统发行版本，取值空间为{"Windows Desktop", "Windows Server", "Ubuntu", "Fedora", "Centos", "Unknown"},
                "version":系统发行编号（64字符内），取值空间为{"win10","win11","2021","2019","2204","2004","36","37","7","8","9","Unknown",....}
                "architecture":系统架构，取值空间为{"x86-64","i386","arm-64","Unknown"}
                "system_type": 系统类型，取值空间为{"Linux",“Windows","Unknown"}
                "creation_time": "0001-01-01T00:00:00Z",
                "desc": "Ubuntu 2004 旧镜像",
                "default_user": "root",
                "default_password": "cnic.cn",
                "min_sys_disk_gb": 200,
                "min_ram_mb": 0
              }
            ]
        """
        try:
            service = self.get_service(request)
        except exceptions.APIException as exc:
            return Response(exc.err_data(), status=exc.status_code)

        try:
            params = inputs.ListImageInput(region_id=service.region_id, page_num=1, page_size=100, flavor_id='')
            r = self.request_service(service, method='list_images', params=params)
            serializer = serializers.ImageOldSerializer(r.images, many=True)
            return Response(data=serializer.data)
        except exceptions.AuthenticationFailed as exc:
            return Response(data=exc.err_data(), status=500)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('分页列举镜像'),
        manual_parameters=[
            openapi.Parameter(
                name='flavor_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='配置ID（针对阿里云，规格与镜像存在依赖关系）'
            ),
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description='服务端点id'
            ),
        ],
        responses={
            200: """"""
        }
    )
    @action(methods=['GET'], detail=False, url_path='paginate', url_name='paginate-list')
    def paginate_list(self, request, *args, **kwargs):
        """
        列举镜像

            200：
            {
                "count": 10,
                "page_num": 1,
                "page_size": 20,
                "results":[
                  {
                    "id": "18",
                    "name": "Ubuntu 2004",
                    "release": 系统发行版本，取值空间为{"Windows Desktop", "Windows Server", "Ubuntu", "Fedora", "Centos", "OpenEuler", "Unknown"},
                    "version":系统发行编号（64字符内），取值空间为{"win10","win11","2021","2019","2204","2004","36","37","7","8","9","Unknown",....}
                    "architecture":系统架构，取值空间为{"x86-64","i386","arm-64","Unknown"}
                    "system_type": 系统类型，取值空间为{"Linux",“Windows","Unknown"}
                    "creation_time": "0001-01-01T00:00:00Z",
                    "desc": "Ubuntu 2004 旧镜像",
                    "default_user": "root",
                    "default_password": "cnic.cn",
                    "min_sys_disk_gb": 200,
                    "min_ram_mb": 0
                  }
                ]
            }
        """
        try:
            service = self.get_service(request)
        except exceptions.APIException as exc:
            return Response(exc.err_data(), status=exc.status_code)

        try:
            page_num = self.paginator.get_page_number(request, self.paginator)
            page_size = self.paginator.get_page_size(request)
            flavor_id = request.query_params.get('flavor_id', '')
            service_flavor_id = ''
            if flavor_id:
                flavor = Flavor.objects.filter(id=flavor_id).first()
                if flavor:
                    service_flavor_id = flavor.flavor_id

            params = inputs.ListImageInput(region_id=service.region_id, page_num=page_num, page_size=page_size,
                                           flavor_id=service_flavor_id)
            r = self.request_service(service, method='list_images', params=params)

            serializer = serializers.ImageSerializer(r.images, many=True)
            response = self.paginator.get_paginated_response(data=serializer.data, count=r.count,
                                                             page_num=int(page_num), page_size=page_size)
        except exceptions.AuthenticationFailed as exc:
            return Response(data=exc.err_data(), status=500)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        return response

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询镜像信息'),
        manual_parameters=[
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description='服务端点id'
            ),
        ],
        responses={
            200: """"""
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        查询镜像信息

            200：
            {
                "id": "18",
                "name": "Ubuntu 2004",
                "release": 系统发行版本，取值空间为{"Windows Desktop", "Windows Server", "Ubuntu", "Fedora", "Centos", "Unknown"},
                "version":系统发行编号（64字符内），取值空间为{"win10","win11","2021","2019","2204","2004","36","37","7","8","9","Unknown",....}
                "architecture":系统架构，取值空间为{"x86-64","i386","arm-64","Unknown"}
                "system_type": "Linux",
                "creation_time": "0001-01-01T00:00:00Z",
                "desc": "Ubuntu 2004 旧镜像",
                "default_user": "root",
                "default_password": "cnic.cn",
                "min_sys_disk_gb": 200,
                "min_ram_mb": 0
            }
        """
        image_id = kwargs.get(self.lookup_field)
        try:
            service = self.get_service(request)
        except exceptions.APIException as exc:
            return Response(exc.err_data(), status=exc.status_code)

        params = inputs.ImageDetailInput(image_id=image_id, region_id=service.region_id)
        try:
            r = self.request_service(service, method='image_detail', params=params)
        except exceptions.AuthenticationFailed as exc:
            return Response(data=exc.err_data(), status=500)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        serializer = serializers.ImageSerializer(instance=r.image, many=False)
        return Response(data=serializer.data)


class NetworkViewSet(CustomGenericViewSet):
    """
    网络子网视图
    """
    permission_classes = [IsAuthenticated, ]
    pagination_class = None
    lookup_field = 'network_id'
    lookup_value_regex = '[0-9a-z-]+'
    serializer_class = Serializer

    @swagger_auto_schema(
        operation_summary=gettext_lazy('网络列表'),
        manual_parameters=[
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description='服务id'
            ),
            openapi.Parameter(
                name='azone_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='可用区编码，只列举可用区内的网络'
            ),
        ],
        responses={
            200: """
                [
                  {
                    "id": "9c70cbe2-690c-11eb-a4b7-c8009fe2eb10",
                    "name": "private_10.108.50.0",
                    "public": false,
                    "segment": "10.108.50.0"
                  }
                ]
            """
        }
    )
    def list(self, request, *args, **kwargs):
        azone_id = request.query_params.get('azone_id', None)
        if azone_id == '':
            return self.exception_response(
                exceptions.InvalidArgument(message='参数“azone_id”无效'))

        try:
            service = self.get_service(request)
        except exceptions.APIException as exc:
            return Response(exc.err_data(), status=exc.status_code)

        params = inputs.ListNetworkInput(region_id=service.region_id, azone_id=azone_id)
        try:
            r = self.request_service(service, method='list_networks', params=params)
        except exceptions.AuthenticationFailed as exc:
            return Response(data=exc.err_data(), status=500)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        serializer = serializers.NetworkSerializer(r.networks, many=True)
        return Response(data=serializer.data)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询网络信息'),
        manual_parameters=[
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description='服务id'
            ),
        ],
        responses={
            200: """
                  {
                    "id": "9c70cbe2-690c-11eb-a4b7-c8009fe2eb10",
                    "name": "private_10.108.50.0",
                    "public": false,
                    "segment": "10.108.50.0"
                  }
                """
        }
    )
    def retrieve(self, request, *args, **kwargs):
        try:
            service = self.get_service(request)
        except exceptions.APIException as exc:
            return Response(exc.err_data(), status=exc.status_code)

        network_id = kwargs.get(self.lookup_field)

        params = inputs.NetworkDetailInput(network_id=network_id)
        try:
            r = self.request_service(service, method='network_detail', params=params)
        except exceptions.AuthenticationFailed as exc:
            return Response(data=exc.err_data(), status=500)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        serializer = serializers.NetworkSerializer(r.network)
        return Response(data=serializer.data)


class AvailabilityZoneViewSet(CustomGenericViewSet):
    permission_classes = [IsAuthenticated, ]
    pagination_class = None
    lookup_field = 'id'

    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举服务的可用区'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description='服务端点id'
            )
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        统计已发放的待使用的用户资源配额

            http code 200：
            {
              "zones": [
                {
                  "id": "nova",
                  "name": "nova",
                  "available": true # true: 可用；false: 不可用
                }
              ]
            }
        """
        try:
            service = self.get_service(request)
        except exceptions.APIException as exc:
            return Response(exc.err_data(), status=exc.status_code)

        params = inputs.ListAzoneInput(region_id=service.region_id)
        try:
            r = self.request_service(service, method='list_availability_zones', params=params)
        except exceptions.AuthenticationFailed as exc:
            return Response(data=exc.err_data(), status=500)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        serializer = serializers.AvailabilityZoneSerializer(r.zones, many=True)
        return Response(data={'zones': serializer.data})

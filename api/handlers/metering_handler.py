import io
import math
from datetime import date

from django.utils.translation import gettext as _
from django.utils import timezone
from django.utils.http import urlquote
from django.http import StreamingHttpResponse
from rest_framework.response import Response

from core import errors
from api.viewsets import CustomGenericViewSet
from api.serializers.serializers import MeteringServerSerializer, MeteringStorageSimpleSerializer
from metering.models import PaymentStatus
from metering.managers import (
    MeteringServerManager, StatementServerManager, MeteringStorageManager, StatementStorageManager
)
from utils.report_file import CSVFileInMemory
from utils import rand_utils
from utils.decimal_utils import quantize_18_2


class MeteringHandler:
    def list_server_metering(self, view: CustomGenericViewSet, request):
        """
        列举云主机计量账单
        """
        try:
            params = self.list_server_metering_validate_params(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        service_id = params['service_id']
        server_id = params['server_id']
        date_start = params['date_start']
        date_end = params['date_end']
        vo_id = params['vo_id']
        user_id = params['user_id']
        download = params['download']

        ms_mgr = MeteringServerManager()
        if view.is_as_admin_request(request):   
            queryset = ms_mgr.filter_server_metering_by_admin(
                user=request.user, service_id=service_id, server_id=server_id, date_start=date_start,
                date_end=date_end, vo_id=vo_id, user_id=user_id
            )
        elif vo_id:     
            queryset = ms_mgr.filter_vo_server_metering(    
                user=request.user, service_id=service_id, server_id=server_id, date_start=date_start,
                date_end=date_end, vo_id=vo_id
            )
        else:           
            queryset = ms_mgr.filter_user_server_metering(
                user=request.user, service_id=service_id, server_id=server_id, date_start=date_start,
                date_end=date_end
            )

        if download:
            return self.list_server_metering_download(
                queryset=queryset, date_start=date_start, date_end=date_end
            )

        try:
            meterings = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=meterings, many=True)
            return view.get_paginated_response(serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def list_server_metering_validate_params(view: CustomGenericViewSet, request) -> dict:
        service_id = request.query_params.get('service_id', None)
        server_id = request.query_params.get('server_id', None)
        date_start = request.query_params.get('date_start', None)
        date_end = request.query_params.get('date_end', None)
        vo_id = request.query_params.get('vo_id', None)
        user_id = request.query_params.get('user_id', None)
        download = request.query_params.get('download', None)

        now_date = timezone.now().date()

        if vo_id is not None and not vo_id:
            raise errors.InvalidArgument(message=_('参数“vo_id”的值无效'))

        if service_id is not None and not service_id:
            raise errors.InvalidArgument(message=_('参数“service_id”的值无效'))

        if server_id is not None and not server_id:
            raise errors.InvalidArgument(message=_('参数“server_id”的值无效'))

        if date_start is not None:
            try:
                date_start = date.fromisoformat(date_start)
            except (TypeError, ValueError):
                raise errors.InvalidArgument(message=_('参数“date_start”的值无效的日期格式'))
        else:   # 默认当月起始时间
            date_start = now_date.replace(day=1)

        if date_end is not None:
            try:
                date_end = date.fromisoformat(date_end)
            except (TypeError, ValueError):
                raise errors.InvalidArgument(message=_('参数“date_end”的值无效的日期格式'))
        else:
            date_end = now_date

        if date_start > date_end:
            raise errors.BadRequest(message=_('参数“date_start”时间必须超前“date_end”时间'))

        # 时间段不得超过一年
        if date_start.replace(year=date_start.year + 1) < date_end:
            raise errors.BadRequest(message=_('起止日期范围不得超过一年'))

        if user_id is not None and not view.is_as_admin_request(request):
            raise errors.BadRequest(message=_('参数“user_id”仅以管理员身份查询时允许使用'))

        if user_id is not None and vo_id is not None:
            raise errors.BadRequest(message=_('参数“user_id”和“vo_id”不能同时提交'))

        return {
            'date_start': date_start,
            'date_end': date_end,
            'vo_id': vo_id,
            'service_id': service_id,
            'server_id': server_id,
            'user_id': user_id,
            'download': download is not None
        }

    def list_server_metering_download(self, queryset, date_start, date_end):
        count = queryset.count()
        if count > 100000:
            exc = errors.ConflictError(message=_('数据量太多'), code='TooManyData')
            return Response(data=exc.err_data(), status=exc.status_code)

        filename = rand_utils.timestamp14_sn()
        csv_file = CSVFileInMemory(filename=filename)
        csv_file.writerow(['#' + _('列举云服务器计量计费明细') + f'[{date_start} - {date_end}]'])
        csv_file.writerow(['#--------------' + _('数据明细列表') + '---------------'])
        csv_file.writerow([
            _('云服务器ID'), _('计费日期'), _('所有者类型'), _('用户名'), _('VO组名'),
            _('CPU (核*小时)'), _('内存 (Gb*小时数)'), _('系统盘 (Gb*小时)'), _('公网IP (个*小时)'),
            _('计费总金额'), _('应付总金额')
        ])
        per_page = 1000
        is_end_page = False
        for number in range(1, math.ceil(count / per_page) + 1):
            bottom = (number - 1) * per_page
            top = bottom + per_page
            if top >= count:
                top = count
                is_end_page = True

            meterings = queryset[bottom:top]
            rows = []
            for m in meterings:
                line_items = [
                    str(m.server_id), str(m.date), m.get_owner_type_display(), str(m.username),
                    str(m.vo_name), str(m.cpu_hours), str(m.ram_hours), str(m.disk_hours),
                    str(m.public_ip_hours), str(quantize_18_2(m.original_amount)),
                    str(quantize_18_2(m.trade_amount))
                ]
                rows.append(line_items)

            csv_file.writerows(rows)
            if is_end_page:
                break

        csv_file.writerow(['#--------------' + _('数据明细列表结束') + '---------------'])
        csv_file.writerow(['#' + _('数据总数') + f': {count}'])
        csv_file.writerow(['#' + _('下载时间') + f': {timezone.now()}'])

        filename = csv_file.filename
        data = csv_file.to_bytes()
        csv_file.close()
        return self._wrap_csv_file_response(filename=filename, data=data)

    def list_aggregation_by_server(self, view: CustomGenericViewSet, request):
        """
        列举云主机计量计费聚合信息
        """
        try:
            params = self.list_aggregation_by_server_validate_params(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        date_start = params['date_start']
        date_end = params['date_end']
        user_id = params['user_id']
        service_id = params['service_id']
        vo_id = params['vo_id']
        download = params['download']

        ms_mgr = MeteringServerManager()
        if view.is_as_admin_request(request):       
            queryset = ms_mgr.aggregate_server_metering_by_uuid_by_admin(
                user=request.user, date_start=date_start, date_end=date_end, user_id=user_id,
                service_id=service_id, vo_id=vo_id
            )
        elif vo_id:     
            queryset = ms_mgr.aggregate_server_metering_by_uuid_by_vo(
                user=request.user, service_id=service_id, date_start=date_start,
                date_end=date_end, vo_id=vo_id
            )
        else:         
            queryset = ms_mgr.aggregate_server_metering_by_uuid_by_user(
                user=request.user, date_start=date_start, date_end=date_end, service_id=service_id
            )

        if download:
            return self.list_aggregation_by_server_download(
                queryset=queryset, date_start=date_start, date_end=date_end
            )

        try:
            data = view.paginate_queryset(queryset)
            data = ms_mgr.aggregate_by_server_mixin_data(data)
            return view.get_paginated_response(data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def list_aggregation_by_server_validate_params(view: CustomGenericViewSet, request) -> dict:    
        date_start = request.query_params.get('date_start', None)
        date_end = request.query_params.get('date_end', None)
        user_id = request.query_params.get('user_id', None)
        service_id = request.query_params.get('service_id', None)
        vo_id = request.query_params.get('vo_id', None)
        download = request.query_params.get('download', None)

        now_date = timezone.now().date()

        if vo_id is not None and not vo_id:
            raise errors.InvalidArgument(message=_('参数“vo_id”的值无效'))

        if date_start is not None:
            try:
                date_start = date.fromisoformat(date_start)
            except (TypeError, ValueError):
                raise errors.InvalidArgument(message=_('参数“date_start”的值无效的日期格式'))
        else:                       # 默认当月起始时间
            date_start = now_date.replace(day=1)

        if date_end is not None:
            try:
                date_end = date.fromisoformat(date_end)
            except (TypeError, ValueError):
                raise errors.InvalidArgument(message=_('参数“date_end”的值无效的日期格式'))
        else:
            date_end = now_date     # 默认当月当前日期

        if user_id is not None and not view.is_as_admin_request(request):
            raise errors.BadRequest(message=_('参数“user_id”仅以管理员身份查询时允许使用'))

        if service_id is not None and not service_id:
            raise errors.InvalidArgument(message=_('参数“service_id”的值无效'))

        if user_id is not None and vo_id is not None:
            raise errors.BadRequest(message=_('参数“user_id”和“vo_id”不能同时提交'))

        return {
            'date_start': date_start,
            'date_end':  date_end,
            'user_id': user_id,
            'service_id': service_id,
            'vo_id': vo_id,
            'download': download is not None
        }

    def list_aggregation_by_server_download(self, queryset, date_start, date_end):
        count = queryset.count()
        if count > 100000:
            exc = errors.ConflictError(message=_('数据量太多'), code='TooManyData')
            return Response(data=exc.err_data(), status=exc.status_code)

        filename = rand_utils.timestamp14_sn()
        csv_file = CSVFileInMemory(filename=filename)
        csv_file.writerow(['#' + _('按云主机列举计量计费聚合统计') + f'[{date_start} - {date_end}]'])
        csv_file.writerow(['#--------------' + _('数据明细列表') + '---------------'])
        csv_file.writerow([
            _('云主机id'), 'IPv4', 'RAM (Mb)', 'CPU', _('服务'), _('CPU (核*小时)'), _('内存 (Gb*小时数)'),
            _('系统盘 (Gb*小时)'), _('公网IP (个*小时)'), _('计费总金额'), _('实际扣费金额')
        ])
        per_page = 100
        is_end_page = False
        for number in range(1, math.ceil(count / per_page) + 1):
            bottom = (number - 1) * per_page
            top = bottom + per_page
            if top >= count:
                top = count
                is_end_page = True

            data = list(queryset[bottom:top])
            data = MeteringServerManager.aggregate_by_server_mixin_data(data)
            rows = []
            for item in data:
                s = item['server']
                line_items = [
                    str(item['server_id']), str(s['ipv4']), str(s['ram']), str(s['vcpus']), str(item['service_name']),
                    str(item['total_cpu_hours']), str(item['total_ram_hours']), str(item['total_disk_hours']),
                    str(item['total_public_ip_hours']),
                    str(quantize_18_2(item['total_original_amount'])),
                    str(quantize_18_2(item['total_trade_amount']))
                ]
                rows.append(line_items)

            csv_file.writerows(rows)
            if is_end_page:
                break

        csv_file.writerow(['#--------------' + _('数据明细列表结束') + '---------------'])
        csv_file.writerow(['#' + _('数据总数') + f': {count}'])
        csv_file.writerow(['#' + _('下载时间') + f': {timezone.now()}'])

        filename = csv_file.filename
        data = csv_file.to_bytes()
        csv_file.close()
        return self._wrap_csv_file_response(filename=filename, data=data)

    @staticmethod
    def _wrap_csv_file_response(filename: str, data):
        """
        :param data: bytes, BytesIO， StringIO
        """
        if isinstance(data, bytes):
            content_type = 'application/octet-stream'
            content_length = len(data)
            data = io.BytesIO(data)
        elif isinstance(data, io.StringIO):
            content_type = 'text/csv'
            content_length = None
            data.seek(0)
        else:
            content_type = 'application/octet-stream'
            content_length = data.seek(0, io.SEEK_END)
            data.seek(0)

        filename = urlquote(filename)  # 中文文件名需要
        response = StreamingHttpResponse(data, charset='utf-8', status=200)
        if content_length:
            response['Content-Length'] = content_length           # byte length

        response['Content-Type'] = content_type
        response['Content-Disposition'] = f"attachment;filename*=utf-8''{filename}"  # 注意filename 这个是下载后的名字
        return response
    
    def list_aggregation_by_user(self, view: CustomGenericViewSet, request):
        """
        列举用户的云主机计量计费聚合信息
        """
        try:
            params = self.list_aggregation_by_user_validate_params(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        date_start = params['date_start']
        date_end = params['date_end']
        service_id = params['service_id']
        download = params['download']

        ms_mgr = MeteringServerManager()
        if view.is_as_admin_request(request):           
            queryset = ms_mgr.aggregate_server_metering_by_userid_by_admin(
                user=request.user, date_start=date_start, date_end=date_end, 
                service_id=service_id
            )
        else:
            return view.exception_response(errors.BadRequest(message=_('只允许以管理员身份请求')))

        if download:
            return self.list_aggregation_by_user_download(
                queryset=queryset, date_start=date_start, date_end=date_end
            )

        try:
            data = view.paginate_queryset(queryset)
            data = ms_mgr.aggregate_by_user_mixin_data(data)
            return view.get_paginated_response(data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def list_aggregation_by_user_validate_params(view: CustomGenericViewSet, request) -> dict:  
        date_start = request.query_params.get('date_start', None)
        date_end = request.query_params.get('date_end', None)
        service_id = request.query_params.get('service_id', None)
        download = request.query_params.get('download', None)

        now_date = timezone.now().date()

        if date_start is not None:
            try:
                date_start = date.fromisoformat(date_start)
            except (TypeError, ValueError):
                raise errors.InvalidArgument(message=_('参数“date_start”的值无效的日期格式'))
        else:                       # 默认当月起始时间
            date_start = now_date.replace(day=1)

        if date_end is not None:
            try:
                date_end = date.fromisoformat(date_end)
            except (TypeError, ValueError):
                raise errors.InvalidArgument(message=_('参数“date_end”的值无效的日期格式'))
        else:
            date_end = now_date     # 默认当月当前日期

        if service_id is not None and not service_id:
            raise errors.InvalidArgument(message=_('参数“service_id”的值无效'))

        return {
            'date_start': date_start,
            'date_end':  date_end,
            'service_id': service_id,
            'download': download is not None
        }

    def list_aggregation_by_user_download(self, queryset, date_start, date_end):
        count = queryset.count()
        if count > 100000:
            exc = errors.ConflictError(message=_('数据量太多'), code='TooManyData')
            return Response(data=exc.err_data(), status=exc.status_code)

        filename = rand_utils.timestamp14_sn()
        csv_file = CSVFileInMemory(filename=filename)
        csv_file.writerow(['#' + _('按用户列举计量计费聚合统计') + f'[{date_start} - {date_end}]'])
        csv_file.writerow(['#--------------' + _('数据明细列表') + '---------------'])
        csv_file.writerow([
            _('用户名'), _('单位/公司'), _('云服务器数'), _('计费总金额'), _('实际扣费总金额')
        ])
        per_page = 100
        is_end_page = False
        for number in range(1, math.ceil(count / per_page) + 1):
            bottom = (number - 1) * per_page
            top = bottom + per_page
            if top >= count:
                top = count
                is_end_page = True

            data = list(queryset[bottom:top])
            data = MeteringServerManager.aggregate_by_user_mixin_data(data)
            rows = []
            for item in data:
                u = item['user']
                line_items = [
                    str(u['username']), str(u['company']), str(item['total_server']),
                    str(quantize_18_2(item['total_original_amount'])),
                    str(quantize_18_2(item['total_trade_amount']))
                ]
                rows.append(line_items)

            csv_file.writerows(rows)
            if is_end_page:
                break

        csv_file.writerow(['#--------------' + _('数据明细列表结束') + '---------------'])
        csv_file.writerow(['#' + _('数据总数') + f': {count}'])
        csv_file.writerow(['#' + _('下载时间') + f': {timezone.now()}'])

        filename = csv_file.filename
        data = csv_file.to_bytes()
        csv_file.close()
        return self._wrap_csv_file_response(filename=filename, data=data)

    def list_aggregation_by_vo(self, view: CustomGenericViewSet, request):
        """
        列举vo组的云主机计量计费聚合信息
        """
        try:
            params = self.list_aggregation_by_vo_validate_params(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        date_start = params['date_start']
        date_end = params['date_end']
        service_id = params['service_id']
        download = params['download']

        ms_mgr = MeteringServerManager()
        if view.is_as_admin_request(request):           
            queryset = ms_mgr.aggregate_server_metering_by_void_by_admin(
                user=request.user, date_start=date_start, date_end=date_end, 
                service_id=service_id
            )
        else:
            return view.exception_response(errors.BadRequest(message=_('只允许以管理员身份请求')))

        if download:
            return self.list_aggregation_by_vo_download(
                queryset=queryset, date_start=date_start, date_end=date_end
            )

        try:
            data = view.paginate_queryset(queryset)
            data = ms_mgr.aggregate_by_vo_mixin_data(data)
            return view.get_paginated_response(data)
        except Exception as exc:
            return view.exception_response(exc)
        
    @staticmethod
    def list_aggregation_by_vo_validate_params(view: CustomGenericViewSet, request) -> dict:  
        date_start = request.query_params.get('date_start', None)
        date_end = request.query_params.get('date_end', None)
        service_id = request.query_params.get('service_id', None)
        download = request.query_params.get('download', None)

        now_date = timezone.now().date()

        if date_start is not None:
            try:
                date_start = date.fromisoformat(date_start)
            except (TypeError, ValueError):
                raise errors.InvalidArgument(message=_('参数“date_start”的值无效的日期格式'))
        else:                       # 默认当月起始时间
            date_start = now_date.replace(day=1)

        if date_end is not None:
            try:
                date_end = date.fromisoformat(date_end)
            except (TypeError, ValueError):
                raise errors.InvalidArgument(message=_('参数“date_end”的值无效的日期格式'))
        else:
            date_end = now_date     # 默认当月当前日期

        if service_id is not None and not service_id:
            raise errors.InvalidArgument(message=_('参数“service_id”的值无效'))

        return {
            'date_start': date_start,
            'date_end':  date_end,
            'service_id': service_id,
            'download': download is not None
        }

    def list_aggregation_by_vo_download(self, queryset, date_start, date_end):
        count = queryset.count()
        if count > 100000:
            exc = errors.ConflictError(message=_('数据量太多'), code='TooManyData')
            return Response(data=exc.err_data(), status=exc.status_code)

        filename = rand_utils.timestamp14_sn()
        csv_file = CSVFileInMemory(filename=filename)
        csv_file.writerow(['#' + _('按VO组列举计量计费聚合统计') + f'[{date_start} - {date_end}]'])
        csv_file.writerow(['#--------------' + _('数据明细列表') + '---------------'])
        csv_file.writerow([
            _('VO组名'), _('单位/公司'), _('云服务器数'), _('计费总金额'), _('实际扣费总金额')
        ])
        per_page = 100
        is_end_page = False
        for number in range(1, math.ceil(count / per_page) + 1):
            bottom = (number - 1) * per_page
            top = bottom + per_page
            if top >= count:
                top = count
                is_end_page = True

            data = list(queryset[bottom:top])
            data = MeteringServerManager.aggregate_by_vo_mixin_data(data)
            rows = []
            for item in data:
                v = item['vo']
                line_items = [
                    str(v['name']), str(v['company']), str(item['total_server']),
                    str(quantize_18_2(item['total_original_amount'])),
                    str(quantize_18_2(item['total_trade_amount']))
                ]
                rows.append(line_items)

            csv_file.writerows(rows)
            if is_end_page:
                break

        csv_file.writerow(['#--------------' + _('数据明细列表结束') + '---------------'])
        csv_file.writerow(['#' + _('数据总数') + f': {count}'])
        csv_file.writerow(['#' + _('下载时间') + f': {timezone.now()}'])

        filename = csv_file.filename
        data = csv_file.to_bytes()
        csv_file.close()
        return self._wrap_csv_file_response(filename=filename, data=data)
        
    def list_aggregation_by_service(self, view: CustomGenericViewSet, request):
        """
        列举服务节点的云主机计量计费聚合信息
        """
        try:
            params = self.list_aggregation_by_service_validate_params(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        date_start = params['date_start']
        date_end = params['date_end']
        download = params['download']

        ms_mgr = MeteringServerManager()
        if view.is_as_admin_request(request):         
            queryset = ms_mgr.aggregate_server_metering_by_serviceid_by_admin(
                user=request.user, date_start=date_start, date_end=date_end, 
            )
        else:
            return view.exception_response(errors.BadRequest(message=_('只允许以管理员身份请求')))

        if download:
            return self.list_aggregation_by_service_download(
                queryset=queryset, date_start=date_start, date_end=date_end
            )

        try:
            data = view.paginate_queryset(queryset)
            data = ms_mgr.aggregate_by_service_mixin_data(data)
            return view.get_paginated_response(data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def list_aggregation_by_service_validate_params(view: CustomGenericViewSet, request) -> dict:  
        date_start = request.query_params.get('date_start', None)
        date_end = request.query_params.get('date_end', None)
        download = request.query_params.get('download', None)

        now_date = timezone.now().date()

        if date_start is not None:
            try:
                date_start = date.fromisoformat(date_start)
            except (TypeError, ValueError):
                raise errors.InvalidArgument(message=_('参数“date_start”的值无效的日期格式'))
        else:                       # 默认当月起始时间
            date_start = now_date.replace(day=1)

        if date_end is not None:
            try:
                date_end = date.fromisoformat(date_end)
            except (TypeError, ValueError):
                raise errors.InvalidArgument(message=_('参数“date_end”的值无效的日期格式'))
        else:
            date_end = now_date     # 默认当月当前日期

        return {
            'date_start': date_start,
            'date_end':  date_end,
            'download': download is not None
        }

    def list_aggregation_by_service_download(self, queryset, date_start, date_end):
        count = queryset.count()
        if count > 100000:
            exc = errors.ConflictError(message=_('数据量太多'), code='TooManyData')
            return Response(data=exc.err_data(), status=exc.status_code)

        filename = rand_utils.timestamp14_sn()
        csv_file = CSVFileInMemory(filename=filename)
        csv_file.writerow(['#' + _('按服务列举计量计费聚合统计') + f'[{date_start} - {date_end}]'])
        csv_file.writerow(['#--------------' + _('数据明细列表') + '---------------'])
        csv_file.writerow([
            _('服务名称'), _('云服务器数'), _('计费总金额'), _('实际扣费总金额')
        ])
        per_page = 100
        is_end_page = False
        for number in range(1, math.ceil(count / per_page) + 1):
            bottom = (number - 1) * per_page
            top = bottom + per_page
            if top >= count:
                top = count
                is_end_page = True

            data = list(queryset[bottom:top])
            data = MeteringServerManager.aggregate_by_service_mixin_data(data)
            rows = []
            for item in data:
                s = item['service']
                line_items = [
                    str(s['name']), str(item['total_server']),
                    str(quantize_18_2(item['total_original_amount'])),
                    str(quantize_18_2(item['total_trade_amount']))
                ]
                rows.append(line_items)

            csv_file.writerows(rows)
            if is_end_page:
                break

        csv_file.writerow(['#--------------' + _('数据明细列表结束') + '---------------'])
        csv_file.writerow(['#' + _('数据总数') + f': {count}'])
        csv_file.writerow(['#' + _('下载时间') + f': {timezone.now()}'])

        filename = csv_file.filename
        data = csv_file.to_bytes()
        csv_file.close()
        return self._wrap_csv_file_response(filename=filename, data=data)


class StatementHandler:
    def list_statement_server(self, view: CustomGenericViewSet, request):
        try:
            data = self.list_statement_server_validate_params(request)     
        except errors.Error as exc:
            return view.exception_response(exc)

        user = request.user
        vo_id = data['vo_id']
        if vo_id:       
            try:
                queryset = StatementServerManager().filter_vo_statement_server_queryset(
                    payment_status=data['payment_status'],
                    date_start=data['date_start'],
                    date_end=data['date_end'],
                    user=user,
                    vo_id=vo_id
                )
            except Exception as exc:
                return view.exception_response(exc)
        else:
            queryset = StatementServerManager().filter_statement_server_queryset(
                payment_status=data['payment_status'],
                date_start=data['date_start'],
                date_end=data['date_end'],
                user_id=user.id
            )
        try:
            statements = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=statements, many=True)
            return view.get_paginated_response(serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def list_statement_server_validate_params(request) -> dict:

        payment_status = request.query_params.get('payment_status', None)
        date_start = request.query_params.get('date_start', None)
        date_end = request.query_params.get('date_end', None)
        vo_id = request.query_params.get('vo_id', None)

        if payment_status is not None and payment_status not in PaymentStatus:
            raise errors.InvalidArgument(message=_('参数“payment_status”的值无效'))

        if date_start is not None:
            try:
                date_start = date.fromisoformat(date_start)
            except (TypeError, ValueError):
                raise errors.InvalidArgument(message=_('参数“date_start”的值无效的日期格式'))

        if date_end is not None:
            try:
                date_end = date.fromisoformat(date_end)
            except (TypeError, ValueError):
                raise errors.InvalidArgument(message=_('参数“date_end”的值无效的日期格式'))

        if date_start and date_end:
            if date_start > date_end:
                raise errors.InvalidArgument(message=_('参数“date_start”时间必须超前“date_end”时间'))

        if vo_id is not None and not vo_id:
            raise errors.InvalidArgument(message=_('参数“vo_id”的值无效'))

        return {
            'payment_status': payment_status,
            'date_start': date_start,
            'date_end': date_end,
            'vo_id': vo_id
        } 

    @staticmethod
    def statement_server_detail(view: CustomGenericViewSet, request, kwargs):
        statement_id: str = kwargs.get(view.lookup_field, '')

        try:
            statement = StatementServerManager().get_statement_server_detail(
                statement_id=statement_id, user=request.user)
        except errors.Error as exc:
            return view.exception_response(exc)

        serializer = view.get_serializer(instance=statement)
        data = serializer.data
        metering_qs = MeteringServerManager.get_meterings_by_statement_id(
            statement_id=statement.id, _date=statement.date)
        meterings = MeteringServerSerializer(instance=metering_qs, many=True).data
        data['meterings'] = meterings
        return Response(data=data)


class MeteringObsHandler:
    def list_bucket_metering(self, view: CustomGenericViewSet, request):
        """
        列举对象存储的计量账单
        """
        try:
            params = self.list_bucket_metering_validate_params(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        service_id = params['service_id']
        bucket_id = params['bucket_id']
        date_start = params['date_start']
        date_end = params['date_end']
        user_id = params['user_id']
        download = params['download']

        ms_mgr = MeteringStorageManager()
        if view.is_as_admin_request(request):
            try:
                queryset = ms_mgr.filter_storage_metering_by_admin(
                    user=request.user, service_id=service_id, bucket_id=bucket_id, date_start=date_start,
                    date_end=date_end, user_id=user_id
                )
            except errors.Error as exc:
                return view.exception_response(exc)
        else:
            queryset = ms_mgr.filter_user_storage_metering(
                user=request.user, service_id=service_id, bucket_id=bucket_id, date_start=date_start,
                date_end=date_end
            )

        if download:
            return self.list_bucket_metering_download(
                queryset=queryset, date_start=date_start, date_end=date_end
            )
        try:
            meterings = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=meterings, many=True)
            return view.get_paginated_response(serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    def list_bucket_metering_download(self, queryset, date_start, date_end):
        count = queryset.count()
        if count > 100000:
            exc = errors.ConflictError(message=_('数据量太多'), code='TooManyData')
            return Response(data=exc.err_data(), status=exc.status_code)

        filename = rand_utils.timestamp14_sn()
        csv_file = CSVFileInMemory(filename=filename)
        csv_file.writerow(['#' + _('列对象存储计量计费明细') + f'[{date_start} - {date_end}]'])
        csv_file.writerow(['#--------------' + _('数据明细列表') + '---------------'])
        csv_file.writerow([
            _('存储桶ID'), _('计费日期'), _('用户名'),
            _('存储容量 (GiB*Hours)'),
            _('计费总金额'), _('应付总金额')
        ])
        per_page = 1000
        is_end_page = False
        for number in range(1, math.ceil(count / per_page) + 1):
            bottom = (number - 1) * per_page
            top = bottom + per_page
            if top >= count:
                top = count
                is_end_page = True

            meterings = queryset[bottom:top]
            rows = []
            for m in meterings:
                line_items = [
                    str(m.storage_bucket_id), str(m.date), str(m.username),
                    str(f'{m.storage: .2f}'),
                    str(quantize_18_2(m.original_amount)),
                    str(quantize_18_2(m.trade_amount))
                ]
                rows.append(line_items)

            csv_file.writerows(rows)
            if is_end_page:
                break

        csv_file.writerow(['#--------------' + _('数据明细列表结束') + '---------------'])
        csv_file.writerow(['#' + _('数据总数') + f': {count}'])
        csv_file.writerow(['#' + _('下载时间') + f': {timezone.now()}'])

        filename = csv_file.filename
        data = csv_file.to_bytes()
        csv_file.close()
        return self._wrap_csv_file_response(filename=filename, data=data)

    @staticmethod
    def _wrap_csv_file_response(filename: str, data):
        """
        :param data: bytes, BytesIO， StringIO
        """
        if isinstance(data, bytes):
            content_type = 'application/octet-stream'
            content_length = len(data)
            data = io.BytesIO(data)
        elif isinstance(data, io.StringIO):
            content_type = 'text/csv'
            content_length = None
            data.seek(0)
        else:
            content_type = 'application/octet-stream'
            content_length = data.seek(0, io.SEEK_END)
            data.seek(0)

        filename = urlquote(filename)  # 中文文件名需要
        response = StreamingHttpResponse(data, charset='utf-8', status=200)
        if content_length:
            response['Content-Length'] = content_length  # byte length

        response['Content-Type'] = content_type
        response['Content-Disposition'] = f"attachment;filename*=utf-8''{filename}"  # 注意filename 这个是下载后的名字
        return response

    @staticmethod
    def list_bucket_metering_validate_params(view: CustomGenericViewSet, request) -> dict:
        service_id = request.query_params.get('service_id', None)
        bucket_id = request.query_params.get('bucket_id', None)
        date_start = request.query_params.get('date_start', None)
        date_end = request.query_params.get('date_end', None)
        user_id = request.query_params.get('user_id', None)
        download = request.query_params.get('download', None)

        now_date = timezone.now().date()

        if service_id is not None and not service_id:
            raise errors.InvalidArgument(message='参数“service_id"的值无效')

        if bucket_id is not None and not bucket_id:
            raise errors.InvalidArgument(message='参数bucket_id"的值无效')

        if date_start is not None:
            try:
                date_start = date.fromisoformat(date_start)
            except (TypeError, ValueError):
                raise errors.InvalidArgument(message='参数"date_start"的值无效')
        else:
            # 默认是当月的起始时间
            date_start = now_date.replace(day=1)

        if date_end is not None:
            try:
                date_end = date.fromisoformat(date_end)
            except (TypeError, ValueError):
                raise errors.InvalidArgument(message='参数"date_end"的值无效')
        else:
            # 默认是当月的起始时间
            date_end = now_date

        if date_start > date_end:
            raise errors.BadRequest(message='参数“date_start”时间必须超前“date_end”时间')

        # 时间段不得超过一年
        if date_start.replace(year=date_start.year + 1) < date_end:
            raise errors.BadRequest(message='起止时间不得超过一年')

        if user_id is not None and not view.is_as_admin_request(request):
            raise errors.BadRequest(message='参数"user_id"只有管理员身份才能允许查询')

        return {
            'date_start': date_start,
            'date_end': date_end,
            'service_id': service_id,
            'bucket_id': bucket_id,
            'user_id': user_id,
            'download': download is not None
        }


class StorageStatementHandler:
    def list_statement_storage(self, view: CustomGenericViewSet, request):
        try:
            data = self.list_statement_storage_validate_params(request)
        except errors.Error as exc:
            return view.exception_response(exc)

        user = request.user

        queryset = StatementStorageManager().filter_statement_storage_queryset(
            payment_status=data['payment_status'],
            date_start=data['date_start'],
            date_end=data['date_end'],
            user_id=user.id
        )

        try:
            statements = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=statements, many=True)
            return view.get_paginated_response(serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def list_statement_storage_validate_params(request) -> dict:

        payment_status = request.query_params.get('payment_status', None)
        date_start = request.query_params.get('date_start', None)
        date_end = request.query_params.get('date_end', None)

        if payment_status is not None and payment_status not in PaymentStatus.values:
            raise errors.InvalidArgument(message='参数"payment_status" 值无效')

        if date_start is not None:
            try:
                date_start = date.fromisoformat(date_start)
            except (TypeError, ValueError):
                raise errors.InvalidArgument(message='参数"date_start" 是无效的日期格式')

        if date_end is not None:
            try:
                date_end = date.fromisoformat(date_end)
            except (TypeError, ValueError):
                raise errors.InvalidArgument(message='参数"date_end" 是无效的日期格式')

        if date_start and date_end:
            if date_start > date_end:
                raise errors.InvalidArgument(message='参数"date_start" 必须提前于 "date_end"时间')

        return {
            'payment_status': payment_status,
            'date_start': date_start,
            'date_end': date_end
        }

    @staticmethod
    def statement_storage_detail(view: CustomGenericViewSet, request, kwargs):
        statement_id: str = kwargs.get(view.lookup_field, '')
        try:
            statement = StatementStorageManager().get_statement_storage_detail(
                statement_id=statement_id, user=request.user)
        except errors.Error as exc:
            return view.exception_response(exc)

        serializer = view.get_serializer(instance=statement)
        data = serializer.data
        metering_qs = MeteringStorageManager.get_meterings_by_statement_id(
            statement_id=statement.id, _date=statement.date)
        meterings = MeteringStorageSimpleSerializer(instance=metering_qs, many=True).data
        data['meterings'] = meterings
        return Response(data=data)

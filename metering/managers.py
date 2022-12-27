from datetime import date

from django.utils.translation import gettext as _
from django.db.models import Subquery, Sum, Count

from core import errors
from service.managers import ServiceManager
from servers.managers import ServerManager
from servers.models import Server, ServerArchive
from metering.models import DailyStatementServer, DailyStatementObjectStorage
from vo.managers import VoManager
from utils.model import OwnerType
from .models import MeteringServer, MeteringObjectStorage
from users.models import UserProfile
from vo.models import VirtualOrganization
from service.models import ServiceConfig


class MeteringServerManager:
    @staticmethod
    def get_metering_server_queryset():
        return MeteringServer.objects.all()

    @staticmethod
    def get_metering_by_id(metering_id: str) -> MeteringServer:
        return MeteringServer.objects.filter(id=metering_id).first()

    @staticmethod
    def get_metering(metering_id: str, user):
        """
        查询一个计量单，检查权限

        :raises: Error
        """
        metering = MeteringServerManager.get_metering_by_id(metering_id=metering_id)
        if metering is None:
            raise errors.NotFound(message=_('计量单不存在。'))

        if metering.owner_type == metering.OwnerType.USER.value:
            if metering.user_id != user.id:
                raise errors.AccessDenied(message=_('无计量单的访问权限。'))
        elif metering.owner_type == metering.OwnerType.VO.value:
            VoManager().get_has_read_perm_vo(vo_id=metering.vo_id, user=user)

        return metering

    def filter_user_server_metering(
            self, user,
            service_id: str = None,
            server_id: str = None,
            date_start: date = None,
            date_end: date = None
    ):
        """
        查询用户云主机计量用量账单查询集
        """
        return self.filter_server_metering_queryset(
            service_id=service_id, server_id=server_id, date_start=date_start,
            date_end=date_end, user_id=user.id
        )

    def filter_vo_server_metering(
            self, user,
            vo_id: str,
            service_id: str = None,
            server_id: str = None,
            date_start: date = None,
            date_end: date = None
    ):
        """
        查询vo组云主机计量用量账单查询集

        :rasies: AccessDenied, NotFound, Error
        """
        VoManager().get_has_read_perm_vo(vo_id=vo_id, user=user)
        return self.filter_server_metering_queryset(
            service_id=service_id, server_id=server_id, date_start=date_start,
            date_end=date_end, vo_id=vo_id
        )

    def filter_server_metering_by_admin(    
            self, user,
            service_id: str = None,
            server_id: str = None,
            date_start: date = None,
            date_end: date = None,
            vo_id: str = None,
            user_id: str = None
    ):
        """
        查询vo组云主机计量用量账单查询集

        :rasies: AccessDenied, NotFound, Error
        """
        if user.is_federal_admin():     
            return self.filter_server_metering_queryset(
                service_id=service_id, server_id=server_id, date_start=date_start, date_end=date_end,
                vo_id=vo_id, user_id=user_id
            )

        if server_id:                    
            server_or_archieve = ServerManager.get_server_or_archive(server_id=server_id) 
            
            if server_or_archieve is None:         
                return MeteringServer.objects.none()
            
            if service_id:      
                if service_id != server_or_archieve.service_id:
                    return MeteringServer.objects.none()
            else:              
                service_id = server_or_archieve.service_id

        if service_id:      
            service = ServiceManager.get_service_if_admin(user=user, service_id=service_id)
            if service is None:
                raise errors.AccessDenied(message=_('您没有指定服务的访问权限'))

        queryset = self.filter_server_metering_queryset(
                service_id=service_id, server_id=server_id, date_start=date_start, date_end=date_end,
                vo_id=vo_id, user_id=user_id
            )

        if not service_id and not server_id:
            qs = ServiceManager.get_all_has_perm_service(user)
            subq = Subquery(qs.values_list('id', flat=True))
            queryset = queryset.filter(service_id__in=subq)

        return queryset

    def filter_server_metering_queryset(       
            self, service_id: str = None,
            server_id: str = None,
            date_start: date = None,
            date_end: date = None,
            user_id: str = None,
            vo_id: str = None
    ):
        """
        查询云主机计量用量账单查询集
        """
        if user_id and vo_id:
            raise errors.Error(_('云主机计量用量账单查询集查询条件不能同时包含"user_id"和"vo_id"'))

        lookups = {}
        if date_start:
            lookups['date__gte'] = date_start

        if date_end:
            lookups['date__lte'] = date_end

        if service_id:
            lookups['service_id'] = service_id

        if server_id:
            lookups['server_id'] = server_id

        if user_id:
            lookups['owner_type'] = OwnerType.USER.value
            lookups['user_id'] = user_id

        if vo_id:
            lookups['owner_type'] = OwnerType.VO.value
            lookups['vo_id'] = vo_id

        queryset = self.get_metering_server_queryset()      
        return queryset.filter(**lookups).order_by('-creation_time')    

    def aggregate_server_metering_by_uuid_by_admin(
            self, user,
            date_start: date = None,
            date_end: date = None,
            user_id: str = None,
            service_id: str = None,
            vo_id: str = None
    ):
        """
            管理员获取以server_id聚合的查询集
        """
        if user.is_federal_admin():
            queryset = self.filter_server_metering_queryset(
                service_id=service_id, date_start=date_start, date_end=date_end, user_id=user_id, vo_id=vo_id
            )
            return self.aggregate_queryset_by_server(queryset)

        if service_id:
            service = ServiceManager.get_service_if_admin(user=user, service_id=service_id)
            if service is None:
                raise errors.AccessDenied(message=_('您没有指定服务的访问权限'))

        queryset = self.filter_server_metering_queryset(
            service_id=service_id, date_start=date_start, date_end=date_end, user_id=user_id, vo_id=vo_id
        )

        if not service_id:
            qs = ServiceManager.get_all_has_perm_service(user)  
            subq = Subquery(qs.values_list('id', flat=True))   
            queryset = queryset.filter(service_id__in=subq)

        return self.aggregate_queryset_by_server(queryset)

    def aggregate_server_metering_by_uuid_by_user(
            self, user,
            date_start: date = None,
            date_end: date = None,
            service_id: str = None
    ):
        """
        普通用户获取自己名下以server_id聚合的查询集
        """
        queryset = self.filter_server_metering_queryset(
            service_id=service_id, date_start=date_start,
            date_end=date_end, user_id=user.id
        )
        return self.aggregate_queryset_by_server(queryset)

    def aggregate_server_metering_by_uuid_by_vo(
            self, user,
            date_start: date = None,
            date_end: date = None,
            service_id: str = None,
            vo_id: str = None
    ):
        """
        指定vo组下以server_id聚合的查询集
        """
        VoManager().get_has_read_perm_vo(vo_id=vo_id, user=user)
        queryset = self.filter_server_metering_queryset(
            service_id=service_id, date_start=date_start,
            date_end=date_end, vo_id=vo_id
        )
        return self.aggregate_queryset_by_server(queryset)

    @staticmethod
    def aggregate_queryset_by_server(queryset):
        """
        聚合云主机计量数据
        """
        queryset = queryset.values('server_id').annotate(   
            total_cpu_hours=Sum('cpu_hours'),
            total_ram_hours=Sum('ram_hours'),
            total_disk_hours=Sum('disk_hours'),
            total_public_ip_hours=Sum('public_ip_hours'),
            total_original_amount=Sum('original_amount'),
            total_trade_amount=Sum('trade_amount')
        ).order_by('server_id')

        return queryset

    @staticmethod
    def aggregate_by_server_mixin_data(data: list):
        """
        按server id聚合数据分页后混合其他数据
        """
        server_ids = [i['server_id'] for i in data]
        servers = Server.objects.filter(id__in=server_ids).values('id', 'ipv4', 'ram', 'vcpus', 'service__name')
        archives = ServerArchive.objects.filter(
            server_id__in=server_ids, archive_type=ServerArchive.ArchiveType.ARCHIVE.value
        ).values('server_id', 'ipv4', 'ram', 'vcpus', 'service__name')

        server_dict = {}
        for s in servers:
            d = {
                'service_name': s.pop('service__name', None),
                'server': s
            }
            server_dict[s['id']] = d

        for a in archives:
            server_id = a['id'] = a.pop('server_id', None)
            if server_id and server_id not in server_dict:
                d = {
                    'service_name': a.pop('service__name', None),
                    'server': a
                }
                server_dict[server_id] = d

        for i in data:
            i: dict
            sid = i['server_id']
            if sid in server_dict:
                i.update(server_dict[sid])
            else:
                i['service_name'] = None
                i['server'] = None

        return data

    def aggregate_server_metering_by_userid_by_admin(
            self, user,
            date_start: date = None,
            date_end: date = None,
            service_id: str = None,
    ):
        """
            管理员获取以user_id聚合的查询集
        """
        queryset = self.filter_server_metering_queryset(   
            date_start=date_start, date_end=date_end, service_id=service_id
        ).filter(owner_type=OwnerType.USER.value)             
               
        if user.is_federal_admin():     
            return self.aggregate_queryset_by_user(queryset)    
        
        if service_id:     
            service = ServiceManager.get_service_if_admin(user=user, service_id=service_id)
            if service is None:
                raise errors.AccessDenied(message=_('您没有指定服务的访问权限'))
        else:               
            qs = ServiceManager.get_all_has_perm_service(user)  
            subq = Subquery(qs.values_list('id', flat=True))   
            queryset = queryset.filter(service_id__in=subq)

        return self.aggregate_queryset_by_user(queryset)

    @staticmethod
    def aggregate_queryset_by_user(queryset):
        """
        聚合用户的云主机计量数据
        """
        queryset = queryset.values('user_id').annotate(
            total_original_amount=Sum('original_amount'),
            total_trade_amount=Sum('trade_amount'),
            total_server=Count('server_id', distinct=True),
        ).order_by('user_id')

        return queryset

    @staticmethod
    def aggregate_by_user_mixin_data(data: list):
        """
        按user id聚合数据分页后混合其他数据
        """
        user_ids = [i['user_id'] for i in data]     
        users = UserProfile.objects.filter(id__in=user_ids).values('id', 'username', 'company')

        user_dict = {}
        for user in users:
            user_id = user['id']
            u = {
                'user': user
            }
            user_dict[user_id] = u

        for i in data:
            i: dict
            i.update(user_dict[i['user_id']])

        return data

    def aggregate_server_metering_by_void_by_admin(
            self, user,
            date_start: date = None,
            date_end: date = None,
            service_id: str = None,
    ):
        """
            管理员获取以vo_id聚合的查询集
        """
        queryset = self.filter_server_metering_queryset(   
            date_start=date_start, date_end=date_end, service_id=service_id
        ).filter(owner_type=OwnerType.VO.value)              
        
        if user.is_federal_admin():     
            return self.aggregate_queryset_by_vo(queryset)   
        
        if service_id:      
            service = ServiceManager.get_service_if_admin(user=user, service_id=service_id)
            if service is None:
                raise errors.AccessDenied(message=_('您没有指定服务的访问权限'))
        else:       
            qs = ServiceManager.get_all_has_perm_service(user)  
            subq = Subquery(qs.values_list('id', flat=True))   
            queryset = queryset.filter(service_id__in=subq)

        return self.aggregate_queryset_by_vo(queryset)

    @staticmethod
    def aggregate_queryset_by_vo(queryset):
        """
        聚合vo组的云主机计量数据
        """
        queryset = queryset.values('vo_id').annotate(
            total_original_amount=Sum('original_amount'),
            total_trade_amount=Sum('trade_amount'),
            total_server=Count('server_id', distinct=True),
        ).order_by('vo_id')

        return queryset

    @staticmethod
    def aggregate_by_vo_mixin_data(data: list):
        """
        按vo id聚合数据分页后混合其他数据
        """
        vo_ids = [i['vo_id'] for i in data]    
        vos = VirtualOrganization.objects.filter(id__in=vo_ids).values('id', 'name', 'company')

        vo_dict = {}
        for vo in vos:
            vo_id = vo['id']
            v = {
                'vo': vo
            }
            vo_dict[vo_id] = v

        for i in data:
            i: dict
            i.update(vo_dict[i['vo_id']])

        return data
    
    def aggregate_server_metering_by_serviceid_by_admin(
            self, user,
            date_start: date = None,
            date_end: date = None,
    ):
        """
            管理员获取以service_id聚合的查询集
        """
        queryset = self.filter_server_metering_queryset(    
            date_start=date_start, date_end=date_end, 
        )      
        
        if user.is_federal_admin():     
            return self.aggregate_queryset_by_service(queryset)    
        
        qs = ServiceManager.get_all_has_perm_service(user)  
        subq = Subquery(qs.values_list('id', flat=True))   
        queryset = queryset.filter(service_id__in=subq)

        return self.aggregate_queryset_by_service(queryset)

    @staticmethod
    def aggregate_queryset_by_service(queryset):
        """
        聚合服务节点的云主机计量数据
        """
        queryset = queryset.values('service_id').annotate(
            total_original_amount=Sum('original_amount'),
            total_trade_amount=Sum('trade_amount'),
            total_server=Count('server_id', distinct=True),
        ).order_by('service_id')

        return queryset

    @staticmethod
    def aggregate_by_service_mixin_data(data: list):
        """
        按service id聚合数据分页后混合其他数据
        """
        service_ids = [i['service_id'] for i in data]    
        services = ServiceConfig.objects.filter(id__in=service_ids).values('id', 'name')

        service_dict = {}
        for service in services:
            service_id = service['id']
            s = {
                'service': service
            }
            service_dict[service_id] = s

        for i in data:
            i: dict
            i.update(service_dict[i['service_id']])

        return data

    @staticmethod
    def get_meterings_by_statement_id(statement_id: str, _date: date):
        queryset = MeteringServerManager.get_metering_server_queryset()
        return queryset.filter(date=_date, daily_statement_id=statement_id)


class StatementServerManager:
    @staticmethod
    def get_statement_server_queryset():
        return DailyStatementServer.objects.all()
    
    def filter_statement_server_queryset(
            self, payment_status: str, date_start, date_end,
            user_id: str = None, vo_id: str = None
    ):
        """
        查询用户或vo组的日结算单查询集
        """
        queryset = self.get_statement_server_queryset()
        if user_id:
            queryset = queryset.filter(user_id=user_id, owner_type=OwnerType.USER.value)

        if vo_id:
            queryset = queryset.filter(vo_id=vo_id, owner_type=OwnerType.VO.value)

        if date_start:
            queryset = queryset.filter(date__gte=date_start)       

        if date_end:
            queryset = queryset.filter(date__lte=date_end)

        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)

        return queryset.order_by('-creation_time')

    def filter_vo_statement_server_queryset(
        self, payment_status: str, date_start, date_end, user, vo_id: str
    ):
        """
        查询vo组的日结算单查询集

        :raises: AccessDenied
        """
        self._has_vo_permission(vo_id=vo_id, user=user)
        return self.filter_statement_server_queryset(
            payment_status=payment_status, date_start=date_start,
            date_end=date_end, vo_id=vo_id
        )

    @staticmethod
    def _has_vo_permission(vo_id, user, read_only: bool = True):
        """
        是否有vo组的权限

        :raises: AccessDenied
        """
        try:
            if read_only:
                VoManager().get_has_read_perm_vo(vo_id=vo_id, user=user)
            else:
                VoManager().get_has_manager_perm_vo(vo_id=vo_id, user=user)
        except errors.Error as exc:
            raise errors.AccessDenied(message=exc.message)

    @staticmethod
    def get_statement_server(statement_id: str, select_for_update: bool = False):
        if select_for_update:
            return DailyStatementServer.objects.filter(
                id=statement_id
            ).select_related('service').select_for_update().first()

        return DailyStatementServer.objects.filter(id=statement_id).select_related('service').first()

    def get_statement_server_detail(
            self, statement_id: str, user, check_permission: bool = True, read_only: bool = True
    ):
        """
        查询日结算单详情

        :param check_permission: 是否检测权限
        :param read_only: 用于vo组权限检测；True：只需要访问权限；False: 需要管理权限
        :return:
            statement_server
        """
        statement = self.get_statement_server(statement_id=statement_id)
        if statement is None:
            raise errors.NotFound(_('日结算单不存在'))

        # check permission
        if check_permission:
            if statement.owner_type == OwnerType.USER.value:
                if statement.user_id and statement.user_id != user.id:
                    raise errors.AccessDenied(message=_('您没有此日结算单访问权限'))
            elif statement.vo_id:
                try:
                    if read_only:
                        VoManager().get_has_read_perm_vo(vo_id=statement.vo_id, user=user)
                    else:
                        VoManager().get_has_manager_perm_vo(vo_id=statement.vo_id, user=user)
                except errors.Error as exc:
                    raise errors.AccessDenied(message=exc.message)

        return statement


class MeteringStorageManager:
    @staticmethod
    def get_metering_obs_queryset():
        return MeteringObjectStorage.objects.select_related('service').all()

    def filter_user_storage_metering(
            self, user,
            service_id: str = None,
            bucket_id: str = None,
            date_start: date = None,
            date_end: date = None
    ):
        """
        查询用户的对象存储的计量账单的查询集合
        """
        return self.filter_obs_metering_queryset(
            service_id=service_id, bucket_id=bucket_id, date_start=date_start,
            date_end=date_end, user_id=user.id
        )

    def filter_storage_metering_by_admin(
            self, user,
            service_id: str = None,
            bucket_id: str = None,
            date_start: date = None,
            date_end: date = None,
            user_id: str = None
    ):
        """
        查询用户的对象存储的计量账单的查询集合
        :return: QuerySet()
        :raises: Error
        """
        if user.is_federal_admin():
            return self.filter_obs_metering_queryset(
                service_id=service_id, bucket_id=bucket_id, date_start=date_start,
                date_end=date_end, user_id=user_id
            )

        raise errors.AccessDenied(message=_('您没有管理员权限'))

    def filter_obs_metering_queryset(
            self, service_id: str = None,
            bucket_id: str = None,
            date_start: date = None,
            date_end: date = None,
            user_id: str = None
    ):
        lookups = {}
        if user_id:
            lookups['user_id'] = user_id

        if service_id:
            lookups['service_id'] = service_id

        if bucket_id:
            lookups['storage_bucket_id'] = bucket_id

        if date_start:
            lookups['date__gte'] = date_start

        if date_end:
            lookups['date__lte'] = date_end

        queryset = self.get_metering_obs_queryset()
        return queryset.filter(**lookups).order_by('-creation_time')

    @staticmethod
    def get_meterings_by_statement_id(statement_id: str, _date: date):
        return MeteringObjectStorage.objects.filter(date=_date, daily_statement_id=statement_id)


class StatementStorageManager:
    @staticmethod
    def get_statement_storage_queryset():
        return DailyStatementObjectStorage.objects.all()

    def filter_statement_storage_queryset(
            self, payment_status: str, date_start, date_end,
            user_id: str = None
    ):
        queryset = self.get_statement_storage_queryset()
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        if date_start:
            queryset = queryset.filter(date__gte=date_start)

        if date_end:
            queryset = queryset.filter(date__lte=date_end)

        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)

        return queryset.order_by('-creation_time')

    @staticmethod
    def get_statement_storage(statement_id: str, select_for_update: bool = False):
        if select_for_update:
            return DailyStatementObjectStorage.objects.filter(
                id=statement_id
            ).select_related('service').select_for_update().first()
        return DailyStatementObjectStorage.objects.filter(id=statement_id).select_related('service').first()

    def get_statement_storage_detail(
            self, statement_id: str, user, check_permission: bool = True
    ):
        statement = self.get_statement_storage(statement_id=statement_id)
        if check_permission:
            if statement.user_id and statement.user_id != user.id:
                raise errors.AccessDenied(message=_('您没有权限访问该结算单'))
        return statement

from datetime import timedelta, date

from django.utils import timezone
from django.db.models import Sum
from django.db import transaction

from metering.models import DailyStatementServer, MeteringServer, PaymentStatus
from servers.models import Server
from utils.model import OwnerType


class GenerateDailyStatementServer:

    def __init__(self, statement_date: date = None, raise_exception: bool = False):
        """
        :param statement_date: 日结算单日期
        :param raise_exception: True(发生错误直接抛出退出)
        """
        if statement_date:
            statement_date = timezone.now().replace(
                year=statement_date.year, month=statement_date.month, day=statement_date.day,
                hour=0, minute=0, second=0, microsecond=0)
        else:
            # 聚合当前时间前一天的计量记录      
            statement_date = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)

        self.statement_date = statement_date.date()
        self.raise_exception = raise_exception
        self._user_daily_statement_count = 0  # 用户日结算单计数
        self._vo_daily_statement_count = 0  # VO组日结算单计数
        self._new_count = 0      # 新产生的日结算单计数

    def run(self, raise_exception: bool = None):
        print(f'generate {self.statement_date} daily statement start: ')
        if self.statement_date >= timezone.now().date():
            print('Exit, date invalid')
            return 
        
        if raise_exception is not None:
            self,raise_exception = raise_exception

        # 用户的日结算单
        self.generate_user_daily_statement()
        # VO组的日结算单
        self.generate_vo_daily_statement()

        print(f'generate {self._user_daily_statement_count} user daily statements,',
              f'generate {self._vo_daily_statement_count} vo daily statements,',
              f'all {self._user_daily_statement_count + self._vo_daily_statement_count}.\n',
              f'new generate {self._new_count} daily statements.')

    def generate_user_daily_statement(self):
        '''
        生成用户的日结算单
        '''
        users = self.get_users()

        for user in users:      # 每个user：按服务单元聚合
            if user['user_id'] == '':
                continue

            # 该用户当天所有的计量记录
            user_meterings = self.get_user_metering_queryset(user['user_id'])
            # 按服务单元聚合
            agg_meterings = self.aggregate_metering_server(user_meterings)  
            for agg_metering in agg_meterings:
                self.save_user_daily_statement_record(user=user, agg_metering=agg_metering, user_meterings=user_meterings)
                
    def generate_vo_daily_statement(self):    
        '''
        生成vo组的日结算单
        '''
        vos = self.get_vos()

        for vo in vos:      # 每个vo：按服务单元聚合
            if vo['vo_id'] == '':
                continue

            # 该vo组当天所有的计量记录
            vo_meterings = self.get_vo_metering_queryset(vo['vo_id'])
            # 按服务单元聚合
            agg_meterings = self.aggregate_metering_server(vo_meterings)  
            for agg_metering in agg_meterings:
                self.save_vo_daily_statement_record(vo=vo, agg_metering=agg_metering, vo_meterings=vo_meterings)

    def get_metering_queryset(self):
        '''
        获取statement_date当天所有后付费metering_server记录
        '''
        lookups = {
            'date': self.statement_date,
            'pay_type': Server.PayType.POSTPAID
        }

        return MeteringServer.objects.filter(**lookups)

    def get_vos(self):
        '''
        获得所有vo组
        '''
        queryset = self.get_metering_queryset()
        return queryset.values('vo_id', 'vo_name').order_by('vo_id').distinct()

    def get_users(self):
        '''
        获得所有用户
        '''
        queryset = self.get_metering_queryset()
        return queryset.values('user_id', 'username').order_by('user_id').distinct()
        
    def get_vo_metering_queryset(self, vo_id):
        '''
        获得某个vo组的计量记录
        '''
        queryset = self.get_metering_queryset()
        return queryset.filter(vo_id=vo_id)

    def get_user_metering_queryset(self, user_id):
        '''
        获得某个用户的计量记录
        '''
        queryset = self.get_metering_queryset()
        return queryset.filter(user_id=user_id)
    
    def aggregate_metering_server(self, queryset):
        '''
        按服务单元聚合        
        '''
        queryset = queryset.values('service_id').annotate(
            st_original_amount=Sum('original_amount'),
            payable_amount=Sum('trade_amount')
        ).order_by('service_id')
        
        return queryset
    
    def save_user_daily_statement_record(self, user, agg_metering, user_meterings):
        st_date = self.statement_date
        # 插入新的日结算单前先判断是否已经存在
        daily_statement = self.daily_statement_exists(statement_date=st_date, service_id=agg_metering['service_id'], user_id=user['user_id'])
        # 已存在
        if daily_statement is not None:
            # 金额不一致：更新
            if agg_metering['st_original_amount'] != daily_statement.original_amount or agg_metering['payable_amount'] != daily_statement.payable_amount:
                self.update_metering_server_amount(agg_metering=agg_metering, daily_statement=daily_statement)
            self._user_daily_statement_count += 1
            
            return daily_statement
        
        # 不存在
        with transaction.atomic():
            # 插入新的日结算单记录
            daily_statement = self.save_daily_statement_record(
                service_id=agg_metering['service_id'], original_amount=agg_metering['st_original_amount'],
                payable_amount=agg_metering['payable_amount'],
                user_id=user['user_id'], username=user['username'],
            )
            self._user_daily_statement_count += 1
            # 更新计量记录metering_server的daily_statement_id字段
            self.update_metering_server(meterings=user_meterings, daily_statement=daily_statement)

        return daily_statement

    def save_vo_daily_statement_record(self, vo, agg_metering, vo_meterings):
        st_date = self.statement_date
        # 插入新的日结算单前先判断是否已经存在
        daily_statement = self.daily_statement_exists(statement_date=st_date, service_id=agg_metering['service_id'], vo_id=vo['vo_id'])
        # 已存在
        if daily_statement is not None:
            # 金额不一致：更新
            if agg_metering['st_original_amount'] != daily_statement.original_amount or agg_metering['payable_amount'] != daily_statement.payable_amount:
                self.update_metering_server_amount(agg_metering=agg_metering, daily_statement=daily_statement)
            self._vo_daily_statement_count += 1
            
            return daily_statement
        
        # 不存在
        with transaction.atomic():
            # 插入新的日结算单记录
            daily_statement = self.save_daily_statement_record(
                service_id=agg_metering['service_id'], original_amount=agg_metering['st_original_amount'],
                payable_amount=agg_metering['payable_amount'],
                vo_id=vo['vo_id'], vo_name=vo['vo_name'],
            )
            self._vo_daily_statement_count += 1
            # 更新计量记录metering_server的daily_statement_id字段
            self.update_metering_server(meterings=vo_meterings, daily_statement=daily_statement)

        return daily_statement  

    def save_daily_statement_record(
        self, service_id, original_amount, payable_amount,
        user_id: str = None, username: str = None,
        vo_id: str = None, vo_name: str = None,
    ):
        """
        创建日结算单记录
        """  
        st_date = self.statement_date

        daily_statement = DailyStatementServer(
            service_id=service_id,
            date=st_date,
            original_amount=original_amount,
            payable_amount=payable_amount,
            trade_amount=0,
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id=''
        )

        if user_id is not None:
            daily_statement.user_id = user_id
            daily_statement.username = username
            daily_statement.owner_type = OwnerType.USER.value
        elif vo_id is not None:
            daily_statement.vo_id = vo_id
            daily_statement.vo_name = vo_name
            daily_statement.owner_type = OwnerType.VO.value

        try:
            daily_statement.save(force_insert=True)
            self._new_count += 1
        except Exception as e:
            _daily_statement = self.daily_statement_exists(statement_date=st_date, service_id = service_id, user_id=user_id, vo_id=vo_id)
            if _daily_statement is None:
                raise e

            daily_statement = _daily_statement

        return daily_statement

    def update_metering_server(self, meterings, daily_statement):
        for metering in meterings:
            if metering.service_id == daily_statement.service_id:
                metering.set_daily_statement_id(daily_statement_id=daily_statement.id)

    def update_metering_server_amount(self, agg_metering, daily_statement):
        daily_statement.original_amount = agg_metering['st_original_amount']
        daily_statement.payable_amount = agg_metering['payable_amount']
        daily_statement.save(update_fields=['original_amount', 'payable_amount'])

    @staticmethod
    def daily_statement_exists(statement_date: date, service_id, user_id: str = None, vo_id: str = None):
        user_daily_statement = None
        vo_daily_statement = None
        
        if user_id is not None:
            user_daily_statement = DailyStatementServer.objects.filter(date=statement_date, user_id=user_id, service_id=service_id).first()
        if vo_id is not None:
            vo_daily_statement = DailyStatementServer.objects.filter(date=statement_date, vo_id=vo_id, service_id=service_id).first()
        
        if user_daily_statement is not None:
            return user_daily_statement
        elif vo_daily_statement is not None:
            return vo_daily_statement
        else:
            return None

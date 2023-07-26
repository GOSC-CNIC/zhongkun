import math

from django.db import models, transaction
from django.db.models import Count, Sum, Q
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from service.models import ServiceConfig
from utils.model import get_encryptor, PayType, UuidModel, OwnerType
from utils import rand_utils
from vo.models import VirtualOrganization
from users.models import UserProfile as User


def short_uuid1_l25():
    return rand_utils.short_uuid1_25()


class ServerBase(models.Model):
    """
    虚拟服务器实例
    """
    TASK_CREATED_OK = 1
    TASK_IN_CREATING = 2
    TASK_CREATE_FAILED = 3
    CHOICES_TASK = (
        (TASK_CREATED_OK, _('创建成功')),
        (TASK_IN_CREATING, _('正在创建中')),
        (TASK_CREATE_FAILED, _('创建失败')),
    )

    QUOTA_PRIVATE = 1
    QUOTA_SHARED = 2
    CHOICES_QUOTA = (
        (QUOTA_PRIVATE, _('私有资源配额')),
        (QUOTA_SHARED, _('共享资源配额'))
    )

    class Classification(models.TextChoices):
        PERSONAL = 'personal', _('个人的')
        VO = 'vo', _('VO组的')

    class Situation(models.TextChoices):
        NORMAL = 'normal', _('正常')
        EXPIRED = 'expired', _('过期停机')
        ARREARAGE = 'arrearage', _('欠费停机')

    id = models.CharField(blank=True, editable=False, max_length=36, primary_key=True, verbose_name='ID')
    name = models.CharField(max_length=255, verbose_name=_('服务器实例名称'))
    instance_id = models.CharField(max_length=128, verbose_name=_('云主机实例ID'), help_text=_('各接入服务中云主机的ID'))
    instance_name = models.CharField(max_length=255, blank=True, default='', verbose_name=_('云主机实例名称'),
                                     help_text=_('各接入服务中云主机的名称'))
    vcpus = models.IntegerField(verbose_name=_('虚拟CPU数'), default=0)
    ram = models.IntegerField(verbose_name=_('内存GiB'), default=0)
    ipv4 = models.CharField(max_length=128, verbose_name='IPV4', default='')
    public_ip = models.BooleanField(default=True, verbose_name=_('公/私网'))
    image = models.CharField(max_length=255, verbose_name=_('镜像系统名称'), default='')
    image_id = models.CharField(max_length=64, verbose_name=_('镜像系统ID'), default='')
    image_desc = models.CharField(max_length=255, verbose_name=_('镜像系统描述'), blank=True, default='')
    default_user = models.CharField(max_length=64, verbose_name=_('默认登录用户名'), default='')
    default_password = models.CharField(max_length=255, blank=True, verbose_name=_('默认登录密码'), default='')
    creation_time = models.DateTimeField(verbose_name=_('创建时间'))
    remarks = models.CharField(max_length=255, blank=True, default='', verbose_name=_('备注'))
    task_status = models.SmallIntegerField(verbose_name=_('创建状态'), choices=CHOICES_TASK, default=TASK_CREATED_OK)
    center_quota = models.SmallIntegerField(verbose_name=_('服务配额'), choices=CHOICES_QUOTA, default=QUOTA_PRIVATE)
    expiration_time = models.DateTimeField(verbose_name=_('过期时间'), null=True, blank=True, default=None)
    classification = models.CharField(verbose_name=_('云主机归属类型'), max_length=16,
                                      choices=Classification.choices, default=Classification.PERSONAL,
                                      help_text=_('标识云主机属于申请者个人的，还是vo组的'))
    start_time = models.DateTimeField(verbose_name=_('计量开始时间'), default=timezone.now,
                                      help_text=_('云主机资源使用量计量开始时间'))
    pay_type = models.CharField(verbose_name=_('计费方式'), max_length=16, choices=PayType.choices,
                                default=PayType.POSTPAID)
    azone_id = models.CharField(verbose_name=_('可用区'), max_length=36, blank=True, default='')
    disk_size = models.IntegerField(verbose_name=_('系统盘GB'), default=0)
    network_id = models.CharField(max_length=64, verbose_name=_('网络ID'), default='')
    situation = models.CharField(
        verbose_name=_('过期欠费管控情况'), max_length=16, choices=Situation.choices, default=Situation.NORMAL.value,
        help_text=_('过期欠费等状态下云主机的停机管控情况')
    )
    situation_time = models.DateTimeField(
        verbose_name=_('管控情况时间'), null=True, blank=True, default=None, help_text=_('过期欠费管控开始时间'))

    class Meta:
        abstract = True

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.id:
            self.id = short_uuid1_l25() + '-i'

        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    def do_delete(self):
        """
        :return: True or False
        """
        try:
            self.delete()
        except Exception as e:
            return False

        return True

    @property
    def ram_mib(self):
        return self.ram * 1024

    @ram_mib.setter
    def ram_mib(self, val: int):
        self.ram = math.ceil(val / 1024)

    @property
    def ram_gib(self):
        return self.ram

    @property
    def is_use_shared_quota(self):
        """是否使用的数据中心共享资源配额"""
        return self.center_quota == self.QUOTA_SHARED

    @property
    def is_use_private_quota(self):
        """是否使用的数据中心私有资源配额"""
        return self.center_quota == self.QUOTA_PRIVATE

    @property
    def raw_default_password(self):
        """
        :return:
            str     # success
            None    # failed, invalid encrypted password
        """
        encryptor = get_encryptor()
        try:
            return encryptor.decrypt(self.default_password)
        except encryptor.InvalidEncrypted as e:
            return None

    @raw_default_password.setter
    def raw_default_password(self, raw_password: str):
        encryptor = get_encryptor()
        self.default_password = encryptor.encrypt(raw_password)

    def belong_to_vo(self):
        return self.classification == self.Classification.VO.value

    def set_situation_normal(self):
        if self.situation == self.Situation.NORMAL.value:
            return True

        self.situation = self.Situation.NORMAL.value
        try:
            self.save(update_fields=['situation'])
        except Exception as e:
            return False

        return True


class Server(ServerBase):
    """
    虚拟服务器实例
    """

    class Lock(models.TextChoices):
        FREE = 'free', _('无锁')
        DELETE = 'lock-delete', _('锁定删除')
        OPERATION = 'lock-operation', _('锁定所有操作，只允许读')

    service = models.ForeignKey(to=ServiceConfig, null=True, on_delete=models.SET_NULL, related_name='server_set',
                                verbose_name=_('接入的服务配置'))
    user = models.ForeignKey(to=User, verbose_name=_('创建者'), on_delete=models.SET_NULL, related_name='user_servers',
                             null=True)
    vo = models.ForeignKey(to=VirtualOrganization, null=True, on_delete=models.SET_NULL, default=None, blank=True,
                           related_name='vo_server_set', verbose_name=_('项目组'))
    lock = models.CharField(verbose_name=_('锁'), max_length=16, choices=Lock.choices, default=Lock.FREE,
                            help_text=_('加锁锁定云主机，防止误操作'))
    email_lasttime = models.DateTimeField(verbose_name=_('上次发送邮件时间'), null=True, blank=True, default=None,
                                          help_text=_('记录上次发邮件的时间，邮件通知用户配额即将到期'))

    class Meta:
        ordering = ['-creation_time']
        verbose_name = _('虚拟服务器')
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'Server({self.id}, {self.ipv4})'

    def user_has_perms(self, user):
        """
        用户是否有访问此宿主机的权限

        :param user: 用户
        :return:
            True    # has
            False   # no
        """
        if not user.id:  # 未认证用户
            return False

        if user.is_superuser:
            return True

        if self.user_id == user.id:
            return True

        return False

    def do_archive(self, archive_user):
        """
        创建归档记录
        :return: True or False
        """
        if not self.id:
            return False

        try:
            with transaction.atomic():
                a = ServerArchive.init_archive_from_server(
                    server=self, archive_user=archive_user,
                    archive_type=ServerArchive.ArchiveType.ARCHIVE, commit=True
                )
                self.delete()
        except Exception as e:
            return False

        return True

    @staticmethod
    def count_private_quota_used(service):
        """
        接入服务的私有资源配额已用统计

        :param service: 接入服务配置对象
        :return:
            {
                'vcpu_used_count': 1,
                'ram_used_count': 80,
                'public_ip_count': 0,
                'private_ip_count': 1
            }
        """
        if not isinstance(service, models.Model):
            service_id = service
        else:
            service_id = service.id

        stat = Server.objects.filter(service=service_id, center_quota=Server.QUOTA_PRIVATE).aggregate(
            vcpu_used_count=Sum('vcpus'), ram_used_count=Sum('ram'),
            public_ip_count=Count('id', filter=Q(public_ip=True)),
            private_ip_count=Count('id', filter=Q(public_ip=False))
        )
        if stat.get('vcpu_used_count', 0) is None:
            stat['vcpu_used_count'] = 0

        if stat.get('ram_used_count', 0) is None:
            stat['ram_used_count'] = 0

        return stat

    @staticmethod
    def count_share_quota_used(service):
        """
        接入服务的分享资源配额已用统计

        :param service: 接入服务配置对象
        :return:
            {
                'vcpu_used_count': 1,
                'ram_used_count': 80,
                'public_ip_count': 0,
                'private_ip_count': 1
            }
        """
        if not isinstance(service, models.Model):
            service_id = service
        else:
            service_id = service.id

        stat = Server.objects.filter(service=service_id, center_quota=Server.QUOTA_SHARED).aggregate(
            vcpu_used_count=Sum('vcpus'), ram_used_count=Sum('ram'),
            public_ip_count=Count('id', filter=Q(public_ip=True)),
            private_ip_count=Count('id', filter=Q(public_ip=False))
        )
        if stat.get('vcpu_used_count', 0) is None:
            stat['vcpu_used_count'] = 0

        if stat.get('ram_used_count', 0) is None:
            stat['ram_used_count'] = 0

        return stat

    def is_locked_operation(self):
        """
        是否加锁, 锁定了一切操作
        :return:
            True        # locked
            False       # not locked
        """
        return self.lock == self.Lock.OPERATION

    def is_locked_delete(self):
        """
        检查是否加锁，是否锁定删除
        :return:
            True        # lock delete
            False       # not lock delete
        """
        return self.lock in [self.Lock.DELETE, self.Lock.OPERATION]


class ServerArchive(ServerBase):
    """
    虚拟服务器实例归档
    """

    class ArchiveType(models.TextChoices):
        ARCHIVE = 'archive', _('删除归档记录')
        REBUILD = 'rebuild', _('重建修改记录')

    server_id = models.CharField(verbose_name=_('服务器ID'), max_length=36, blank=True, default='',
                                 help_text=_('归档服务器的ID'))
    service = models.ForeignKey(to=ServiceConfig, null=True, on_delete=models.SET_NULL,
                                related_name='server_archive_set', verbose_name=_('接入的服务配置'))
    user = models.ForeignKey(to=User, verbose_name=_('创建者'), on_delete=models.SET_NULL,
                             related_name='user_server_archives', null=True)
    vo = models.ForeignKey(to=VirtualOrganization, null=True, on_delete=models.SET_NULL, default=None, blank=True,
                           related_name='vo_server_archive_set', verbose_name=_('项目组'))
    deleted_time = models.DateTimeField(verbose_name=_('删除归档时间'))
    archive_user = models.ForeignKey(to=User, verbose_name=_('归档人'), on_delete=models.SET_NULL,
                                     related_name='+', blank=True, null=True, default=None)
    archive_type = models.CharField(
        verbose_name=_('归档记录类型'), max_length=16, choices=ArchiveType.choices, default=ArchiveType.ARCHIVE)

    class Meta:
        ordering = ['-deleted_time']
        verbose_name = _('服务器归档记录')
        verbose_name_plural = verbose_name

    @classmethod
    def init_archive_from_server(cls, server, archive_user, archive_type, commit: bool = True):
        """
        创建归档记录
        :return:
            ServerArchive()

        :raises: Exception
        """
        if archive_type not in cls.ArchiveType.values:
            raise Exception(f'Invalid input archive_type')

        a = cls()
        a.server_id = server.id
        a.service = server.service
        a.name = server.name
        a.instance_id = server.instance_id
        a.instance_name = server.instance_name
        a.vcpus = server.vcpus
        a.ram = server.ram
        a.ipv4 = server.ipv4
        a.public_ip = server.public_ip
        a.image = server.image
        a.creation_time = server.creation_time
        a.remarks = server.remarks
        a.user_id = server.user_id
        a.vo_id = server.vo_id
        a.deleted_time = timezone.now()
        a.task_status = server.task_status
        a.center_quota = server.center_quota
        a.expiration_time = server.expiration_time
        a.classification = server.classification
        a.image_id = server.image_id
        a.image_desc = server.image_desc
        a.default_user = server.default_user
        a.default_password = server.default_password
        a.archive_user = archive_user
        a.start_time = server.start_time
        a.archive_type = archive_type
        a.pay_type = server.pay_type
        a.azone_id = server.azone_id
        a.disk_size = server.disk_size
        a.network_id = server.network_id
        a.situation = server.situation
        a.situation_time = server.situation_time

        if commit:
            a.save()

        return a


class Flavor(models.Model):
    id = models.CharField(blank=True, editable=False, max_length=36, primary_key=True, verbose_name='ID')
    flavor_id = models.CharField(blank=True, max_length=256, verbose_name='服务端规格ID')
    vcpus = models.IntegerField(verbose_name=_('虚拟CPU数'), default=0)
    ram = models.IntegerField(verbose_name=_('内存GiB'), default=0)
    disk = models.IntegerField(verbose_name=_('硬盘GB'), default=0)
    desc = models.CharField(max_length=255, verbose_name=_('Tag描述'), blank=True, default='')
    enable = models.BooleanField(verbose_name=_('可用状态'), default=True)
    creation_time = models.DateTimeField(auto_now_add=True, verbose_name=_('创建时间'))
    service = models.ForeignKey(to=ServiceConfig, on_delete=models.SET_NULL, db_constraint=False,
                                related_name='+', null=True, blank=True, default=None, verbose_name=_('服务单元'))

    class Meta:
        db_table = 'flavor'
        ordering = ['vcpus']
        verbose_name = _('配置样式')
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'Flavor(vcpus={self.vcpus}, ram={self.ram_mib}Mb)'

    @property
    def ram_mib(self):
        return self.ram * 1024

    @property
    def ram_gib(self):
        return self.ram

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.id:
            self.id = short_uuid1_l25()

        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)


class Disk(models.Model):
    """
    云硬盘实例
    """
    class TaskStatus(models.TextChoices):
        OK = 'ok', _('创建成功')
        CREATING = 'creating', _('正在创建中')
        FAILED = 'failed', _('创建失败')

    class QuotaType(models.TextChoices):
        PRIVATE = 'private', _('私有资源配额')
        SHARED = 'shared', _('共享资源配额')

    class Classification(models.TextChoices):
        PERSONAL = 'personal', _('个人的')
        VO = 'vo', _('VO组的')

    class Lock(models.TextChoices):
        FREE = 'free', _('无锁')
        DELETE = 'lock-delete', _('锁定删除')
        OPERATION = 'lock-operation', _('锁定所有操作，只允许读')

    id = models.CharField(blank=True, editable=False, max_length=36, primary_key=True, verbose_name='ID')
    name = models.CharField(max_length=255, verbose_name=_('云硬盘名称'))
    instance_id = models.CharField(max_length=128, verbose_name=_('云硬盘实例ID'), help_text=_('各接入服务单元中云硬盘的ID'))
    instance_name = models.CharField(
        max_length=255, blank=True, default='', verbose_name=_('云硬盘实例名称'), help_text=_('各接入服务单元中云硬盘的名称'))
    size = models.IntegerField(verbose_name=_('容量大小GiB'), default=0)
    service = models.ForeignKey(
        verbose_name=_('服务单元'), to=ServiceConfig, null=True, on_delete=models.SET_NULL, related_name='+',
        db_constraint=False, db_index=False
    )
    azone_id = models.CharField(verbose_name=_('可用区Id'), max_length=36, blank=True, default='')
    azone_name = models.CharField(verbose_name=_('可用区名称'), max_length=36, blank=True, default='')
    quota_type = models.CharField(
        verbose_name=_('服务单元配额'), max_length=16, choices=QuotaType.choices, default=QuotaType.PRIVATE.value)
    creation_time = models.DateTimeField(verbose_name=_('创建时间'))
    remarks = models.CharField(max_length=255, blank=True, default='', verbose_name=_('备注'))
    task_status = models.CharField(
        verbose_name=_('创建状态'), max_length=16, choices=TaskStatus.choices, default=TaskStatus.OK.value)
    expiration_time = models.DateTimeField(verbose_name=_('过期时间'), null=True, blank=True, default=None)
    start_time = models.DateTimeField(
        verbose_name=_('计量开始时间'), default=timezone.now, help_text=_('云硬盘资源使用量计量开始时间'))
    pay_type = models.CharField(
        verbose_name=_('计费方式'), max_length=16, choices=PayType.choices, default=PayType.POSTPAID.value)
    classification = models.CharField(
        verbose_name=_('云硬盘归属类型'), max_length=16, choices=Classification.choices, default=Classification.PERSONAL,
        help_text=_('标识云硬盘属于申请者个人的，还是vo组的'))
    user = models.ForeignKey(
        to=User, verbose_name=_('创建者'), related_name='+', null=True, on_delete=models.SET_NULL,
        db_constraint=False, blank=True, default=None)
    vo = models.ForeignKey(
        verbose_name=_('项目组'), to=VirtualOrganization, related_name='+', null=True, on_delete=models.SET_NULL,
        db_constraint=False, blank=True, default=None)
    lock = models.CharField(verbose_name=_('锁'), max_length=16, choices=Lock.choices, default=Lock.FREE,
                            help_text=_('加锁锁定云硬盘，防止误操作'))
    email_lasttime = models.DateTimeField(verbose_name=_('上次发送邮件时间'), null=True, blank=True, default=None,
                                          help_text=_('记录上次发邮件的时间，邮件通知用户云硬盘即将到期'))
    server = models.ForeignKey(
        verbose_name=_('挂载于云主机'), to=Server, related_name='mounted_disk_set', on_delete=models.SET_NULL,
        db_constraint=False, db_index=False, null=True, blank=True, default=None)
    mountpoint = models.CharField(
        verbose_name=_('挂载点/设备名'), max_length=64, blank=True, default='', help_text='例如 "/dev/vdc"')
    attached_time = models.DateTimeField(verbose_name=_('最后一次挂载时间'), null=True, blank=True, default=None)
    detached_time = models.DateTimeField(verbose_name=_('最后一次卸载时间'), null=True, blank=True, default=None)
    deleted = models.BooleanField(verbose_name=_('删除状态'), default=False, help_text=_('选中表示已删除'))
    deleted_time = models.DateTimeField(verbose_name=_('删除时间'), null=True, blank=True, default=None)
    deleted_user = models.CharField(verbose_name=_('删除人'), max_length=128, default='')

    class Meta:
        db_table = 'servers_disk'
        ordering = ['-creation_time']
        verbose_name = _('云硬盘')
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'Disk({self.id}, {self.size}GiB)'

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.id:
            self.id = short_uuid1_l25() + '-d'

        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    def do_soft_delete(self, deleted_user: str, raise_exception=True):
        """
        :return: True or False
        """
        try:
            self.deleted = True
            self.deleted_time = timezone.now()
            self.deleted_user = deleted_user
            self.save(update_fields=['deleted', 'deleted_time', 'deleted_user'])
        except Exception as e:
            if raise_exception:
                raise e

            return False

        return True

    def is_locked_operation(self):
        """
        是否加锁, 锁定了一切操作
        :return:
            True        # locked
            False       # not locked
        """
        return self.lock == self.Lock.OPERATION.value

    def is_locked_delete(self):
        """
        检查是否加锁，是否锁定删除
        :return:
            True        # lock delete
            False       # not lock delete
        """
        return self.lock in [self.Lock.DELETE.value, self.Lock.OPERATION.value]

    def set_attach(self, server_id: str):
        self.server_id = server_id
        self.attached_time = timezone.now()
        self.save(update_fields=['server_id', 'attached_time'])

    def set_detach(self):
        self.server_id = None
        self.detached_time = timezone.now()
        self.save(update_fields=['server_id', 'detached_time'])

    def is_attached(self):
        if self.server_id:
            return True

        return False

    @staticmethod
    def count_private_quota_used(service):
        """
        接入服务的私有资源配额已用统计

        :param service: 接入服务配置对象
        :return:
            {
                'disk_used_count': 1
            }
        """
        if not isinstance(service, models.Model):
            service_id = service
        else:
            service_id = service.id

        stat = Disk.objects.filter(
            service_id=service_id, deleted=False, quota_type=Disk.QuotaType.PRIVATE.value
        ).aggregate(disk_used_count=Sum('size'))

        if stat.get('disk_used_count', 0) is None:
            stat['disk_used_count'] = 0

        return stat

    def belong_to_vo(self):
        return self.classification == self.Classification.VO.value


class ResourceActionLog(UuidModel):
    class ResourceType(models.TextChoices):
        SERVER = 'server', _('云主机')
        DISK = 'disk', _('云硬盘')
        BUCHET = 'bucket', _('存储桶')

    class ActionFlag(models.TextChoices):
        ADDITION = 'add', _('添加')
        CHANGE = 'change', _('修改')
        DELETION = 'delete', _('删除')

    action_time = models.DateTimeField(verbose_name=_('操作时间'), editable=False)
    user_id = models.CharField(verbose_name=_('操作者id'), max_length=36)
    username = models.CharField(verbose_name=_('操作者'), max_length=150)
    action_flag = models.CharField(verbose_name=_('操作类型'), max_length=16, choices=ActionFlag.choices)
    resource_type = models.CharField(verbose_name=_('资源类型'), max_length=16, choices=ResourceType.choices)
    resource_id = models.TextField(_('资源id'), blank=True, null=True)
    resource_repr = models.CharField(_('资源描述'), max_length=200)
    resource_message = models.JSONField(_('资源信息'), blank=True)
    owner_id = models.CharField(verbose_name=_('资源拥有者id'), max_length=32)
    owner_name = models.CharField(verbose_name=_('资源拥有者'), max_length=128)
    owner_type = models.CharField(verbose_name=_('资源拥有者类型'), max_length=16, choices=OwnerType.choices)

    class Meta:
        verbose_name = _('资源操作日志')
        verbose_name_plural = verbose_name
        db_table = 'resource_action_log'
        ordering = ['-action_time']

    def __repr__(self):
        return str(self.action_time)

    def __str__(self):
        if self.is_addition():
            return _('创建 “%(object)s”') % {'object': self.resource_repr}
        elif self.is_change():
            return _('修改 “%(object)s”') % {'object': self.resource_repr}
        elif self.is_deletion():
            return _('删除 “%(object)s”') % {'object': self.resource_repr}

        return _('资源操作日志')

    def is_addition(self):
        return self.action_flag == self.ActionFlag.ADDITION.value

    def is_change(self):
        return self.action_flag == self.ActionFlag.CHANGE.value

    def is_deletion(self):
        return self.action_flag == self.ActionFlag.DELETION.value

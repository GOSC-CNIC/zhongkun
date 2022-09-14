from django.db import models
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

from service.models import DataCenter
from utils.model import UuidModel, get_encryptor


User = get_user_model()


class ObjectsService(UuidModel):
    """
    对象存储接入服务配置
    """
    class ServiceType(models.TextChoices):
        IHARBOR = 'iharbor', 'iHarbor'
        SWIFT = 'swift', 'Swift'
        S3 = 's3', 'S3'

    class Status(models.TextChoices):
        ENABLE = 'enable', _('服务中')
        DISABLE = 'disable', _('停止服务')
        DELETED = 'deleted', _('删除')

    data_center = models.ForeignKey(to=DataCenter, null=True, on_delete=models.SET_NULL,
                                    related_name='object_service_set', verbose_name=_('数据中心'))
    name = models.CharField(max_length=255, verbose_name=_('服务名称'))
    name_en = models.CharField(verbose_name=_('服务英文名称'), max_length=255, default='')
    service_type = models.CharField(max_length=16, choices=ServiceType.choices, default=ServiceType.IHARBOR.value,
                                    verbose_name=_('服务平台类型'))
    endpoint_url = models.CharField(max_length=255, verbose_name=_('服务地址url'), unique=True,
                                    help_text='http(s)://{hostname}:{port}/')
    api_version = models.CharField(max_length=64, default='v1', verbose_name=_('API版本'),
                                   help_text=_('预留，主要iHarbor使用'))
    username = models.CharField(max_length=128, verbose_name=_('用户名'), help_text=_('用于此服务认证的用户名'))
    password = models.CharField(max_length=128, verbose_name=_('密码'))
    add_time = models.DateTimeField(auto_now_add=True, verbose_name=_('添加时间'))
    status = models.CharField(max_length=16, verbose_name=_('服务状态'), choices=Status.choices,
                              default=Status.ENABLE.value)
    remarks = models.CharField(max_length=255, default='', blank=True, verbose_name=_('备注'))
    extra = models.CharField(max_length=1024, blank=True, default='', verbose_name=_('其他配置'), help_text=_('json格式'))
    users = models.ManyToManyField(to=User, verbose_name=_('用户'), blank=True, related_name='object_service_set')

    provide_ftp = models.BooleanField(verbose_name=_('是否提供FTP服务'), default=True)
    ftp_domains = models.CharField(max_length=1024, blank=True, default='', verbose_name=_('FTP服务域名或IP'),
                                   help_text=_('多个域名时以,分割'))
    contact_person = models.CharField(verbose_name=_('联系人名称'), max_length=128,
                                      blank=True, default='')
    contact_email = models.EmailField(verbose_name=_('联系人邮箱'), blank=True, default='')
    contact_telephone = models.CharField(verbose_name=_('联系人电话'), max_length=16,
                                         blank=True, default='')
    contact_fixed_phone = models.CharField(verbose_name=_('联系人固定电话'), max_length=16,
                                           blank=True, default='')
    contact_address = models.CharField(verbose_name=_('联系人地址'), max_length=256,
                                       blank=True, default='')
    logo_url = models.CharField(verbose_name=_('LOGO url'), max_length=256,
                                blank=True, default='')
    longitude = models.FloatField(verbose_name=_('经度'), blank=True, default=0)
    latitude = models.FloatField(verbose_name=_('纬度'), blank=True, default=0)
    pay_app_service_id = models.CharField(
        verbose_name=_('余额结算APP服务ID'), max_length=36, default='',
        help_text=_('此服务对应的APP服务（注册在余额结算中的APP服务）id，扣费时需要此id，用于指定哪个服务发生的扣费'))

    class Meta:
        db_table = 'object_service'
        ordering = ['-add_time']
        verbose_name = _('对象存储服务单元接入配置')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    @property
    def raw_password(self):
        """
        :return:
            str     # success
            None    # failed, invalid encrypted password
        """
        encryptor = get_encryptor()
        try:
            return encryptor.decrypt(self.password)
        except encryptor.InvalidEncrypted as e:
            return None

    def set_password(self, raw_password: str):
        encryptor = get_encryptor()
        self.password = encryptor.encrypt(raw_password)

    def ftp_domains_list(self):
        return self.ftp_domains.split(',')


class BucketBase(UuidModel):
    bucket_id = models.CharField(max_length=36, verbose_name=_('存储桶ID'), help_text=_('存储桶在对象存储服务单元中的id'))
    name = models.CharField(max_length=63, verbose_name=_('存储桶名称'))
    creation_time = models.DateTimeField(verbose_name=_('创建时间'))

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class Bucket(BucketBase):
    user = models.ForeignKey(to=User, null=True, related_name='+', on_delete=models.SET_NULL,
                             verbose_name=_('所属用户'))
    service = models.ForeignKey(to=ObjectsService, related_name='+', null=True,
                                on_delete=models.SET_NULL, verbose_name=_('所属服务'))

    class Meta:
        db_table = 'bucket'
        ordering = ['-creation_time']
        verbose_name = _('存储桶')
        verbose_name_plural = verbose_name

    def do_archive(self, archiver: str, raise_exception: bool = False):
        """
        删除归档存储桶
        """
        arc = BucketArchive()
        arc.original_id = self.id
        arc.bucket_id = self.bucket_id
        arc.name = self.name
        arc.creation_time = self.creation_time
        arc.user_id = self.user_id
        arc.service_id = self.service_id
        arc.archiver = archiver

        try:
            with transaction.atomic():
                arc.save(force_insert=True)
                self.delete()
        except Exception as e:
            if raise_exception:
                raise e

            return False

        return True


class BucketArchive(BucketBase):
    original_id = models.CharField(max_length=36, verbose_name=_('存储桶删除前原始id'), default='',
                                   help_text=_('存储桶删除前在存储桶表中原始id'))
    user = models.ForeignKey(to=User, null=True, related_name='+', on_delete=models.SET_NULL,
                             verbose_name=_('所属用户'))
    service = models.ForeignKey(to=ObjectsService, null=True, related_name='+',
                                on_delete=models.SET_NULL, verbose_name=_('所属服务'))
    delete_time = models.DateTimeField(auto_now_add=True, verbose_name=_('删除时间'))
    archiver = models.CharField(verbose_name=_('删除归档人'), max_length=128, blank=True, default='')

    class Meta:
        db_table = 'bucket_archive'
        ordering = ['-delete_time']
        verbose_name = _('存储桶归档记录')
        verbose_name_plural = verbose_name


class StorageQuota(UuidModel):
    count_total = models.IntegerField(verbose_name=_('存储桶数'), default=0)
    count_used = models.IntegerField(verbose_name=_('已创建存储桶数'), default=0)
    size_gb_total = models.IntegerField(verbose_name=_('总存储容量'), default=0, help_text='Gb')
    size_gb_used = models.IntegerField(verbose_name=_('已用存储容量'), default=0, help_text='Gb')
    creation_time = models.DateTimeField(auto_now_add=True, verbose_name=_('创建时间'))
    expiration_time = models.DateTimeField(verbose_name=_('过期时间'), null=True, blank=True, default=None)
    deleted = models.BooleanField(verbose_name=_('删除'), default=False)
    is_email = models.BooleanField(verbose_name=_('是否邮件通知'), default=False,
                                   help_text=_('是否邮件通知用户配额即将到期'))
    user = models.ForeignKey(to=User, null=True, on_delete=models.SET_NULL,
                             related_name='storage_quotas', verbose_name=_('用户'))
    service = models.ForeignKey(to=ObjectsService, null=True, on_delete=models.SET_NULL,
                                related_name='storage_quotas', verbose_name=_('所属服务'))

    class Meta:
        db_table = 'storage_quota'
        ordering = ['-creation_time']
        verbose_name = _('存储配额')
        verbose_name_plural = verbose_name

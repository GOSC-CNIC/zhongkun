from django.db import models
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

from service.models import DataCenter

from utils.model import UuidModel

User = get_user_model()


class ObjectsService(UuidModel):
    """
    对象存储接入服务配置
    """
    SERVICE_IHARBOR = 'iharbor'
    SERVICE_SWIFT = 'swift'
    SERVICE_S3 = 's3'
    SERVICE_TYPE_CHOICES = (
        (SERVICE_IHARBOR, 'iHarhor'),
        (SERVICE_SWIFT, 'Swift'),
        (SERVICE_S3, 'S3'),
    )

    STATUS_SERVING = 'serving'
    STATUS_OUT_OF = 'out_of'
    CHOICE_STATUS = (
        (STATUS_SERVING, _('服务中')),
        (STATUS_OUT_OF, _('停止服务'))
    )

    data_center = models.ForeignKey(to=DataCenter, null=True, on_delete=models.SET_NULL,
                                    related_name='object_service_set', verbose_name=_('数据中心'))
    name = models.CharField(max_length=255, verbose_name=_('服务名称'))
    service_type = models.CharField(max_length=16, choices=SERVICE_TYPE_CHOICES, default=SERVICE_IHARBOR,
                                    verbose_name=_('服务平台类型'))
    endpoint_url = models.CharField(max_length=255, verbose_name=_('服务地址url'), unique=True,
                                    help_text='http(s)://{hostname}:{port}/')
    api_version = models.CharField(max_length=64, default='v3', verbose_name=_('API版本'),
                                   help_text=_('预留，主要iHarbor使用'))
    username = models.CharField(max_length=128, verbose_name=_('用户名'), help_text=_('用于此服务认证的用户名'))
    password = models.CharField(max_length=128, verbose_name=_('密码'))
    add_time = models.DateTimeField(auto_now_add=True, verbose_name=_('添加时间'))
    status = models.CharField(max_length=16, verbose_name=_('服务状态'), choices=CHOICE_STATUS, default=STATUS_SERVING)
    remarks = models.CharField(max_length=255, default='', blank=True, verbose_name=_('备注'))
    extra = models.CharField(max_length=1024, blank=True, default='', verbose_name=_('其他配置'), help_text=_('json格式'))
    users = models.ManyToManyField(to=User, verbose_name=_('用户'), blank=True, related_name='object_service_set')

    class Meta:
        db_table = 'object_service'
        ordering = ['-add_time']
        verbose_name = _('对象存储服务接入配置')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class BucketBase(UuidModel):
    ACCESS_PUBLIC = 'public'
    ACCESS_PRIVATE = 'private'
    CHOICES_ACCESS = (
        (ACCESS_PUBLIC, _('公有')),
        (ACCESS_PRIVATE, _('私有'))
    )

    LOCK_READONLY = 'readonly'
    LOCK_READWRITE = 'readwrite'
    LOCK_FORBIDDEN = 'forbidden'
    CHOICES_LOCK = (
        (LOCK_READWRITE, _('可读可写')),
        (LOCK_READONLY, _('只读')),
        (LOCK_FORBIDDEN, _('禁止访问'))
    )

    bucket_id = models.CharField(max_length=36, verbose_name=_('存储桶ID'))
    name = models.CharField(max_length=63, verbose_name=_('存储桶名称'))
    creation_time = models.DateTimeField(auto_now_add=True, verbose_name=_('创建时间'))
    access_perm = models.CharField(max_length=16, verbose_name='访问权限',
                                   choices=CHOICES_ACCESS, default=ACCESS_PRIVATE)
    lock = models.CharField(max_length=16, choices=CHOICES_LOCK,
                            default=LOCK_READWRITE, verbose_name=_('读写锁'))

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class Bucket(BucketBase):
    user = models.ForeignKey(to=User, null=True, related_name='bucket_set', on_delete=models.SET_NULL,
                             verbose_name=_('所属用户'))
    service = models.ForeignKey(to=ObjectsService, related_name='bucket_set',
                                on_delete=models.DO_NOTHING, verbose_name=_('所属服务'))
    token = models.CharField(max_length=36, verbose_name=_('桶读写token'))

    class Meta:
        db_table = 'bucket'
        ordering = ['-creation_time']
        verbose_name = _('存储桶')
        verbose_name_plural = verbose_name

    def do_archive(self, raise_exception: bool = False):
        """
        删除归档存储桶
        """
        arc = BucketArchive()
        arc.id = self.id
        arc.bucket_id = self.bucket_id
        arc.name = self.name
        arc.creation_time = self.creation_time
        arc.access_perm = self.access_perm
        arc.lock = self.lock
        arc.user_id = self.user_id
        arc.service_id = self.service_id

        try:
            with transaction.atomic():
                arc.save()
                self.delete()
        except Exception as e:
            if raise_exception:
                raise e

            return False

        return True


class BucketArchive(BucketBase):
    bucket_id = models.CharField(max_length=36, verbose_name=_('存储桶ID'))
    delete_time = models.DateTimeField(auto_now_add=True, verbose_name=_('删除时间'))
    user = models.ForeignKey(to=User, null=True, related_name='bucket_archive_set', on_delete=models.SET_NULL,
                             verbose_name=_('所属用户'))
    service = models.ForeignKey(to=ObjectsService, null=True, related_name='bucket_archive_set',
                                on_delete=models.SET_NULL, verbose_name=_('所属服务'))

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

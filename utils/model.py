from django.db import models
from django.contrib import admin
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from utils.crypto import Encryptor
from utils.rand_utils import short_uuid1_25


def get_encryptor():
    return Encryptor(key=settings.SECRET_KEY)


class CustomIdModel(models.Model):
    id = models.CharField(blank=True, editable=False, max_length=36, primary_key=True, verbose_name='ID')

    class Meta:
        abstract = True

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.enforce_id()
        super().save(force_insert=force_insert, force_update=force_update,
                     using=using, update_fields=update_fields)

    def enforce_id(self):
        """确保id有效"""
        if not self.id:
            self.id = self.generate_id()

        return self.id

    def generate_id(self) -> str:
        raise NotImplementedError('`generate_id()` must be implemented.')


class UuidModel(CustomIdModel):
    class Meta:
        abstract = True

    def generate_id(self):
        return short_uuid1_25()


class OwnerType(models.TextChoices):
    USER = 'user', _('用户')
    VO = 'vo', _('VO组')


class PayType(models.TextChoices):
    PREPAID = 'prepaid', _('包年包月')
    POSTPAID = 'postpaid', _('按量计费')
    QUOTA = 'quota', _('资源配额券')


class BaseModelAdmin(admin.ModelAdmin):
    class Media:
        css = {
            'all': ['yunkun/admin/common.css']
        }


class NoDeleteSelectModelAdmin(BaseModelAdmin):
    def get_actions(self, request):
        actions = super(NoDeleteSelectModelAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']

        return actions


class ResourceType(models.TextChoices):
    VM = 'vm', _('云主机')
    DISK = 'disk', _('云硬盘')
    BUCKET = 'bucket', _('存储桶')
    SCAN = 'scan', _('安全扫描')
    VM_SNAPSHOT = 'vm_snapshot', _('云主机快照')


class DeriveTypeBase(models.TextChoices):
    OTHER = 'other', _('其他')
    TRIAL = 'trial', _('试用')
    STAFF = 'staff', _('内部员工')

from uuid import uuid1

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from utils.crypto import Encryptor


def get_encryptor():
    return Encryptor(key=settings.SECRET_KEY)


class UuidModel(models.Model):
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
            self.id = str(uuid1())

        return self.id


class OwnerType(models.TextChoices):
    USER = 'user', _('用户')
    VO = 'vo', _('VO组')


class PayType(models.TextChoices):
    PREPAID = 'prepaid', _('包年包月')
    POSTPAID = 'postpaid', _('按量计费')
    QUOTA = 'quota', _('资源配额券')

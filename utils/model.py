from uuid import uuid1

from django.db import models
from django.conf import settings

from utils.crypto import Encryptor


def get_encryptor():
    return Encryptor(key=settings.SECRET_KEY)


class UuidModel(models.Model):
    id = models.CharField(blank=True, editable=False, max_length=36, primary_key=True, verbose_name='ID')

    class Meta:
        abstract = True

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.id:
            self.id = str(uuid1())

        super().save(force_insert=force_insert, force_update=force_update,
                     using=using, update_fields=update_fields)



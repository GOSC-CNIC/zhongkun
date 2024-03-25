from django.db import models
from django.core import checks
from django.core.validators import BaseValidator
from django.utils.translation import gettext_lazy
from django.utils.deconstruct import deconstructible


@deconstructible
class LengthValidator(BaseValidator):
    message = gettext_lazy("确保值长度等于%(limit_value)d.")
    code = "length"

    def compare(self, a, b):
        return a == b

    def clean(self, x):
        return len(x)


class ByteField(models.BinaryField):
    """
    定长二进制字段
    """
    def __init__(self, *args, **kwargs):
        if 'max_length' not in kwargs:
            raise Exception('ByteField必须通过参数max_length指定字节长度，取值必须在1至1024之间')

        length = kwargs['max_length']
        if not (1 <= length <= 1024):
            raise Exception('ByteField参数length的取值必须在1至1024之间')

        super(ByteField, self).__init__(*args, **kwargs)
        self.validators.append(LengthValidator(self.max_length))

    def db_type(self, connection) -> str:
        if connection.vendor == 'mysql':
            return f"binary({self.max_length})"
        elif connection.vendor == 'postgresql':
            return 'bytea'
        elif connection.vendor == 'sqlite':
            return 'BLOB'

        raise Exception(f'此字段不支持数据库 {connection.vendor}.')

    def get_internal_type(self):
        return 'ByteField'

    def _check_str_default_value(self):
        errs = super(ByteField, self)._check_str_default_value()
        if self.has_default() and len(self.default) != self.max_length:
            errs.append([
                checks.Error(
                    "ByteField's default must be a bytes. The length of default must be equal max_length",
                    obj=self,
                    id="fields.E170",
                )
            ])
        return errs

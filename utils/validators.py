import json

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.utils.deconstruct import deconstructible


@deconstructible()
class JSONStringValidator:
    message = _('值必须是一个有效的JSON字符串。')
    code = 'invalid'

    def __init__(self, message=None, code=None, decoder=None):
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code
        self.decoder = decoder

    def __call__(self, value):
        """
        Validate that the input value is valid json string
        """
        try:
            json.loads(value, cls=self.decoder)
        except TypeError:
            raise ValidationError(self.message, code=self.code, params={'value': value})


json_string_validator = JSONStringValidator()

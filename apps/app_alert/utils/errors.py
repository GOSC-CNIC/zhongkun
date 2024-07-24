from rest_framework.exceptions import APIException
from rest_framework import status
from django.utils.translation import gettext_lazy as _


class APIError(APIException):
    status_code = 500
    default_detail = 'API Error'


class BadRequest(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'FieldNotfound'


class InvalidArgument(BadRequest):
    default_message = 'Invalid Argument.'
    default_code = 'InvalidArgument'


class NotFound(APIException):
    default_message = 'Not Found.'
    default_code = 'NotFound'
    default_status_code = 404


class AccessDenied(APIException):
    default_message = 'Access Denied.'
    default_code = 'AccessDenied'
    default_status_code = 403


class JWTRequired(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = '请使用JWT请求接口'


class GroupMemberExistedError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('用户已经存在，请勿重复添加')
    default_code = 'Existed'


class GroupElementExistedError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('元素已经存在，请勿重复添加')
    default_code = 'ElementExisted'

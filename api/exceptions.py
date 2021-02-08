"""
异常定义
"""
from core.errors import Error


class APIException(Error):
    pass


class AuthenticationFailed(APIException):
    default_message = 'Incorrect authentication credentials.'
    default_code = 'AuthenticationFailed'
    default_status_code = 401


class InvalidJWT(APIException):
    default_message = 'Token is invalid or expired.'
    default_code = 'InvalidJWT'
    default_status_code = 401


class NotFound(APIException):
    default_message = 'Not Found.'
    default_code = 'NotFound'
    default_status_code = 404


class ServerNotExist(NotFound):
    default_message = 'This server is not exist.'
    default_code = 'ServerNotExist'
    default_status_code = 404


class ServiceNotExist(NotFound):
    default_message = 'This service is not exist.'
    default_code = 'ServiceNotExist'


class BadRequest(APIException):
    default_message = 'BadRequest.'
    default_code = 'BadRequest'
    default_status_code = 400


class NoSupportVPN(APIException):
    default_message = 'This service does not provide VPN support.'
    default_code = 'NoSupportVPN'
    default_status_code = 405


class InvalidArgument(BadRequest):
    default_message = 'Invalid Argument.'
    default_code = 'InvalidArgument'


class NoFoundArgument(BadRequest):
    default_message = 'No Found Argument.'
    default_code = 'NoFoundArgument'


class AccessDenied(APIException):
    default_message = 'Access Denied.'
    default_code = 'AccessDenied'
    default_status_code = 403


class MethodNotSupportInService(APIException):
    default_message = 'This method or business is not supported by this service center.'
    default_code = 'MethodNotSupportInService'
    default_status_code = 405

class Error(Exception):
    default_message = 'We encountered an internal error. Please try again.'
    default_code = 'InternalError'
    default_status_code = 500

    def __init__(self, message: str = '', code: str = '', status_code=None, extend_msg=''):
        """
        :param message: 错误描述
        :param code: 错误代码
        :param status_code: HTTP状态码
        :param extend_msg: 扩展错误描述的信息，追加到message后面
        """
        self.message = message if message else self.default_message
        self.code = code if code else self.default_code
        self.status_code = self.default_status_code if status_code is None else status_code
        if extend_msg:
            self.message += '&&' + extend_msg

    def __repr__(self):
        return f'{type(self)}(message={self.message}, code={self.code}, status_code={self.status_code})'

    def __str__(self):
        return self.message

    def detail_str(self):
        return self.__repr__()

    def err_data(self):
        return {
            'code': self.code,
            'message': self.message
        }

    def copy_to_sub_error(self, error_cls):
        """
        创建一个Error子类对象
        :param error_cls: subclass of Error
        """
        return error_cls(message=self.message, code=self.code, status_code=self.status_code)


# API请求相关错误
class APIError(Error):
    default_message = 'We encountered an internal error. Please try again.'
    default_code = 'APIRequestError'
    default_status_code = 500


class AuthenticationFailed(APIError):
    default_message = 'Incorrect authentication credentials.'
    default_code = 'AuthenticationFailed'
    status_code = 401


class NotAuthenticated(APIError):
    status_code = 401
    default_detail = 'Authentication credentials were not provided.'
    default_code = 'NotAuthenticated'


class UnsupportedServiceType(Error):
    status_code = 400
    default_detail = 'Unsupported service type.'
    default_code = 'UnsupportedServiceType'


class ServerNotExist(Error):
    default_message = 'This server instance is not exist.'
    default_code = 'ServerNotExist'
    status_code = 404


class MethodNotSupportInService(Error):
    default_message = 'This method or business is not supported by this service center.'
    default_code = 'MethodNotSupportInService'
    status_code = 405

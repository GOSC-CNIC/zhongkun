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

    @classmethod
    def from_error(cls, err):
        if isinstance(err, Error):
            return cls(message=err.message, code=err.code, status_code=err.status_code)

        return cls(message=str(err))


class BadRequestError(Error):
    default_message = "bad request."
    default_code = "BadRequest"
    default_status_code = 400


class QuotaError(Error):
    pass


class NoSuchQuotaError(QuotaError):
    default_message = "The specified quota does not exist."
    default_code = "NoSuchQuota"
    default_status_code = 404


class QuotaShortageError(QuotaError):
    """配置不足短缺"""
    default_message = "There are not enough resources to use."
    default_code = "QuotaShortage"
    default_status_code = 409


class CenterApplyNotPassError(Error):
    default_message = '机构加入申请未通过'
    default_code = 'CenterApplyNotPass'
    default_status_code = 409


class DoNotKnowWhichCenterBelongToError(Error):
    default_message = '不确定归属于哪一个机构'
    default_code = 'DoNotKnowWhichCenterBelongTo'
    default_status_code = 409


class NoCenterBelongToError(Error):
    default_message = '没有归属的机构'
    default_code = 'NoCenterBelongTo'
    default_status_code = 409

from datetime import datetime
import requests

from storage.adapter import inputs
from storage.adapter import outputs
from core import errors
from .builders import APIBuilder
from .converters import OutputConverter


def get_failed_msg(response, msg_key='message'):
    """
    请求失败错误信息

    :param response: requests.Response()
    :param msg_key: 信息键值
    :return:
    """
    try:
        data = response.json()
        msg = data.get(msg_key, '')
        return msg
    except Exception:
        return ''


def get_failed_err_code(response, code_key='code'):
    """
    请求失败错误码

    :param response: requests.Response()
    :param code_key: 信息键值
    :return:
    """
    try:
        data = response.json()
        code = data.get(code_key, '')
        return code
    except Exception:
        return ''


class IHarborClient:
    def __init__(
            self,
            endpoint_url: str,
            auth: outputs.AuthenticateOutput = None,
            api_version: str = 'v1',
            **kwargs
    ):

        api_version = api_version.lower()
        api_version = api_version if api_version in ['v1'] else 'v1'
        self.api_builder = APIBuilder(endpoint_url=endpoint_url, api_version=api_version)
        self.endpoint_url = endpoint_url.rstrip('/')
        self.auth = auth
        self.api_version = api_version
        self.kwargs = kwargs

    def get_auth_header(self):
        """
        :return: {}

        :raises: NotAuthenticated, AuthenticationFailed, Error
        """
        auth = self.auth
        now = datetime.utcnow().timestamp()
        if auth is None:
            raise errors.NotAuthenticated()
        elif now >= auth.expire:
            params = inputs.AuthenticateInput(username=auth.username, password=auth.password)
            auth = self.authenticate(params=params)

        if not auth.ok:
            if isinstance(auth.error, errors.Error):
                raise auth.error

        h = auth.header
        return {h.header_name: h.header_value}

    @staticmethod
    def do_request(method: str, url: str, ok_status_codes=(200,), headers=None, **kwargs):
        """
        :param method: 'get', 'post, 'put', 'delete', 'patch', ..
        :param ok_status_codes: 表示请求成功的状态码列表，返回响应体，其他抛出Error
        :param url:
        :param headers:
        :param kwargs:
        :return:
            requests.Response()
        :raises: Error, AuthenticationFailed, APIError
        """
        try:
            r = requests.request(method=method, url=url, headers=headers, **kwargs)
        except Exception as e:
            raise errors.Error(str(e))

        if not isinstance(ok_status_codes, (list, tuple)):
            ok_status_codes = [ok_status_codes]

        if r.status_code in ok_status_codes:
            return r

        if r.status_code == 401:
            raise errors.AuthenticationFailed()

        msg = get_failed_msg(r)
        err_code = get_failed_err_code(r)
        raise errors.APIException(msg, status_code=r.status_code, code=err_code)

    def authenticate(self, params: inputs.AuthenticateInput, **kwargs) -> outputs.AuthenticateOutput:
        """
        认证获取 Token

        :return:
            outputs.AuthenticateOutput()
        """
        try:
            auth = self.authenticate_jwt(username=params.username, password=params.password)
        except errors.Error:
            raise

        self.auth = auth
        return auth

    def authenticate_jwt(self, username, password):
        url = self.api_builder.jwt_base_url()
        try:
            r = requests.post(url, data={'username': username, 'password': password})
        except Exception as e:
            return OutputConverter().to_authenticate_output_error(error=errors.Error(str(e)), style='jwt')

        if r.status_code == 200:
            data = r.json()
            token = data['access']
            return OutputConverter.to_authenticate_output_jwt(token=token, username=username, password=password)

        err = errors.AuthenticationFailed(status_code=r.status_code)
        return OutputConverter().to_authenticate_output_error(error=err, style='jwt')

    def bucket_lock(self, params: inputs.BucketLockInput) -> outputs.BucketLockOutput:
        url = self.api_builder.bucket_lock_url(bucket_name=params.bucket_name, lock=params.lock)
        try:
            headers = self.get_auth_header()
            r = self.do_request(method='post', url=url, ok_status_codes=[200, 403, 404], headers=headers)
        except errors.Error as e:
            return outputs.BucketLockOutput(ok=False, error=e)

        err_code = get_failed_err_code(r)
        msg = get_failed_msg(r)
        if r.status_code == 200:
            return outputs.BucketLockOutput(ok=True, error=None)

        if r.status_code == 404 and err_code == 'NoSuchBucket':
            error = errors.BucketNotExist(message=msg)
        elif r.status_code == 403 and err_code == 'AccessDenied':
            error = errors.AccessDenied(message=msg)
        else:
            error = errors.APIException(message=msg, status_code=r.status_code, code=err_code)

        return outputs.BucketLockOutput(ok=False, error=error)

    def bucket_create(self, params: inputs.BucketCreateInput) -> outputs.BucketCreateOutput:
        url = self.api_builder.bucket_create_url()
        try:
            headers = self.get_auth_header()
            data = {'name': params.bucket_name, 'username': params.username}
            r = self.do_request(
                method='post', url=url, data=data,
                ok_status_codes=[200, 400, 403, 409], headers=headers
            )
        except errors.Error as e:
            return OutputConverter.to_bucket_create_output_error(e)

        if r.status_code == 200:
            return OutputConverter.to_bucket_create_output(r.json())

        err_code = get_failed_err_code(r)
        msg = get_failed_msg(r)
        if r.status_code == 403 and err_code == 'AccessDenied':
            error = errors.AccessDenied(message=msg)
        elif r.status_code == 409 and err_code == 'BucketAlreadyExists':
            error = errors.BucketAlreadyExists()
        else:
            error = errors.APIException(message=msg, status_code=r.status_code, code=err_code)

        return OutputConverter.to_bucket_create_output_error(error)

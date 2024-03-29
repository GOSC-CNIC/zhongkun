from ..exceptions import (Error, APIError, AuthenticationFailed as AuthF, NotAuthenticated as NotAuth,
                          ServerNotExist, ResourceNotFound)


class AuthenticationFailed(AuthF):
    pass


class NotAuthenticated(NotAuth):
    pass


class ServerNotExistError(ServerNotExist):
    pass


class URLError(Error):
    default_message = 'We encountered an error about url.'
    default_code = 'URLError'


class URLInvalidError(Error):
    default_message = 'Invalid url.'
    default_code = 'URLInvalidError'


class URLBuildError(Error):
    default_message = 'We encountered an error during build api url.'
    default_code = 'APIBuildError'


class AuthenticationError(Error):
    default_message = 'We encountered an error during authenticate.'
    default_code = 'AuthenticationError'


class APIInvalidParam(APIError):
    default_message = 'invalid param'
    default_code = 'APIInvalidParam'


class OutputConvertError(Error):
    default_message = 'EVCloud adapter convert output object error.'
    default_code = 'OutputConvertError'

class ResourceNotFoundError(ResourceNotFound):
    pass

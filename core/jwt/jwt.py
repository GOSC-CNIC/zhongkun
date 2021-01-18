"""
django-rest-framework-simplejwt
"""
from pytz import utc
from datetime import datetime, timedelta
from calendar import timegm
from uuid import uuid4

from django.contrib.auth import get_user_model
import jwt
from jwt import InvalidAlgorithmError, InvalidTokenError, algorithms
from rest_framework.settings import settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework import HTTP_HEADER_ENCODING
from rest_framework import authentication

from core.errors import Error


class DictObjectWrapper:
    def __init__(self, d: dict):
        self._d = d

    def __getattr__(self, name):
        return self._d.get(name)

    def __setattr__(self, name, value):
        if name == '_d':
            super().__setattr__(name, value)
            return

        self._d[name] = value


USER_SETTINGS = DictObjectWrapper(getattr(settings, 'SIMPLE_JWT', None))

AUTH_HEADER_TYPES = USER_SETTINGS.AUTH_HEADER_TYPES
if not isinstance(AUTH_HEADER_TYPES, (list, tuple)):
    AUTH_HEADER_TYPES = (AUTH_HEADER_TYPES,)

AUTH_HEADER_TYPE_BYTES = set(
    h.encode(HTTP_HEADER_ENCODING)
    for h in AUTH_HEADER_TYPES
)


class JWTInvalidError(Error):
    default_message = "Token is invalid or expired."
    default_code = "InvalidJWT"
    default_status_code = 401


def make_utc(dt):
    if dt.utcoffset() is None:      # 不带时区
        return dt.replace(tzinfo=utc)

    return dt.astimezone(utc)


def datetime_to_epoch(dt):
    return timegm(dt.utctimetuple())


def datetime_from_epoch(ts):
    return make_utc(datetime.utcfromtimestamp(ts))


ALLOWED_ALGORITHMS = (
    'HS256',
    'HS384',
    'HS512',
    'RS256',
    'RS384',
    'RS512',
)


class TokenBackend:
    def __init__(self, algorithm, signing_key=None, verifying_key=None, audience=None, issuer=None):
        self._validate_algorithm(algorithm)

        self.algorithm = algorithm
        self.signing_key = signing_key
        self.audience = audience
        self.issuer = issuer
        if algorithm.startswith('HS'):
            self.verifying_key = signing_key
        else:
            self.verifying_key = verifying_key

    @staticmethod
    def _validate_algorithm(algorithm):
        """
        Ensure that the nominated algorithm is recognized, and that cryptography is installed for those
        algorithms that require it
        """
        if algorithm not in ALLOWED_ALGORITHMS:
            raise JWTInvalidError(f"Unrecognized algorithm type '{algorithm}'")

        if algorithm in algorithms.requires_cryptography and not algorithms.has_crypto:
            raise JWTInvalidError(f"You must have cryptography installed to use {algorithm}.")

    def encode(self, payload):
        """
        Returns an encoded token for the given payload dictionary.
        """
        jwt_payload = payload.copy()
        if self.audience is not None:
            jwt_payload['aud'] = self.audience
        if self.issuer is not None:
            jwt_payload['iss'] = self.issuer

        token = jwt.encode(jwt_payload, self.signing_key, algorithm=self.algorithm)
        if isinstance(token, bytes):
            # For PyJWT <= 1.7.1
            return token.decode('utf-8')
        # For PyJWT >= 2.0.0a1
        return token

    def decode(self, token, verify=True):
        """
        Performs a validation of the given token and returns its payload
        dictionary.
        Raises a `TokenBackendError` if the token is malformed, if its
        signature check fails, or if its 'exp' claim indicates it has expired.
        """
        try:
            return jwt.decode(token, self.verifying_key, algorithms=[self.algorithm], verify=verify,
                              audience=self.audience, issuer=self.issuer,
                              options={'verify_aud': self.audience is not None})
        except InvalidAlgorithmError as ex:
            raise JWTInvalidError('Invalid algorithm specified') from ex
        except InvalidTokenError:
            raise JWTInvalidError('Token is invalid or expired')


token_backend = TokenBackend(USER_SETTINGS.ALGORITHM, USER_SETTINGS.SIGNING_KEY,
                             USER_SETTINGS.VERIFYING_KEY, USER_SETTINGS.AUDIENCE, USER_SETTINGS.ISSUER)


class Token:
    """
    A class which validates and wraps an existing JWT or can be used to build a
    new JWT.
    """
    token_type = 'access'
    lifetime = timedelta(hours=1, minutes=5)

    def __init__(self, token=None, verify=True):
        """
        !!!! IMPORTANT !!!! MUST raise a TokenError with a user-facing error
        message if the given token is invalid, expired, or otherwise not safe
        to use.
        """
        if self.token_type is None or self.lifetime is None:
            raise JWTInvalidError('Cannot create token with no type or lifetime')

        self.token = token
        self.current_time = make_utc(datetime.utcnow())

        # Set up token
        if token is not None:
            self.payload = token_backend.decode(token, verify=verify)

            if verify:
                self.verify()
        else:
            # New token.  Skip all the verification steps.
            self.payload = {USER_SETTINGS.TOKEN_TYPE_CLAIM: self.token_type}

            # Set "exp" claim with default value
            self.set_exp(from_time=self.current_time, lifetime=self.lifetime)

            # Set "jti" claim
            self.set_jti()

    def __repr__(self):
        return repr(self.payload)

    def __getitem__(self, key):
        return self.payload[key]

    def __setitem__(self, key, value):
        self.payload[key] = value

    def __delitem__(self, key):
        del self.payload[key]

    def __contains__(self, key):
        return key in self.payload

    def get(self, key, default=None):
        return self.payload.get(key, default)

    def __str__(self):
        """
        Signs and returns a token as a base64 encoded string.
        """
        return token_backend.encode(self.payload)

    def verify(self):
        """
        Performs additional validation steps which were not performed when this
        token was decoded.  This method is part of the "public" API to indicate
        the intention that it may be overridden in subclasses.
        """
        self.check_exp()

        # Ensure token id is present
        if USER_SETTINGS.JTI_CLAIM not in self.payload:
            raise JWTInvalidError('Token has no id')

        self.verify_token_type()

    def verify_token_type(self):
        """
        Ensures that the token type claim is present and has the correct value.
        """
        try:
            token_type = self.payload[USER_SETTINGS.TOKEN_TYPE_CLAIM]
        except KeyError:
            raise JWTInvalidError('Token has no type')

        if self.token_type != token_type:
            raise JWTInvalidError('Token has wrong type')

    def set_jti(self):
        """
        Populates the configured jti claim of a token with a string where there
        is a negligible probability that the same string will be chosen at a
        later time.
        See here:
        https://tools.ietf.org/html/rfc7519#section-4.1.7
        """
        self.payload[USER_SETTINGS.JTI_CLAIM] = uuid4().hex

    def set_exp(self, claim='exp', from_time=None, lifetime=None):
        """
        Updates the expiration time of a token.
        """
        if from_time is None:
            from_time = self.current_time

        if lifetime is None:
            lifetime = self.lifetime

        self.payload[claim] = datetime_to_epoch(from_time + lifetime)

    def check_exp(self, claim='exp', current_time=None):
        """
        Checks whether a timestamp value in the given claim has passed (since
        the given datetime value in `current_time`).  Raises a TokenError with
        a user-facing error message if so.
        """
        if current_time is None:
            current_time = self.current_time

        try:
            claim_value = self.payload[claim]
        except KeyError:
            raise JWTInvalidError(f"Token has no '{claim}' claim")

        claim_time = datetime_from_epoch(claim_value)
        if claim_time <= current_time:
            raise JWTInvalidError(f"Token '{claim}' claim has expired")

    @classmethod
    def for_user(cls, user):
        """
        Returns an authorization token for the given user that will be provided
        after authenticating the user's credentials.
        """
        user_id = getattr(user, USER_SETTINGS.USER_ID_FIELD)
        if not isinstance(user_id, int):
            user_id = str(user_id)

        token = cls()
        token[USER_SETTINGS.USER_ID_CLAIM] = user_id

        return token


class JWTAuthentication(authentication.BaseAuthentication):
    """
    An authentication plugin that authenticates requests through a JSON web
    token provided in a request header.
    """
    www_authenticate_realm = 'api'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_model = get_user_model()

    def authenticate(self, request):
        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)

        return self.get_user(validated_token), validated_token

    def authenticate_header(self, request):
        return '{0} realm="{1}"'.format(
            AUTH_HEADER_TYPES[0],
            self.www_authenticate_realm,
        )

    @staticmethod
    def get_header(request):
        """
        Extracts the header containing the JSON web token from the given
        request.
        """
        header = request.META.get(USER_SETTINGS.AUTH_HEADER_NAME)

        if isinstance(header, str):
            # Work around django test client oddness
            header = header.encode(HTTP_HEADER_ENCODING)

        return header

    @staticmethod
    def get_raw_token(header):
        """
        Extracts an unvalidated JSON web token from the given "Authorization"
        header value.
        """
        parts = header.split()

        if len(parts) == 0:
            # Empty AUTHORIZATION header sent
            return None

        if parts[0] not in AUTH_HEADER_TYPE_BYTES:
            # Assume the header does not contain a JSON web token
            return None

        if len(parts) != 2:
            raise AuthenticationFailed(
                'Authorization header must contain two space-delimited values',
                code='bad_authorization_header',
            )

        return parts[1]

    @staticmethod
    def get_validated_token(raw_token):
        """
        Validates an encoded JSON web token and returns a validated token
        wrapper object.
        """
        try:
            return Token(raw_token)
        except JWTInvalidError as e:
            extend_msg = f'token_class={Token.__name__}, token_type={Token.token_type}, message={e.args[0]}'
            raise JWTInvalidError(message='Given token not valid for any token type', extend_msg=extend_msg)

    def get_user(self, validated_token):
        """
        Attempts to find and return a user using the given validated token.
        """
        try:
            user_id = validated_token[USER_SETTINGS.USER_ID_CLAIM]
        except KeyError:
            raise JWTInvalidError('Token contained no recognizable user identification')

        try:
            user = self.user_model.objects.get(**{USER_SETTINGS.USER_ID_FIELD: user_id})
        except self.user_model.DoesNotExist:
            raise AuthenticationFailed('User not found', code='user_not_found')

        if not user.is_active:
            raise AuthenticationFailed('User is inactive', code='user_inactive')

        return user


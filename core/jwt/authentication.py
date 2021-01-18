from django.utils.translation import gettext as _
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed


User = get_user_model()


class CreateUserJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        """
        Attempts to find or creat and return a user using the given validated token.
        """
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
        except KeyError:
            raise InvalidToken(_('Token contained no recognizable user identification'))

        params = {api_settings.USER_ID_FIELD: user_id}
        try:
            user = User.objects.get(**params)
        except User.DoesNotExist:
            params.update({'email': user_id, 'first_name': '', 'last_name': ''})
            user = User(**params)
            try:
                user.save()
            except Exception as e:
                raise AuthenticationFailed(_('User create failed') + f';error: {str(e)}', code='user_create_failed')

        if not user.is_active:
            raise AuthenticationFailed(_('User is inactive'), code='user_inactive')

        return user

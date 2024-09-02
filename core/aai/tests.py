from datetime import datetime, timedelta, timezone

from django.test import TestCase
from django.http.request import HttpRequest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from apps.users.models import UserProfile
from apps.app_global.models import GlobalConfig
from . import jwt
from .authentication import CreateUserJWTAuthentication, JWTInvalidError

utc = timezone.utc


class TimeTestCase(TestCase):
    def test_make_utc(self):
        dt1 = datetime.now()
        dt2 = jwt.make_utc(dt1)
        self.assertEqual(dt2.tzinfo, utc, msg='not utc time')

        dt1 = datetime.now(tz=timezone(offset=-timedelta(hours=8), name='Asia/Shanghai'))
        dt2 = jwt.make_utc(dt1)
        self.assertEqual(dt2.tzinfo, utc, msg='not utc time')
        self.assertEqual(dt2, dt1, msg='time not equal after make_utc()')


class JWTTestCase(TestCase):
    token = ''

    def setUp(self):
        self.rsa = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        bytes_private_key = self.rsa.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        self.private_key = bytes_private_key.decode('utf-8')
        self.public_rsa = self.rsa.public_key()
        bytes_public_key = self.public_rsa.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        self.public_key = bytes_public_key.decode('utf-8')

    def test_jwt(self):
        token = 'test'
        request = HttpRequest()
        request.META = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        with self.assertRaises(JWTInvalidError):
            CreateUserJWTAuthentication().authenticate(request=request)

        token = self.token
        if not self.token:
            return

        request = HttpRequest()
        request.META = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        user, t = CreateUserJWTAuthentication().authenticate(request=request)
        print(t.payload)
        u = UserProfile.objects.first()
        self.assertEqual(u.id, t.payload['id'])
        print(f'user id={u.id}, name={u.username}')

    def test_jwt_token_backend(self):
        token_backend = jwt.TokenBackend(
            algorithm='RS512', signing_key=self.private_key, verifying_key=self.public_key,
            audience=None, issuer=None
        )
        token = token_backend.encode(
            payload={'username': 'test', 'company': 'cnic', 'age': 18},
            headers={'header1': 'header'}
        )
        r = token_backend.decode(token=token, verify_signature=True)
        payload = r['payload']
        headers = r['header']
        self.assertEqual(payload['username'], 'test')
        self.assertEqual(payload['company'], 'cnic')
        self.assertEqual(payload['age'], 18)
        self.assertEqual(headers['header1'], 'header')

    def test_token(self):
        token_backend = jwt.TokenBackend(
            algorithm='RS512', signing_key=self.private_key, verifying_key=self.public_key,
            audience=None, issuer=None
        )
        token1 = jwt.Token(token=None, backend=token_backend)
        token1['username'] = 'test'
        token = str(token1)
        token2 = jwt.Token(token=token, backend=token_backend)
        self.assertEqual(token2["username"], 'test')

        obj = GlobalConfig(
            name=GlobalConfig.ConfigName.AAI_JWT_VERIFYING_KEY.value,
            value=self.public_key, remark=''
        )
        obj.save(force_insert=True)
        jwt.global_configs.clear_cache()
        token3 = jwt.Token(token=token)
        self.assertEqual(token3["username"], 'test')
        obj.delete()

    def test_sha256_rsa2048(self):
        from utils.crypto.rsa import SHA256WithRSA
        rsa = SHA256WithRSA(private_key=self.private_key, public_key=self.public_key)
        data = '1234abcd二位分为。xx'.encode(encoding='utf-8')
        signature = rsa.sign(data=data)
        rsa.verify(signature=signature, data=data)

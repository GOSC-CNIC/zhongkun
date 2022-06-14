from urllib import parse
import json

from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from api.signers import SignatureRequest, SignatureResponse
from bill.models import PayApp
from . import MyAPITestCase


class TradeTestTests(MyAPITestCase):
    def setUp(self):
        user_rsa = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        bytes_private_key = user_rsa.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        self.user_private_key = bytes_private_key.decode('utf-8')
        public_rsa = user_rsa.public_key()
        bytes_public_key = public_rsa.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        self.user_public_key = bytes_public_key.decode('utf-8')
        self.app = PayApp(
            name='APP name', app_url='', app_desc='test', rsa_public_key=self.user_public_key,
            status=PayApp.Status.UNAUDITED.value
        )
        self.app.save(force_insert=True)

        self.vms_public_key = settings.PAYMENT_RSA2048['public_key']

    def test_trade_test(self):
        body = {
            'a': 1,
            'b': 'test',
            'c': '测试'
        }
        params = {
            'param1': 'test param1',
            'param2': '参数2',
            'param3': 66
        }
        base_url = reverse('api:trade-test-list')
        query_str = parse.urlencode(params)
        url = f'{base_url}?{query_str}'
        body_json = json.dumps(body)
        token = SignatureRequest.built_token(
            app_id=self.app.id,
            method='POST',
            uri=url,
            body=body_json,
            private_key=self.user_private_key
        )
        headers = {'HTTP_AUTHORIZATION': f'{SignatureRequest.SING_TYPE} ' + token}

        # app status unaudited
        r = self.client.post(url, data=body_json, content_type='application/json', **headers)
        self.assertErrorResponse(status_code=409, code='AppStatusUnaudited', response=r)

        # app status ban
        self.app.status = PayApp.Status.BAN.value
        self.app.save(update_fields=['status'])
        r = self.client.post(url, data=body_json, content_type='application/json', **headers)
        self.assertErrorResponse(status_code=409, code='AppStatusBan', response=r)

        # app status ok
        self.app.status = PayApp.Status.NORMAL.value
        self.app.save(update_fields=['status'])
        r = self.client.post(url, data=body_json, content_type='application/json', **headers)
        self.assertEqual(r.status_code, 200)
        r_body: bytes = r.rendered_content
        timestamp = int(r['Pay-Timestamp'])
        now_timestamp = int(timezone.now().timestamp())
        self.assertLess(abs(now_timestamp - timestamp), 60)
        signature = r['Pay-Signature']
        sign_type = r['Pay-Sign-Type']
        parts = [sign_type, str(timestamp), r_body.decode('utf-8')]
        data = '\n'.join(parts)
        ok = SignatureResponse.verify(data.encode('utf-8'), sig=signature, public_key=self.vms_public_key)
        self.assertIs(ok, True)
        self.assertEqual(r.data, body)

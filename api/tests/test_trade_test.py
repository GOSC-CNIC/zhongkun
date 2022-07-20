from urllib import parse
import json
from datetime import timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from jwt import PyJWT

from api.signers import SignatureRequest, SignatureResponse
from bill.models import PayApp, PayOrgnazition, PayAppService, PaymentHistory, CashCoupon
from bill.managers.payment import PaymentManager
from utils.test import get_or_create_user
from utils.model import OwnerType
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
            'param3': 66,
            'sign': 'test sign'
        }
        base_url = reverse('api:trade-test-list')
        query_str = parse.urlencode(params)
        url = f'{base_url}?{query_str}'
        body_json = json.dumps(body)
        params.pop('sign', None)
        token = SignatureRequest.built_token(
            app_id=self.app.id,
            method='POST',
            uri=parse.unquote(base_url),
            querys=params,
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


class TradeTests(MyAPITestCase):
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
            status=PayApp.Status.NORMAL.value
        )
        self.app.save(force_insert=True)

        self.vms_public_key = settings.PAYMENT_RSA2048['public_key']

        # 余额支付有关配置
        self.po = PayOrgnazition(name='机构')
        self.po.save()
        app_service1 = PayAppService(
            id='123', name='service1', app=self.app, orgnazition=self.po
        )
        app_service1.save()
        self.app_service1 = app_service1
        self.user = get_or_create_user(username='lilei@xx.com')

    @staticmethod
    def get_aai_jwt_rsa_key():
        rs512 = rsa.generate_private_key(public_exponent=65537, key_size=1024)
        bytes_private_key = rs512.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        rs512_private_key = bytes_private_key.decode('utf-8')
        public_rsa = rs512.public_key()
        bytes_public_key = public_rsa.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        rs512_public_key = bytes_public_key.decode('utf-8')
        return rs512_private_key, rs512_public_key

    def get_aai_jwt(self, rs512_private_key: str, now_timestamp: int = None):
        algorithm = 'RS512'
        headers = {
            'type': 'accessToken',
            'typ': 'JWT',
            'alg': algorithm
        }
        if now_timestamp is None:
            st_now = int(timezone.now().timestamp())
        else:
            st_now = now_timestamp

        st_delta = int(timedelta(minutes=15).total_seconds())
        payload = {
            'name': '李雷',
            'email': self.user.username,
            'orgName': 'cnic',
            'country': None,
            'voJson': None,
            'id': 'testid',
            'exp': st_now + st_delta,
            'iss': 2,
            'iat': st_now
        }
        jwtoken = PyJWT().encode(
            payload=payload,
            key=rs512_private_key,
            algorithm=algorithm,
            headers=headers
        )
        return jwtoken

    def do_request(self, method: str, base_url: str, body: dict, params: dict):
        query_str = parse.urlencode(params)
        url = f'{base_url}?{query_str}'
        if body:
            body_json = json.dumps(body)
        else:
            body_json = ''

        params.pop('sign', None)
        token = SignatureRequest.built_token(
            app_id=self.app.id,
            method=method.upper(),
            uri=parse.unquote(base_url),
            querys=params,
            body=body_json,
            private_key=self.user_private_key
        )
        headers = {'HTTP_AUTHORIZATION': f'{SignatureRequest.SING_TYPE} ' + token}
        func = getattr(self.client, method.lower())
        r = func(url, data=body_json, content_type='application/json', **headers)
        return r

    def response_sign_assert(self, r):
        """
        响应验签
        """
        r_body: bytes = r.rendered_content
        timestamp = int(r['Pay-Timestamp'])
        signature = r['Pay-Signature']
        sign_type = r['Pay-Sign-Type']
        parts = [sign_type, str(timestamp), r_body.decode('utf-8')]
        data = '\n'.join(parts)
        ok = SignatureResponse.verify(data.encode('utf-8'), sig=signature, public_key=self.vms_public_key)
        self.assertIs(ok, True)

    def test_trade_pay(self):
        rs512_private_key, rs512_public_key = self.get_aai_jwt_rsa_key()
        aai_jwt = self.get_aai_jwt(rs512_private_key)
        from core.jwt import jwt
        jwt.token_backend.verifying_key = rs512_public_key

        body = {
            'subject': 'pay test',
            'order_id': 'order_id1',
            'amounts': '6.66',
            'app_service_id': self.app_service1.id,
            'aai_jwt': aai_jwt,
            'remark': 'test remark'
        }
        params = {}
        base_url = reverse('api:trade-pay')
        r = self.do_request(method='post', base_url=base_url, body=body, params=params)
        self.assertErrorResponse(status_code=409, code='BalanceNotEnough', response=r)

        ts = int(timezone.now().timestamp())
        ts -= int(timedelta(hours=1).total_seconds())
        expired_aai_jwt = self.get_aai_jwt(rs512_private_key, now_timestamp=ts)
        body['aai_jwt'] = expired_aai_jwt
        r = self.do_request(method='post', base_url=base_url, body=body, params=params)
        self.assertErrorResponse(status_code=400, code='InvalidJWT', response=r)

        body['aai_jwt'] = aai_jwt
        r = self.do_request(method='post', base_url=base_url, body=body, params=params)
        self.assertErrorResponse(status_code=409, code='BalanceNotEnough', response=r)

        body['amounts'] = '1.234'
        r = self.do_request(method='post', base_url=base_url, body=body, params=params)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=r)

        body['amounts'] = '-1.23'
        r = self.do_request(method='post', base_url=base_url, body=body, params=params)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=r)

        body['amounts'] = '123456789.99'
        r = self.do_request(method='post', base_url=base_url, body=body, params=params)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=r)

        body['amounts'] = '99999999.99'
        r = self.do_request(method='post', base_url=base_url, body=body, params=params)
        self.assertErrorResponse(status_code=409, code='BalanceNotEnough', response=r)
        self.response_sign_assert(r)

        userpointaccount = PaymentManager().get_user_point_account(user_id=self.user.id)
        userpointaccount.balance = Decimal('100')
        userpointaccount.save(update_fields=['balance'])

        body['amounts'] = '1.99'
        r = self.do_request(method='post', base_url=base_url, body=body, params=params)
        self.assertEqual(r.status_code, 200)
        self.response_sign_assert(r)
        userpointaccount.refresh_from_db()
        self.assertEqual(userpointaccount.balance, Decimal('98.01'))
        self.assertKeysIn(keys=[
            'id', 'subject', 'payment_method', 'executor', 'payer_id', 'payer_name', 'payer_type', 'amounts',
            'coupon_amount', 'payment_time', 'type', 'remark', 'order_id', 'app_id', 'app_service_id'
        ], container=r.data)
        self.assert_is_subdict_of(sub={
            "subject": body['subject'], "payment_method": PaymentHistory.PaymentMethod.BALANCE.value,
            "payer_id": self.user.id, "payer_name": self.user.username, "payer_type": "user",
            "amounts": "-1.99", "coupon_amount": "0.00", "type": PaymentHistory.Type.PAYMENT.value,
            "remark": body['remark'], "order_id": body['order_id'], "app_id": self.app.id,
            "app_service_id": self.app_service1.id
        }, d=r.data)

        r = self.do_request(method='post', base_url=base_url, body=body, params=params)
        self.assertErrorResponse(status_code=409, code='OrderIdExist', response=r)

        body['amounts'] = '200'
        body['order_id'] = 'orderid2'
        r = self.do_request(method='post', base_url=base_url, body=body, params=params)
        self.assertErrorResponse(status_code=409, code='BalanceNotEnough', response=r)

        # 有效
        now_time = timezone.now()
        coupon1_user = CashCoupon(
            face_value=Decimal('50'),
            balance=Decimal('50'),
            effective_time=now_time - timedelta(days=1),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=self.app_service1.id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id, vo_id=None
        )
        coupon1_user.save(force_insert=True)

        # 无效
        coupon2_user = CashCoupon(
            face_value=Decimal('100'),
            balance=Decimal('100'),
            effective_time=now_time + timedelta(days=2),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=self.app_service1.id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id, vo_id=None
        )
        coupon2_user.save(force_insert=True)

        r = self.do_request(method='post', base_url=base_url, body=body, params=params)
        self.assertErrorResponse(status_code=409, code='BalanceNotEnough', response=r)

        # 有效
        coupon2_user = CashCoupon(
            face_value=Decimal('100'),
            balance=Decimal('100'),
            effective_time=now_time - timedelta(days=2),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=self.app_service1.id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id, vo_id=None
        )
        coupon2_user.save(force_insert=True)

        r = self.do_request(method='post', base_url=base_url, body=body, params=params)
        self.assertEqual(r.status_code, 200)
        self.response_sign_assert(r)
        self.assertKeysIn(keys=[
            'id', 'subject', 'payment_method', 'executor', 'payer_id', 'payer_name', 'payer_type', 'amounts',
            'coupon_amount', 'payment_time', 'type', 'remark', 'order_id', 'app_id', 'app_service_id'
        ], container=r.data)
        self.assert_is_subdict_of(sub={
            "subject": body['subject'], "payment_method": PaymentHistory.PaymentMethod.BALANCE_COUPON.value,
            "payer_id": self.user.id, "payer_name": self.user.username, "payer_type": "user",
            "amounts": "-50.00", "coupon_amount": "-150.00", "type": PaymentHistory.Type.PAYMENT.value,
            "remark": body['remark'], "order_id": body['order_id'], "app_id": self.app.id,
            "app_service_id": self.app_service1.id
        }, d=r.data)
        userpointaccount.refresh_from_db()
        self.assertEqual(userpointaccount.balance, Decimal('48.01'))

        # test query by id
        trade_id = r.data['id']
        url = reverse('api:trade-query-trade-id', kwargs={'trade_id': 'notfound'})
        response = self.do_request(method='get', base_url=url, body={}, params={})
        self.assertErrorResponse(status_code=404, code='NoSuchTrade', response=response)
        url = reverse('api:trade-query-trade-id', kwargs={'trade_id': trade_id})
        response = self.do_request(method='get', base_url=url, body={}, params={})
        self.assertEqual(response.status_code, 200)
        self.response_sign_assert(response)
        self.assertKeysIn(keys=[
            'id', 'subject', 'payment_method', 'executor', 'payer_id', 'payer_name', 'payer_type', 'amounts',
            'coupon_amount', 'payment_time', 'type', 'remark', 'order_id', 'app_id', 'app_service_id'
        ], container=response.data)

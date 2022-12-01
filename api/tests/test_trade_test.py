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
from bill.models import (
    PayApp, PayOrgnazition, PayAppService, PaymentHistory, CashCoupon, RefundRecord,
    TransactionBill
)
from bill.managers.payment import PaymentManager
from utils.test import get_or_create_user
from utils.model import OwnerType
from vo.models import VirtualOrganization
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

    def _query_trade_test(self, trade_id: str, order_id: str):
        # test query by id
        url = reverse('api:trade-query-trade-id', kwargs={'trade_id': 'notfound'})
        response = self.do_request(method='get', base_url=url, body={}, params={})
        self.assertErrorResponse(status_code=404, code='NoSuchTrade', response=response)
        url = reverse('api:trade-query-trade-id', kwargs={'trade_id': trade_id})
        response = self.do_request(method='get', base_url=url, body={}, params={})
        self.assertEqual(response.status_code, 200)
        self.response_sign_assert(response)
        self.assertKeysIn(keys=[
            'id', 'subject', 'payment_method', 'executor', 'payer_id', 'payer_name', 'payer_type', 'amounts',
            'coupon_amount', 'payment_time', 'remark', 'order_id', 'app_id', 'app_service_id',
            "status", 'status_desc', 'creation_time', 'payable_amounts'
        ], container=response.data)

        # test query by order id
        url = reverse('api:trade-query-order-id', kwargs={'order_id': 'notfound'})
        response = self.do_request(method='get', base_url=url, body={}, params={})
        self.assertErrorResponse(status_code=404, code='NoSuchTrade', response=response)
        url = reverse('api:trade-query-order-id', kwargs={'order_id': order_id})
        response = self.do_request(method='get', base_url=url, body={}, params={})
        self.assertEqual(response.status_code, 200)
        self.response_sign_assert(response)
        self.assertKeysIn(keys=[
            'id', 'subject', 'payment_method', 'executor', 'payer_id', 'payer_name', 'payer_type', 'amounts',
            'coupon_amount', 'payment_time', 'remark', 'order_id', 'app_id', 'app_service_id',
            "status", 'status_desc', 'creation_time', 'payable_amounts'
        ], container=response.data)

    def _charge_ok_test(self, base_url: str, body: dict, params: dict):
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
            'coupon_amount', 'payment_time', 'remark', 'order_id', 'app_id', 'app_service_id',
            "status", 'status_desc', 'creation_time', 'payable_amounts'
        ], container=r.data)
        self.assert_is_subdict_of(sub={
            "subject": body['subject'], "payment_method": PaymentHistory.PaymentMethod.BALANCE.value,
            "payer_id": self.user.id, "payer_name": self.user.username, "payer_type": "user",
            "amounts": "-1.99", "coupon_amount": "0.00", "status": PaymentHistory.Status.SUCCESS.value,
            "remark": body['remark'], "order_id": body['order_id'], "app_id": self.app.id,
            "app_service_id": self.app_service1.id, 'payable_amounts': '1.99'
        }, d=r.data)

        r = self.do_request(method='post', base_url=base_url, body=body, params=params)
        self.assertErrorResponse(status_code=409, code='OrderIdExist', response=r)

        order_id2 = 'orderid2'
        body['amounts'] = '200'
        body['order_id'] = order_id2
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
            'coupon_amount', 'payment_time', 'remark', 'order_id', 'app_id', 'app_service_id',
            "status", 'status_desc', 'creation_time', 'payable_amounts'
        ], container=r.data)
        self.assert_is_subdict_of(sub={
            "subject": body['subject'], "payment_method": PaymentHistory.PaymentMethod.BALANCE_COUPON.value,
            "payer_id": self.user.id, "payer_name": self.user.username, "payer_type": "user",
            "amounts": "-50.00", "coupon_amount": "-150.00", "status": PaymentHistory.Status.SUCCESS.value,
            "remark": body['remark'], "order_id": body['order_id'], "app_id": self.app.id,
            "app_service_id": self.app_service1.id, 'payable_amounts': '200.00'
        }, d=r.data)
        userpointaccount.refresh_from_db()
        self.assertEqual(userpointaccount.balance, Decimal('48.01'))
        trade_id = r.data['id']
        return trade_id, order_id2

    def test_trade_charge_jwt(self):
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
        base_url = reverse('api:trade-charge-jwt')
        r = self.do_request(method='post', base_url=base_url, body=body, params=params)
        self.assertErrorResponse(status_code=409, code='BalanceNotEnough', response=r)

        ts = int(timezone.now().timestamp())
        ts -= int(timedelta(hours=1).total_seconds())
        expired_aai_jwt = self.get_aai_jwt(rs512_private_key, now_timestamp=ts)
        body['aai_jwt'] = expired_aai_jwt
        r = self.do_request(method='post', base_url=base_url, body=body, params=params)
        self.assertErrorResponse(status_code=400, code='InvalidJWT', response=r)

        body['aai_jwt'] = aai_jwt
        trade_id, order_id = self._charge_ok_test(base_url=base_url, body=body, params=params)
        self._query_trade_test(trade_id=trade_id, order_id=order_id)

    def test_trade_charge_account(self):
        body = {
            'subject': 'pay test',
            'order_id': 'order_id1',
            'amounts': '6.66',
            'app_service_id': self.app_service1.id,
            'username': 'notfount',
            'remark': 'test remark'
        }
        params = {}
        base_url = reverse('api:trade-charge-account')
        r = self.do_request(method='post', base_url=base_url, body=body, params=params)
        self.assertErrorResponse(status_code=404, code='NoSuchBalanceAccount', response=r)

        body['username'] = self.user.username
        trade_id, order_id = self._charge_ok_test(base_url=base_url, body=body, params=params)
        self._query_trade_test(trade_id=trade_id, order_id=order_id)


class TradeSignKeyTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(username='tom@cnic.cn')

    def test_rsa_key_generate(self):
        base_url = reverse('api:trade-signkey-public-key')
        r = self.client.get(base_url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['public_key'], container=r.data)


class RefundRecordTests(MyAPITestCase):
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

    @staticmethod
    def do_request(client, app_id: str, private_key: str, method: str, base_url: str, body: dict, params: dict):
        query_str = parse.urlencode(params)
        url = f'{base_url}?{query_str}'
        if body:
            body_json = json.dumps(body)
        else:
            body_json = ''

        params.pop('sign', None)
        token = SignatureRequest.built_token(
            app_id=app_id,
            method=method.upper(),
            uri=parse.unquote(base_url),
            querys=params,
            body=body_json,
            private_key=private_key
        )
        headers = {'HTTP_AUTHORIZATION': f'{SignatureRequest.SING_TYPE} ' + token}
        func = getattr(client, method.lower())
        r = func(url, data=body_json, content_type='application/json', **headers)
        return r

    def test_refund(self):
        user = get_or_create_user(username='lilei@cnic.cn')
        # 创建用户账户，否者退款失败
        PaymentManager.get_user_point_account(user_id=user.id, is_create=True)
        payment1 = PaymentHistory(
            payment_account='',
            payment_method=PaymentHistory.PaymentMethod.BALANCE_COUPON.value,
            executor='executor',
            payer_id=user.id,
            payer_name=user.username,
            payer_type=OwnerType.USER.value,
            payable_amounts=Decimal('100.00'),
            amounts=Decimal('-60.00'),
            coupon_amount=Decimal('-40.00'),
            status=PaymentHistory.Status.SUCCESS.value,
            status_desc='支付成功',
            remark='remark',
            order_id='order_id',
            app_service_id='',
            instance_id='',
            app_id=self.app.id,
            subject='subject',
            creation_time=timezone.now(),
            payment_time=timezone.now()
        )
        payment1.save(force_insert=True)

        body = {
            "out_refund_id": 'out_refund_id',
            "trade_id": payment1.id,
            # "out_order_id": "string",
            "refund_amount": "10",
            "refund_reason": "reason1",
            "remark": "remark1"
        }
        base_url = reverse('api:trade-refund-list')

        # AppStatusUnaudited
        r = self.do_request(client=self.client, app_id=self.app.id, private_key=self.user_private_key,
                            method='post', base_url=base_url, body=body, params={})
        self.assertErrorResponse(status_code=409, code='AppStatusUnaudited', response=r)

        # set app normal
        self.app.status = PayApp.Status.NORMAL.value
        self.app.save(update_fields=['status'])

        # InvalidSignature
        r = self.do_request(client=self.client, app_id=self.app.id, private_key=self.user_private_key,
                            method='post', base_url=f'{base_url}?a=1', body=body, params={})
        self.assertErrorResponse(status_code=401, code='InvalidSignature', response=r)

        # MissingTradeId
        data = body.copy()
        data.pop('trade_id', None)
        data.pop('out_order_id', None)
        r = self.do_request(client=self.client, app_id=self.app.id, private_key=self.user_private_key,
                            method='post', base_url=base_url, body=data, params={})
        self.assertErrorResponse(status_code=400, code='MissingTradeId', response=r)

        # InvalidRefundAmount
        data = body.copy()
        data['refund_amount'] = '-1'
        r = self.do_request(client=self.client, app_id=self.app.id, private_key=self.user_private_key,
                            method='post', base_url=base_url, body=data, params={})
        self.assertErrorResponse(status_code=400, code='InvalidRefundAmount', response=r)

        # NoSuchTrade
        no_trade_data = body.copy()
        no_trade_data['trade_id'] = 'notfound'
        r = self.do_request(client=self.client, app_id=self.app.id, private_key=self.user_private_key,
                            method='post', base_url=base_url, body=no_trade_data, params={})
        self.assertErrorResponse(status_code=404, code='NoSuchTrade', response=r)

        # ok, 10 = 6 + 4, balance + 6.00
        out_refund_id1 = 'out_refund_id1'
        body = {
            "out_refund_id": out_refund_id1,
            "trade_id": payment1.id,
            # "out_order_id": "string",
            "refund_amount": "10",
            "refund_reason": "reason1",
            "remark": "remark1"
        }
        r = self.do_request(client=self.client, app_id=self.app.id, private_key=self.user_private_key,
                            method='post', base_url=base_url, body=body, params={})
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'trade_id', 'out_order_id', 'out_refund_id', 'refund_reason', 'total_amounts',
            'refund_amounts', 'real_refund', 'coupon_refund', 'creation_time', 'success_time',
            'status', 'status_desc', 'remark', 'owner_id', 'owner_name', 'owner_type'
        ], container=r.data)
        self.assert_is_subdict_of(sub={
            'trade_id': payment1.id, 'out_order_id': payment1.order_id, 'out_refund_id': out_refund_id1,
            'refund_reason': body['refund_reason'], 'total_amounts': '100.00', 'refund_amounts': '10.00',
            'real_refund': '6.00', 'coupon_refund': '4.00', 'status': RefundRecord.Status.SUCCESS.value,
            'remark': body['remark'], 'owner_id': payment1.payer_id, 'owner_type': payment1.payer_type
        }, d=r.data)
        trade_refund_id = r.data['id']
        # 确认余额
        user.userpointaccount.refresh_from_db()
        self.assertEqual(user.userpointaccount.balance, Decimal('6'))

        # 退款记录确认
        refund: RefundRecord = RefundRecord.objects.filter(id=trade_refund_id).first()
        self.assertEqual(refund.app_id, self.app.id)
        self.assertEqual(refund.out_order_id, payment1.order_id)
        self.assertEqual(refund.out_refund_id, out_refund_id1)
        self.assertEqual(refund.refund_amounts, Decimal('10'))
        self.assertEqual(refund.total_amounts, Decimal('100'))
        self.assertEqual(refund.real_refund, Decimal('6'))
        self.assertEqual(refund.coupon_refund, Decimal('4'))
        self.assertEqual(refund.status, RefundRecord.Status.SUCCESS.value)
        self.assertEqual(refund.owner_id, payment1.payer_id)
        self.assertEqual(refund.owner_type, payment1.payer_type)
        self.assertEqual(refund.in_account, user.userpointaccount.id)

        # 交易流水确认
        bill: TransactionBill = TransactionBill.objects.filter(
            trade_id=trade_refund_id, trade_type=TransactionBill.TradeType.REFUND.value).first()
        self.assertEqual(bill.subject, refund.refund_reason)
        self.assertEqual(bill.account, refund.in_account)
        self.assertEqual(bill.app_service_id, refund.app_service_id)
        self.assertEqual(bill.app_id, self.app.id)
        self.assertEqual(bill.amounts, Decimal('6'))
        self.assertEqual(bill.coupon_amount, Decimal('0'))
        self.assertEqual(bill.after_balance, user.userpointaccount.balance)
        self.assertEqual(bill.owner_id, payment1.payer_id)
        self.assertEqual(bill.owner_type, OwnerType.USER.value)

        # ok, balance + 0.01
        out_refund_id2 = 'out_refund_id2'
        body = {
            "out_refund_id": out_refund_id2,
            "out_order_id": payment1.order_id,
            "refund_amount": "0.01",
            "refund_reason": "reason好久2",
            "remark": "remark回来3"
        }
        r = self.do_request(client=self.client, app_id=self.app.id, private_key=self.user_private_key,
                            method='post', base_url=base_url, body=body, params={})
        self.assertEqual(r.status_code, 200)
        self.assert_is_subdict_of(sub={
            'trade_id': payment1.id, 'out_order_id': payment1.order_id, 'out_refund_id': out_refund_id2,
            'refund_reason': body['refund_reason'], 'total_amounts': '100.00', 'refund_amounts': '0.01',
            'real_refund': '0.01', 'coupon_refund': '0.00', 'status': RefundRecord.Status.SUCCESS.value,
            'remark': body['remark'], 'owner_id': payment1.payer_id, 'owner_type': payment1.payer_type
        }, d=r.data)
        trade_refund_id2 = r.data['id']
        # 确认余额
        user.userpointaccount.refresh_from_db()
        self.assertEqual(user.userpointaccount.balance, Decimal('6.01'))

        # 退款记录确认
        refund: RefundRecord = RefundRecord.objects.filter(id=trade_refund_id2).first()
        self.assertEqual(refund.out_order_id, payment1.order_id)
        self.assertEqual(refund.out_refund_id, out_refund_id2)
        self.assertEqual(refund.total_amounts, Decimal('100'))
        self.assertEqual(refund.refund_amounts, Decimal('0.01'))
        self.assertEqual(refund.real_refund, Decimal('0.01'))
        self.assertEqual(refund.coupon_refund, Decimal('0'))
        self.assertEqual(refund.status, RefundRecord.Status.SUCCESS.value)
        self.assertEqual(refund.owner_id, payment1.payer_id)
        self.assertEqual(refund.owner_type, payment1.payer_type)
        self.assertEqual(refund.in_account, user.userpointaccount.id)

        # 交易流水确认
        bill: TransactionBill = TransactionBill.objects.filter(
            trade_id=trade_refund_id2, trade_type=TransactionBill.TradeType.REFUND.value).first()
        self.assertEqual(bill.subject, refund.refund_reason)
        self.assertEqual(bill.account, refund.in_account)
        self.assertEqual(bill.app_service_id, refund.app_service_id)
        self.assertEqual(bill.app_id, self.app.id)
        self.assertEqual(bill.amounts, Decimal('0.01'))
        self.assertEqual(bill.coupon_amount, Decimal('0'))
        self.assertEqual(bill.after_balance, user.userpointaccount.balance)
        self.assertEqual(bill.owner_id, payment1.payer_id)
        self.assertEqual(bill.owner_type, OwnerType.USER.value)

        # RefundAmountsExceedTotal
        body = {
            "out_refund_id": 'tetsssfaho',
            "out_order_id": payment1.order_id,
            "refund_amount": "90",
            "refund_reason": "reason好久2",
            "remark": "remark回来3"
        }
        r = self.do_request(client=self.client, app_id=self.app.id, private_key=self.user_private_key,
                            method='post', base_url=base_url, body=body, params={})
        self.assertErrorResponse(status_code=409, code='RefundAmountsExceedTotal', response=r)

        # OutRefundIdExists
        body = {
            "out_refund_id": out_refund_id2,
            "out_order_id": payment1.order_id,
            "refund_amount": "6.66",
            "refund_reason": "reason好久2",
            "remark": "remark回来3"
        }
        r = self.do_request(client=self.client, app_id=self.app.id, private_key=self.user_private_key,
                            method='post', base_url=base_url, body=body, params={})
        self.assertErrorResponse(status_code=409, code='OutRefundIdExists', response=r)

        # --- only coupon ---
        payment2 = PaymentHistory(
            payment_account='',
            payment_method=PaymentHistory.PaymentMethod.CASH_COUPON.value,
            executor='executor',
            payer_id=user.id,
            payer_name=user.username,
            payer_type=OwnerType.USER.value,
            payable_amounts=Decimal('66.00'),
            amounts=Decimal('0.00'),
            coupon_amount=Decimal('-66.00'),
            status=PaymentHistory.Status.SUCCESS.value,
            status_desc='支付成功',
            remark='remark',
            order_id='order_id2',
            app_service_id='',
            instance_id='',
            app_id=self.app.id,
            subject='subject',
            creation_time=timezone.now(),
            payment_time=timezone.now()
        )
        payment2.save(force_insert=True)

        # ok, balance + 0.00
        out_refund_id3 = 'out_refund_id_balance2'
        body = {
            "out_refund_id": out_refund_id3,
            "out_order_id": payment2.order_id,
            "refund_amount": "0.02",
            "refund_reason": "reason好久2",
            "remark": "remark回来3"
        }
        r = self.do_request(client=self.client, app_id=self.app.id, private_key=self.user_private_key,
                            method='post', base_url=base_url, body=body, params={})
        self.assertEqual(r.status_code, 200)
        self.assert_is_subdict_of(sub={
            'trade_id': payment2.id, 'out_order_id': payment2.order_id, 'out_refund_id': out_refund_id3,
            'refund_reason': body['refund_reason'], 'total_amounts': '66.00', 'refund_amounts': '0.02',
            'real_refund': '0.00', 'coupon_refund': '0.02', 'status': RefundRecord.Status.SUCCESS.value,
            'remark': body['remark'], 'owner_id': payment2.payer_id, 'owner_type': payment2.payer_type
        }, d=r.data)
        trade_refund_id3 = r.data['id']
        # 确认余额
        user.userpointaccount.refresh_from_db()
        self.assertEqual(user.userpointaccount.balance, Decimal('6.01'))

        # 退款记录确认
        refund: RefundRecord = RefundRecord.objects.filter(id=trade_refund_id3).first()
        self.assertEqual(refund.out_order_id, payment2.order_id)
        self.assertEqual(refund.out_refund_id, out_refund_id3)
        self.assertEqual(refund.total_amounts, Decimal('66.00'))
        self.assertEqual(refund.refund_amounts, Decimal('0.02'))
        self.assertEqual(refund.real_refund, Decimal('0.00'))
        self.assertEqual(refund.coupon_refund, Decimal('0.02'))
        self.assertEqual(refund.status, RefundRecord.Status.SUCCESS.value)
        self.assertEqual(refund.owner_id, payment2.payer_id)
        self.assertEqual(refund.owner_type, payment2.payer_type)
        self.assertEqual(refund.in_account, user.userpointaccount.id)

        # 交易流水确认
        bill: TransactionBill = TransactionBill.objects.filter(
            trade_id=trade_refund_id3, trade_type=TransactionBill.TradeType.REFUND.value).first()
        self.assertEqual(bill.subject, refund.refund_reason)
        self.assertEqual(bill.account, refund.in_account)
        self.assertEqual(bill.app_service_id, refund.app_service_id)
        self.assertEqual(bill.app_id, self.app.id)
        self.assertEqual(bill.amounts, Decimal('0.00'))
        self.assertEqual(bill.coupon_amount, Decimal('0'))
        self.assertEqual(bill.after_balance, user.userpointaccount.balance)
        self.assertEqual(bill.owner_id, payment2.payer_id)
        self.assertEqual(bill.owner_type, OwnerType.USER.value)

        # --- vo ---
        vo = VirtualOrganization(name='test vo', owner=user)
        vo.save(force_insert=True)
        payment3 = PaymentHistory(
            payment_account='',
            payment_method=PaymentHistory.PaymentMethod.BALANCE.value,
            executor='executor',
            payer_id=vo.id,
            payer_name=vo.name,
            payer_type=OwnerType.VO.value,
            payable_amounts=Decimal('88.88'),
            amounts=Decimal('-88.88'),
            coupon_amount=Decimal('0'),
            status=PaymentHistory.Status.SUCCESS.value,
            status_desc='支付成功',
            remark='remark',
            order_id='order_id3',
            app_service_id='',
            instance_id='',
            app_id=self.app.id,
            subject='subject',
            creation_time=timezone.now(),
            payment_time=timezone.now()
        )
        payment3.save(force_insert=True)

        # error, no vo account
        out_refund_id4 = 'out_refund_id4_vo'
        body = {
            "out_refund_id": out_refund_id4,
            "out_order_id": payment3.order_id,
            "refund_amount": "1.01",
            "refund_reason": "reason好久2",
            "remark": "remark回来3"
        }
        r = self.do_request(client=self.client, app_id=self.app.id, private_key=self.user_private_key,
                            method='post', base_url=base_url, body=body, params={})
        self.assertEqual(r.status_code, 200)
        self.assert_is_subdict_of(sub={
            'trade_id': payment3.id, 'out_order_id': payment3.order_id, 'out_refund_id': out_refund_id4,
            'refund_reason': body['refund_reason'], 'total_amounts': '88.88', 'refund_amounts': '1.01',
            'real_refund': '1.01', 'coupon_refund': '0.00', 'status': RefundRecord.Status.ERROR.value,
            'remark': body['remark'], 'owner_id': payment3.payer_id, 'owner_type': payment3.payer_type
        }, d=r.data)
        trade_refund_id4_failed = r.data['id']
        # 退款记录确认
        refund4_failed: RefundRecord = RefundRecord.objects.filter(id=trade_refund_id4_failed).first()
        self.assertEqual(refund4_failed.status, RefundRecord.Status.ERROR.value)
        # 交易流水确认, 不存在
        bill = TransactionBill.objects.filter(
            trade_id=trade_refund_id4_failed, trade_type=TransactionBill.TradeType.REFUND.value).first()
        self.assertIsNone(bill)

        # 创建vo账户，否者退款失败
        PaymentManager.get_vo_point_account(vo_id=vo.id, is_create=True)
        # ok, balance + 0.00，同一个退款单号，旧的退款失败的退款记录会被删除
        body = {
            "out_refund_id": out_refund_id4,
            "out_order_id": payment3.order_id,
            "refund_amount": "1.01",
            "refund_reason": "reason好久2",
            "remark": "remark回来3"
        }
        r = self.do_request(client=self.client, app_id=self.app.id, private_key=self.user_private_key,
                            method='post', base_url=base_url, body=body, params={})
        self.assertEqual(r.status_code, 200)
        self.assert_is_subdict_of(sub={
            'trade_id': payment3.id, 'out_order_id': payment3.order_id, 'out_refund_id': out_refund_id4,
            'refund_reason': body['refund_reason'], 'total_amounts': '88.88', 'refund_amounts': '1.01',
            'real_refund': '1.01', 'coupon_refund': '0.00', 'status': RefundRecord.Status.SUCCESS.value,
            'remark': body['remark'], 'owner_id': payment3.payer_id, 'owner_type': payment3.payer_type
        }, d=r.data)
        trade_refund_id4 = r.data['id']
        # 确认余额
        user.userpointaccount.refresh_from_db()
        self.assertEqual(user.userpointaccount.balance, Decimal('6.01'))
        vo.vopointaccount.refresh_from_db()
        self.assertEqual(vo.vopointaccount.balance, Decimal('1.01'))

        # 退款记录确认
        refund: RefundRecord = RefundRecord.objects.filter(id=trade_refund_id4).first()
        self.assertEqual(refund.out_order_id, payment3.order_id)
        self.assertEqual(refund.out_refund_id, out_refund_id4)
        self.assertEqual(refund.total_amounts, Decimal('88.88'))
        self.assertEqual(refund.refund_amounts, Decimal('1.01'))
        self.assertEqual(refund.real_refund, Decimal('1.01'))
        self.assertEqual(refund.coupon_refund, Decimal('0.00'))
        self.assertEqual(refund.status, RefundRecord.Status.SUCCESS.value)
        self.assertEqual(refund.owner_id, payment3.payer_id)
        self.assertEqual(refund.owner_type, payment3.payer_type)
        self.assertEqual(refund.in_account, vo.vopointaccount.id)

        # 交易流水确认
        bill: TransactionBill = TransactionBill.objects.filter(
            trade_id=trade_refund_id4, trade_type=TransactionBill.TradeType.REFUND.value).first()
        self.assertEqual(bill.subject, refund.refund_reason)
        self.assertEqual(bill.account, refund.in_account)
        self.assertEqual(bill.app_service_id, refund.app_service_id)
        self.assertEqual(bill.app_id, self.app.id)
        self.assertEqual(bill.amounts, Decimal('1.01'))
        self.assertEqual(bill.coupon_amount, Decimal('0'))
        self.assertEqual(bill.after_balance, vo.vopointaccount.balance)
        self.assertEqual(bill.owner_id, payment3.payer_id)
        self.assertEqual(bill.owner_type, OwnerType.VO.value)

        # 同一个退款单号，旧的退款失败的退款记录会被删除
        refund = RefundRecord.objects.filter(id=refund4_failed.id).first()
        self.assertIsNone(refund)

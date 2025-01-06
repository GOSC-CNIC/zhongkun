import base64

from django.utils.translation import gettext as _

from core import errors as exceptions
from core import site_configs_manager
from apps.app_wallet.signers import SignatureResponse, SignatureRequest, SignatureParser
from apps.app_wallet.models import PayApp
from apps.api.viewsets import CustomGenericViewSetMixin, BaseGenericViewSet


class PaySignGenericViewSet(CustomGenericViewSetMixin, BaseGenericViewSet):
    """
    仅限JSON格式数据api视图使用
    """
    from django.db.models import QuerySet
    queryset = QuerySet().none()

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        # 处理请求之前，确保钱包密钥已配置
        site_configs_manager.get_wallet_rsa_keys()

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        private_key, public_key = site_configs_manager.get_wallet_rsa_keys()
        signer = SignatureResponse(private_key=private_key)
        response = signer.add_sign(response=response)
        return response

    def initialize_request(self, request, *args, **kwargs):
        request = super().initialize_request(request, *args, **kwargs)
        # 因为json parse时直接转成字典格式了，所以在json parse之前读取body以保存原始body bytes
        # 在视图之前有可能会触发json parse，比如CSRF会读django.POST
        body = request.body
        return request

    @staticmethod
    def check_request_sign(request):
        """
        :raise: Error
        """
        parser = SignatureParser(sign_type=SignatureRequest.SING_TYPE)
        token = parser.get_token_in_header(request)
        auth_type, app_id, timestamp, signature = parser.parse_token(token)

        # 检查base
        try:
            base64.b64decode(signature.encode('utf-8'))
        except Exception:
            raise exceptions.AuthenticationFailed(
                message=_('签名无效'), code='InvalidSignature'
            )

        app = PayApp.objects.filter(id=app_id).first()
        if app is None:
            raise exceptions.NotFound(
                message=_('app_id不存在'), code='NoSuchAPPID'
            )

        if app.status == PayApp.Status.UNAUDITED.value:
            raise exceptions.ConflictError(
                message=_('应用处于未审核状态'), code='AppStatusUnaudited'
            )
        elif app.status == PayApp.Status.BAN.value:
            raise exceptions.ConflictError(
                message=_('应用处于禁止状态'), code='AppStatusBan'
            )

        if not app.rsa_public_key:
            raise exceptions.ConflictError(
                message=_('app未配置RSA公钥'), code='NoSetPublicKey'
            )
        try:
            sr = SignatureRequest(request=request, public_key=app.rsa_public_key)
        except exceptions.Error as e:
            raise e

        method = request.method.upper()
        uri = request.path      # 为编码的
        body = request.body
        ok = sr.verify_signature(
            timestamp=timestamp, method=method, uri=uri,
            querys=request.query_params,
            body=body.decode(encoding='utf-8'), sig=signature
        )
        if not ok:
            raise exceptions.AuthenticationFailed(
                message=_('签名无效'), code='InvalidSignature'
            )

        return app


class TradeGenericViewSet(CustomGenericViewSetMixin, BaseGenericViewSet):
    """
    交易视图
    """
    from django.db.models import QuerySet
    queryset = QuerySet().none()

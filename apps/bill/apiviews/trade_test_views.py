from django.utils.translation import gettext_lazy
from rest_framework.serializers import Serializer
from rest_framework.request import Request
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from bill.apiviews import PaySignGenericViewSet
from api.paginations import NewPageNumberPagination
from core import errors


class TradeTestViewSet(PaySignGenericViewSet):
    """
    支付交易test视图
    """
    authentication_classes = []
    permission_classes = []
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('加签验签测试'),
        manual_parameters=[
            openapi.Parameter(
                name='param1',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='param1'
            ),
            openapi.Parameter(
                name='param2',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='param2'
            )
        ],
        responses={
            200: ''
        }
    )
    def create(self, request: Request, *args, **kwargs):
        """
        加签验签测试

            ## 接入余额结算准备条件
                * 需要先注册APP，再注册app service，一个app下可以有多个app service，至少要有一个app service，
                  支付扣费交易时需要指定app service id；
                * app service可以理解为在app下进一步细分了一个层级，例如一个接入的app下有云主机和存储2种资源服务，结算的时候2种资源的订单费用
                  想分别结算，就可以分别注册一个app service 1和app service 2，不想分开结算就注册一个app service，支付交易记录会记录
                  app service id。
                * 余额结算系统有资源券，一个资源券绑定到一个app service，券的结算使用限制在对应的app service，在app下细分一
                  个app service层级，也是为了细分资源券的结算使用范围（有的券只能用于云主机资源订单费用抵扣，有的券只能用于存储资源订单费用抵扣）。
                * 余额结算系统每个app需要配置app接入者一方的RSA2048密钥对的公钥，用于双方的签名认证。

            ## 请求签名生成规则：

            ### 待签名字符串(string_to_sign)的具体格式如下，无论各部分内容是否为空，各部分间的分割符“\\n“不能缺少。
                认证类型\\n                # SHA256-RSA2048
                请求时间戳\\n              # 1657097510; 请保持自身系统的时间准确
                HTTP请求方法\\n            # 大写字母, GET\POST\PUT
                URI\\n                    # api path, 不含域名； "/api/trade/test"
                QueryString\\n           # 按参数排序,各参数key=value以&分割拼接, UriEncode(key) + "=" + UriEncode(value)
                请求报文主体body            # json字符串，或者为空

                #### QueryString
                剔除 sign（需要以url参数传递签名的API对应的的参数名）字段，然后将所有参数与其对应值按参数名排序（字母升序排序）后，
                组合成 参数=参数值 的格式，并且把这些参数用 & 字符连接起来。
                参数名和参数值都需要经过uri编码, 空格字符是保留字符，必须编码为“%20”，而不是“+”

                #### 待签名字符串
                待签名字符串各部分以换行符\\n分割拼接，示例如下：
                1. 以此api为例 URI: /api/trade/test
                2. api有3个query参数: param1=test param1 ; param2=参数2 ; param3=66
                   QueryString: param1=test%20param1&param2=%E5%8F%82%E6%95%B02&param3=66
                3. 请求报文主体body: {'a': 1, 'b': 'test', 'c': '测试'}
                4. 最后得到的待签名字符串如下：
                ```
                SHA256-RSA2048\\n
                1657097510\\n
                POST\\n
                /api/trade/test\\n
                param1=test%20param1&param2=%E5%8F%82%E6%95%B02&param3=66\\n
                {"a": 1, "b": "test", "c": "\u6d4b\u8bd5"}
                ```
            ### 对签名字符串进行签名生成signature
                使用SHA256WithRSA签名函数用APP的私钥对待签名字符串进行签名，并进行 Base64 编码，得到签名字符串signature如下：
                GVbT13tSkxqhH2wl11TxKAdVA-DJsyTg5gTT6mvvARk4lzTC3RbdVg2O1q5PFpStIi-oLUIb9P7V5iXjEILJEMHIwoYZ51dcE0n
                IxqBru4sVZ0IdWg8Y7r8hMHaI2BYJffSO1LOMKsfVZssOjadt7TL14FDlwESBvCveAbBtp8zNBx1xZOBaLmvRh_SFvtPGgiAN0J
                yKaHdhgV6fF4wxzSyD2lXcx5L8uMsvTd1BY9h358ErWPpvchG1pMrXYJPE7TcG3xZe2kIhto-z45Q21kM-vIGjthlmmH0_Z-VMo
                2cBSlLmcLOwNFN4cVachPYYJWeB5bAjem6lUVDKsoDP3Q

            ### 最终签名sign格式，以下4部分以分割符”,“拼接。
                认证类型,                # SHA256-RSA2048
                请求时间戳,              # 1657097510; 请保持自身系统的时间准确，时间戳误差1小时内有效
                app_id,                 # 20220615085208
                signature

                最后得到sign:
                SHA256-RSA2048,1657097510,20220615085208,GVbT13tSkxqhH2wl11TxKAdVA-DJsyTg5gTT6mvvARk4lzTC3RbdVg2O1q5
                PFpStIi-oLUIb9P7V5iXjEILJEMHIwoYZ51dcE0nIxqBru4sVZ0IdWg8Y7r8hMHaI2BYJffSO1LOMKsfVZssOjadt7TL14FDlwES
                BvCveAbBtp8zNBx1xZOBaLmvRh_SFvtPGgiAN0JyKaHdhgV6fF4wxzSyD2lXcx5L8uMsvTd1BY9h358ErWPpvchG1pMrXYJPE7Tc
                G3xZe2kIhto-z45Q21kM-vIGjthlmmH0_Z-VMo2cBSlLmcLOwNFN4cVachPYYJWeB5bAjem6lUVDKsoDP3Q

            ## 应答验签签名规则：

            ### 应答签名通过3个标头header返回：
                标头 Pay-Sign-Type：SHA256-RSA2048     # 认证类型
                标头 Pay-Timestamp：1657184002         # 响应时间戳
                标头 Pay-Signature：                   # 应答签名

            ### 应答签名字符串格式：
                认证类型\n              # 标头 Pay-Sign-Type
                应答时间戳\n             # 标头 Pay-Timestamp
                响应报文主体

            ### 响应应答示例：
                标头 Pay-Sign-Type：SHA256-RSA2048     # 认证类型
                标头 Pay-Timestamp：1657184002         # 响应时间戳
                标头 Pay-Signature：                   # 应答签名
                UZz94tSxywv2ZfanJ_WURXmsnvM6yA8xoUfoddDQX7Rxw9b_HPWSdc1WdMZLSnfE9mAazETG1gjCdD9MfhJHR2tKF6hW
                4-qBVaoQ4bsnSHeDjGTgSNoXNbn8zuadxITGnDwHvrGgtrLMUi6iwDU4I4NYwRRzteVfJU71MsLbKwNtWpHok9hqljVI
                6tn7nFKUzHq-HImv6oKpSrBaVi1c5PW6PUDPrwjmOjxx876TrxKM7_3W0ztVF0ACEfAHPtXzPt4gP4AoRGeYtmWVypMK
                0xTlo2OeKTXej9GdUkdJWsRm_rcHtAYdOSHdF47hIuU-puKfuhg2WVUzLpwdJd4D-g

                响应报文主体：{'a': 1, 'b': 'test', 'c': '测试'}

            ### 验签
                应答签名字符串：
                ```
                SHA256-RSA2048\\n
                1657184002\\n
                {'a': 1, 'b': 'test', 'c': '测试'}
                ```
                使用SHA256WithRSA验签函数用 余额结算服务 的公钥对签名字符串进行签名验签。

            http code 200：
            {
                "xxx": "xxx",
                ...
            }
        """
        try:
            self.check_request_sign(request)
        except errors.Error as exc:
            return self.exception_response(exc)

        return Response(data=request.data)

    def get_serializer_class(self):
        return Serializer

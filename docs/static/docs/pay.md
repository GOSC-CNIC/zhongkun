## 1 接入余额结算准备条件
***
> 需要先注册APP，再注册app service，一个app下可以有多个app service，至少要有一个app service，
支付扣费交易时需要指定app service id；   
> app service可以理解为在app下进一步细分了一个层级，例如一个接入的app下有云主机和存储2种资源服务，结算的时候2种资源的订单费用
想分别结算，就可以分别注册一个app service 1和app service 2，不想分开结算就注册一个app service，支付交易记录会记录
app service id。   
> 余额结算系统有代金券，一个代金券绑定到一个app service，券的结算使用限制在对应的app service，在app下细分一
个app service层级，也是为了细分代金券的结算使用范围（有的券只能用于云主机资源订单费用抵扣，有的券只能用于存储资源订单费用抵扣）。   
> 余额结算系统每个app需要配置app接入者一方的RSA2048密钥对的公钥，用于双方的签名认证;
> app方需要拿到余额结算服务的RSA公钥，用于请求api时响应结果的验签。

> **app和app service的注册请联系技术支持人员。**  

* 结算服务示意图   

![](images/pay.png)

## 2 请求签名
***
> 加签认证用于部分安全性较高的接口，其他接口支持科技云通行证JWT认证方式。   
> 签名sign通过标头"Authorization"传递。   
`Authorization: 'SHA256-RSA2048 sign'`    
> 请求签名是客户端（应用）请求结算服务API时需要携带的身份/权限认证凭据，结算服务需要通过请求签名核实客户端的权限。
签名生成过程使用字符集UTF-8。

#### 请求签名生成规则
    待签名字符串(string_to_sign)的具体格式如下，无论各部分内容是否为空，各部分间的分割符“\n“不能缺少。
    ```
    认证类型\n                # SHA256-RSA2048    
    请求时间戳\n              # 1657097510; 请保持自身系统的时间准确   
    HTTP请求方法\n            # 大写字母, GET\POST\PUT    
    URI\n                    # api path, 不含域名； "/api/trade/test"   
    QueryString\n           # 按参数排序,各参数key=value以&分割拼接, UriEncode(key) + "=" + UriEncode(value)   
    请求报文主体body            # json字符串，或者为空   
    ```
#### QueryString
>剔除 sign（需要以url参数传递签名的API对应的的参数名）字段，然后将所有参数与其对应值按参数名排序（字母升序排序）后，
组合成 参数=参数值 的格式，并且把这些参数用 & 字符连接起来。   
>参数名和参数值都需要经过uri编码, 空格字符是保留字符，必须编码为“%20”，而不是“+”

#### 待签名字符串
待签名字符串各部分以换行符\n分割拼接，示例如下：   
1. 以此验签测试api为例 URI: /api/trade/test
2. api有3个query参数: param1=test param1 ; param2=参数2 ; param3=66
   QueryString: param1=test%20param1&param2=%E5%8F%82%E6%95%B02&param3=66
3. 请求报文主体body: {'a': 1, 'b': 'test', 'c': '测试'}
4. 最后得到的待签名字符串如下：
```
   SHA256-RSA2048\n
   1657097510\n
   POST\n
   /api/trade/test\n
   param1=test%20param1&param2=%E5%8F%82%E6%95%B02&param3=66\n
   {"a": 1, "b": "test", "c": "\u6d4b\u8bd5"}
```
#### 对签名字符串进行签名生成signature
    使用SHA256WithRSA签名函数用APP的私钥对待签名字符串进行签名，并进行 Base64 编码，得到签名字符串signature如下：   
    GVbT13tSkxqhH2wl11TxKAdVA-DJsyTg5gTT6mvvARk4lzTC3RbdVg2O1q5PFpStIi-oLUIb9P7V5iXjEILJEMHIwoYZ51dcE0n
    IxqBru4sVZ0IdWg8Y7r8hMHaI2BYJffSO1LOMKsfVZssOjadt7TL14FDlwESBvCveAbBtp8zNBx1xZOBaLmvRh_SFvtPGgiAN0J
    yKaHdhgV6fF4wxzSyD2lXcx5L8uMsvTd1BY9h358ErWPpvchG1pMrXYJPE7TcG3xZe2kIhto-z45Q21kM-vIGjthlmmH0_Z-VMo
    2cBSlLmcLOwNFN4cVachPYYJWeB5bAjem6lUVDKsoDP3Q

#### 最终签名sign格式，以下4部分以分割符“,”拼接。
    认证类型,                # SHA256-RSA2048
    请求时间戳,              # 1657097510; 请保持自身系统的时间准确，时间戳误差1小时内有效
    app_id,                 # 20220615085208
    signature

    最后得到sign:
    SHA256-RSA2048,1657097510,20220615085208,GVbT13tSkxqhH2wl11TxKAdVA-DJsyTg5gTT6mvvARk4lzTC3RbdVg2O1q5
    PFpStIi-oLUIb9P7V5iXjEILJEMHIwoYZ51dcE0nIxqBru4sVZ0IdWg8Y7r8hMHaI2BYJffSO1LOMKsfVZssOjadt7TL14FDlwES
    BvCveAbBtp8zNBx1xZOBaLmvRh_SFvtPGgiAN0JyKaHdhgV6fF4wxzSyD2lXcx5L8uMsvTd1BY9h358ErWPpvchG1pMrXYJPE7Tc
    G3xZe2kIhto-z45Q21kM-vIGjthlmmH0_Z-VMo2cBSlLmcLOwNFN4cVachPYYJWeB5bAjem6lUVDKsoDP3Q

## 3 应答签名
***
> 客户端请求服务API，API响应会返回应答签名，用于客户端验签，验证api响应的真实性。

#### 应答签名通过3个标头header返回：
    标头 Pay-Sign-Type：SHA256-RSA2048     # 认证类型
    标头 Pay-Timestamp：1657184002         # 响应时间戳
    标头 Pay-Signature：                   # 应答签名

#### 应答签名字符串格式：
    认证类型\n              # 标头 Pay-Sign-Type
    应答时间戳\n             # 标头 Pay-Timestamp
    响应报文主体

#### 响应应答示例：
    标头 Pay-Sign-Type：SHA256-RSA2048     # 认证类型
    标头 Pay-Timestamp：1657184002         # 响应时间戳
    标头 Pay-Signature：                   # 应答签名
    UZz94tSxywv2ZfanJ_WURXmsnvM6yA8xoUfoddDQX7Rxw9b_HPWSdc1WdMZLSnfE9mAazETG1gjCdD9MfhJHR2tKF6hW
    4-qBVaoQ4bsnSHeDjGTgSNoXNbn8zuadxITGnDwHvrGgtrLMUi6iwDU4I4NYwRRzteVfJU71MsLbKwNtWpHok9hqljVI
    6tn7nFKUzHq-HImv6oKpSrBaVi1c5PW6PUDPrwjmOjxx876TrxKM7_3W0ztVF0ACEfAHPtXzPt4gP4AoRGeYtmWVypMK
    0xTlo2OeKTXej9GdUkdJWsRm_rcHtAYdOSHdF47hIuU-puKfuhg2WVUzLpwdJd4D-g

    响应报文主体：{'a': 1, 'b': 'test', 'c': '测试'}

#### 验签
    应答签名字符串：
    ```
    SHA256-RSA2048\\n
    1657184002\\n
    {'a': 1, 'b': 'test', 'c': '测试'}
    ```
    使用SHA256WithRSA验签函数用 余额结算服务 的公钥对签名字符串进行签名验签。


## 4 加签验签测试接口
***

+ **说明**
>加签验签测试;   
> 签名sign通过标头"Authorization"传递。   
`Authorization: 'SHA256-RSA2048 sign'`

+ **请求url**
>https://vms.cstcloud.cn/api/trade/test

+ **请求方式**
>POST

***
+ **Query参数**   

可随意添加

| 参数 |   值   |
| :------: | :---: |
| param1 |  test param1  |
| param2 |  参数2   |
| param1 |  66   |

+ **请求体参数**

可随意添加

+ **请求示例**    
https://vms.cstcloud.cn/api/trade/test?param1=test%20param1&param2=%E5%8F%82%E6%95%B02&param3=66
```json
{
  "name1": "string",
  "name2": "string",
  "name3": "string"
}
```

+ **返回示例**  
响应标头  
```
Pay-Sign-Type：SHA256-RSA2048     # 认证类型
Pay-Timestamp：1657184002         # 响应时间戳
Pay-Signature：xxx                # 应答签名
```

请求成功时返回客户端请求体的内容   

```json
{
  "name1": "string",
  "name2": "string",
  "name3": "string"
}
```
请求错误响应示例    
```json
{
    "code": "xxx",
    "message": "xxx"
}
```
+ 错误码   

| 状态码 | 错误码 |             描述             | 解决方案 |
| :------: | :------: | :--------------------------: | :------: |
| 400  |  BadRequest   | 请求数据有误 | |
| 400  |  InvalidJWT   | Token is invalid or expired. | |
| 401  |  NoSuchAPPID   | app_id不存在 | |
| 401  |  AppStatusUnaudited   | 应用app处于未审核状态 | 联系服务技术支持人员 |
| 401  |  AppStatusBan   | 应用处于禁止状态 | 联系服务技术支持人员 |
| 401  |  NoSetPublicKey   | app未配置RSA公钥 | |
| 401  |  InvalidSignature   | 签名无效 | 检查签名生产过程是否有误，检查APP的私钥和RSA公钥是否匹配 |


## 5 支付扣费（JWT指定付款用户）
***

+ **说明**
> 向余额结算服务发起支付扣费，通过AAI/科技云通行证用户认证JWT指定付款用户。   
> 此接口适用要求：支持AAI/科技云通行证登录认证的APP，APP服务中扣费过程需要用户交互确认，即能拿到用户AAI/科技云通行证jwt。

+ **请求url**
>https://vms.cstcloud.cn/api/trade/pay

+ **请求方式**
>POST

***
+ **Query参数**
>无

+ **请求体参数**

| 参数 | 必选  | 参数类型 |   描述   |
| :------: | :---: | :------: | :------: |
| subject |  是   |  sring   |   标题   |
| order_id |  是   |  sring   |   外部订单ID，应用系统内部唯一   |
| amounts  |  是   |  sring   | 支付扣费金额，精确到小数点后2位，0.01 |
| app_service_id  |  是   |  sring   | APP服务ID |
| aai_jwt  |  是   |  sring   | AAI/科技云通行证用户认证JWT，用于指定付款用户，并验证付款用户的有效性 |
| remark  |  否   |  sring   | 备注信息 |

***

+ **请求示例**    

```json
{
  "subject": "string",
  "order_id": "string",
  "amounts": "string",
  "app_service_id": "string",
  "aai_jwt": "string",
  "remark": "string"
}
```

+ **响应示例**

| 参数 | 参数类型 |             参数名             | 描述 |
| :------: | :------: | :--------------------------: | :------: |
| id  |  sring   | 支付记录编号 | |
| subject |   sring    | 标题 | |
| payment_method  |  sring   | 支付方式 | balance(余额支付)；coupon(代金券支付)；balance+coupon(余额+代金卷)           |
| executor |  sring   | 交易执行人，可忽略 | |
| payer_id |  sring  | 支付者id | |
| payer_name |  sring  | 支付者名程 | |
| payer_type |  sring  | 支付者类型 | user(支付者是用户)；vo(支付者是VO组) |
| amounts | string | 余额扣费金额 | |
| coupon_amount | string |  代金券扣费金额 | |
| payment_time | string | 支付时间 | |
| type | string | 支付类型 | recharge：充值；payment：支付；refund：退款 |
| remark | string | 备注 |  |
| order_id | string | 外部订单编号 |  |
| app_id | string | 应用id |  |
| app_service_id | string | 应用子服务id |  |
 
响应标头  
```
Pay-Sign-Type：SHA256-RSA2048     # 认证类型
Pay-Timestamp：1657184002         # 响应时间戳
Pay-Signature：xxx                # 应答签名
```

请求成功响应示例
```json
{
    "id": "202207190608088519002990",
    "subject": "云主机（订购）8个月",
    "payment_method": "balance",
    "executor": "",
    "payer_id": "28b94370-0729-11ed-8d9d-c8009fe2ebbc",
    "payer_name": "lilei@xx.com",
    "payer_type": "user",   
    "amounts": "-1.99",       
    "coupon_amount": "0.00", 
    "payment_time": "2022-07-19T06:08:08.852251Z",
    "type": "payment",
    "remark": "test remark",
    "order_id": "123456789",
    "app_id": "20220719060807",
    "app_service_id": "123"
}
```
请求错误响应示例    
```json
{
    "code": "xxx",
    "message": "xxx"
}
```
错误码   

| 状态码 | 错误码 |             描述             | 解决方案 |
| :------: | :------: | :--------------------------: | :------: |
| 400  |  BadRequest   | 请求数据有误 | |
| 400  |  InvalidJWT   | Token is invalid or expired. | |
| 401  |  NoSuchAPPID   | app_id不存在 | |
| 401  |  AppStatusUnaudited   | 应用app处于未审核状态 | 联系服务技术支持人员 |
| 401  |  AppStatusBan   | 应用处于禁止状态 | 联系服务技术支持人员 |
| 401  |  NoSetPublicKey   | app未配置RSA公钥 | |
| 401  |  InvalidSignature   | 签名无效 | 检查签名生产过程是否有误，检查APP的私钥和RSA公钥是否匹配 |
| 409  |  BalanceNotEnough   | 余额不足 | |


## 6 支付扣费（直接指定用户名）
***

+ **说明**
> 此接口给予了APP最大的信任，直接通过用户名指定付款用户，向余额结算服务发起支付扣费。   
> 用于APP对应的服务内扣费过程中无用户参与，即无法拿到AAI/科技云通行证用户认证JWT的场景。

+ **请求url**
>https://vms.cstcloud.cn/api/trade/charge

+ **请求方式**
>POST

***
+ **Query参数**
>无

+ **请求体参数**

| 参数 | 必选  | 参数类型 |   描述   |
| :------: | :---: | :------: | :------: |
| subject |  是   |  sring   |   标题   |
| order_id |  是   |  sring   |   外部订单ID，应用系统内部唯一   |
| amounts  |  是   |  sring   | 支付扣费金额，精确到小数点后2位，0.01 |
| app_service_id  |  是   |  sring   | APP服务ID |
| username  |  是   |  sring   | AAI/科技云通行证用户邮箱，用于指定付款用户 |
| remark  |  否   |  sring   | 备注信息 |

***

+ **请求示例**    

```json
{
  "subject": "string",
  "order_id": "string",
  "amounts": "string",
  "app_service_id": "string",
  "username": "string",
  "remark": "string"
}
```

+ **响应示例**

| 参数 | 参数类型 |             参数名             | 描述 |
| :------: | :------: | :--------------------------: | :------: |
| id  |  sring   | 支付记录编号 | |
| subject |   sring    | 标题 | |
| payment_method  |  sring   | 支付方式 | balance(余额支付)；coupon(代金券支付)；balance+coupon(余额+代金卷)           |
| executor |  sring   | 交易执行人，可忽略 | |
| payer_id |  sring  | 支付者id | |
| payer_name |  sring  | 支付者名程 | |
| payer_type |  sring  | 支付者类型 | user(支付者是用户)；vo(支付者是VO组) |
| amounts | string | 余额扣费金额 | 此次支付交易从余额账户扣除的金额 |
| coupon_amount | string |  代金券扣费金额 | 此次支付交易从代金券扣费（抵扣）的金额 |
| payment_time | string | 支付时间 | |
| type | string | 支付类型 | recharge：充值；payment：支付；refund：退款 |
| remark | string | 备注 |  |
| order_id | string | 外部订单编号 |  |
| app_id | string | 应用id |  |
| app_service_id | string | 应用子服务id |  |
 
响应标头  
```
Pay-Sign-Type：SHA256-RSA2048     # 认证类型
Pay-Timestamp：1657184002         # 响应时间戳
Pay-Signature：xxx                # 应答签名
```

请求成功响应示例
```json
{
    "id": "202207190608088519002990",
    "subject": "云主机（订购）8个月",
    "payment_method": "balance",
    "executor": "",
    "payer_id": "28b94370-0729-11ed-8d9d-c8009fe2ebbc",
    "payer_name": "lilei@xx.com",
    "payer_type": "user",   
    "amounts": "-1.99",       
    "coupon_amount": "0.00", 
    "payment_time": "2022-07-19T06:08:08.852251Z",
    "type": "payment",
    "remark": "test remark",
    "order_id": "123456789",
    "app_id": "20220719060807",
    "app_service_id": "123"
}
```
请求错误响应示例    
```json
{
    "code": "xxx",
    "message": "xxx"
}
```
错误码   

| 状态码 | 错误码 |             描述             | 解决方案 |
| :------: | :------: | :--------------------------: | :------: |
| 400  |  BadRequest   | 请求数据有误 | |
| 400  |  InvalidJWT   | Token is invalid or expired. | |
| 401  |  NoSuchAPPID   | app_id不存在 | |
| 401  |  AppStatusUnaudited   | 应用app处于未审核状态 | 联系服务技术支持人员 |
| 401  |  AppStatusBan   | 应用处于禁止状态 | 联系服务技术支持人员 |
| 401  |  NoSetPublicKey   | app未配置RSA公钥 | |
| 401  |  InvalidSignature   | 签名无效 | 检查签名生产过程是否有误，检查APP的私钥和RSA公钥是否匹配 |
| 404  |  NoSuchBalanceAccount   | 指定的付费用户不存在（余额不足） | 付款用户名有误，或者可能未登录过结算系统（没有余额账号） |
| 409  |  BalanceNotEnough   | 余额不足 | |


## 7 支付交易记录编号查询支付交易记录
***

+ **说明**
> 支付交易记录编号查询支付交易记录

+ **请求url**
>https://vms.cstcloud.cn/api/trade/query/trade/{trade_id}

+ **请求方式**
>GET

+ **Path参数**

| 参数 | 必选  | 参数类型 |   描述   |
| :------: | :---: | :------: | :------: |
| trade_id |  是   |  sring   |   结算服务支付/交易记录编号(id)   |

***
+ **Query参数**
>无

+ **请求体参数**
>无   

***

+ **请求示例**   
```
https://vms.cstcloud.cn/api/trade/query/trade/202207190608088519002990
```

+ **响应示例**

| 参数 | 参数类型 |             参数名             | 描述 |
| :------: | :------: | :--------------------------: | :------: |
| id  |  sring   | 支付记录编号 | |
| subject |   sring    | 标题 | |
| payment_method  |  sring   | 支付方式 | balance(余额支付)；coupon(代金券支付)；balance+coupon(余额+代金卷)           |
| executor |  sring   | 交易执行人，可忽略 | |
| payer_id |  sring  | 支付者id | |
| payer_name |  sring  | 支付者名程 | |
| payer_type |  sring  | 支付者类型 | user(支付者是用户)；vo(支付者是VO组) |
| amounts | string | 余额扣费金额 | |
| coupon_amount | string |  代金券扣费金额 | |
| payment_time | string | 支付时间 | |
| type | string | 支付类型 | recharge：充值；payment：支付；refund：退款 |
| remark | string | 备注 |  |
| order_id | string | 外部订单编号 |  |
| app_id | string | 应用id |  |
| app_service_id | string | 应用子服务id |  |
 
响应标头  
```
Pay-Sign-Type：SHA256-RSA2048     # 认证类型
Pay-Timestamp：1657184002         # 响应时间戳
Pay-Signature：xxx                # 应答签名
```

请求成功响应示例
```json
{
    "id": "202207190608088519002990",
    "subject": "云主机（订购）8个月",
    "payment_method": "balance",
    "executor": "",
    "payer_id": "28b94370-0729-11ed-8d9d-c8009fe2ebbc",
    "payer_name": "lilei@xx.com",
    "payer_type": "user",   
    "amounts": "-1.99",       
    "coupon_amount": "0.00", 
    "payment_time": "2022-07-19T06:08:08.852251Z",
    "type": "payment",
    "remark": "test remark",
    "order_id": "123456789",
    "app_id": "20220719060807",
    "app_service_id": "123"
}
```
请求错误响应示例    
```json
{
    "code": "xxx",
    "message": "xxx"
}
```
错误码   

| 状态码 | 错误码 |             描述             | 解决方案 |
| :------: | :------: | :--------------------------: | :------: |
| 400  |  BadRequest   | 请求数据有误 | |
| 401  |  NoSuchAPPID   | app_id不存在 | |
| 401  |  AppStatusUnaudited   | 应用app处于未审核状态 | 联系服务技术支持人员 |
| 401  |  AppStatusBan   | 应用处于禁止状态 | 联系服务技术支持人员 |
| 401  |  NoSetPublicKey   | app未配置RSA公钥 | |
| 401  |  InvalidSignature   | 签名无效 | 检查签名生产过程是否有误，检查APP的私钥和RSA公钥是否匹配 |
| 404  |  NoSuchTrade   | 查询的交易记录不存在 | |
| 404  |  NotOwnTrade   | 交易记录存在，但交易记录不属于你app | |


## 8 外部订单编号查询支付交易记录
***

+ **说明**
> 订单编号查询支付交易记录，可用于查询确认订单对应的支付/扣费是否成功或完成。

+ **请求url**
> https://vms.cstcloud.cn/api/trade/query/out-order/{order_id}

+ **请求方式**
>GET

+ **Path参数**

| 参数 | 必选  | 参数类型 |   描述   |
| :------: | :---: | :------: | :------: |
| order_id |  是   |  sring   |   应用APP内的订单编号   |

***
+ **Query参数**
>无

+ **请求体参数**
>无   

***

+ **请求示例**   
```
https://vms.cstcloud.cn/api/trade/query/out-order/123456789
```

+ **响应示例**

| 参数 | 参数类型 |             参数名             | 描述 |
| :------: | :------: | :--------------------------: | :------: |
| id  |  sring   | 支付记录编号 | |
| subject |   sring    | 标题 | |
| payment_method  |  sring   | 支付方式 | balance(余额支付)；coupon(代金券支付)；balance+coupon(余额+代金卷)           |
| executor |  sring   | 交易执行人，可忽略 | |
| payer_id |  sring  | 支付者id | |
| payer_name |  sring  | 支付者名程 | |
| payer_type |  sring  | 支付者类型 | user(支付者是用户)；vo(支付者是VO组) |
| amounts | string | 余额扣费金额 | |
| coupon_amount | string |  代金券扣费金额 | |
| payment_time | string | 支付时间 | |
| type | string | 支付类型 | recharge：充值；payment：支付；refund：退款 |
| remark | string | 备注 |  |
| order_id | string | 外部订单编号 |  |
| app_id | string | 应用id |  |
| app_service_id | string | 应用子服务id |  |
 
响应标头  
```
Pay-Sign-Type：SHA256-RSA2048     # 认证类型
Pay-Timestamp：1657184002         # 响应时间戳
Pay-Signature：xxx                # 应答签名
```

请求成功响应示例
```json
{
    "id": "202207190608088519002990",
    "subject": "云主机（订购）8个月",
    "payment_method": "balance",
    "executor": "",
    "payer_id": "28b94370-0729-11ed-8d9d-c8009fe2ebbc",
    "payer_name": "lilei@xx.com",
    "payer_type": "user",   
    "amounts": "-1.99",       
    "coupon_amount": "0.00", 
    "payment_time": "2022-07-19T06:08:08.852251Z",
    "type": "payment",
    "remark": "test remark",
    "order_id": "123456789",
    "app_id": "20220719060807",
    "app_service_id": "123"
}
```
请求错误响应示例    
```json
{
    "code": "xxx",
    "message": "xxx"
}
```
错误码   

| 状态码 | 错误码 |             描述             | 解决方案 |
| :------: | :------: | :--------------------------: | :------: |
| 400  |  BadRequest   | 请求数据有误 | |
| 401  |  NoSuchAPPID   | app_id不存在 | |
| 401  |  AppStatusUnaudited   | 应用app处于未审核状态 | 联系服务技术支持人员 |
| 401  |  AppStatusBan   | 应用处于禁止状态 | 联系服务技术支持人员 |
| 401  |  NoSetPublicKey   | app未配置RSA公钥 | |
| 401  |  InvalidSignature   | 签名无效 | 检查签名生产过程是否有误，检查APP的私钥和RSA公钥是否匹配 |
| 404  |  NoSuchTrade   | 查询的交易记录不存在 | |

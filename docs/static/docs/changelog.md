## v1.5.0rc1
2023-05-22  
shun <869588058@qq.com>

* 订购云主机时验证配置样式flavor是否和服务单元匹配;
* 云主机元数据、配置样式flavor、服务单元资源配额中的内存单位由MiB改为GiB, 
  相关接口返回内存值的单位同时变更为GiB，编写对应的数据库迁移文件以更新历史数据，
  以及受影响的相关功能代码和测试用例修改;
* add AdminMeteringStorageStatistics api and testcase;
* 对象存储计量表增加计量时桶字节容量大小字段;
* 云主机和存储服务单元名称变更时 同步更新到对应的钱包子服务；
* 后台server修改页面字段布局优化，增加明文输入修改默认登录密码的功能;
* add command 'balance_due_zero';
* 新增指定时间段内创建用户和vo数量api和测试用例;

## v1.4.0
2023-04-27  
shun <869588058@qq.com>

* 新增VO组统计信息查询接口和测试用例；
* TiDB监控单元增加版本字段'version'；
* uwsgi配置文件修改，socket文件方式启动服务；
* EVCloud适配器身份认证请求设置timeout，以防止服务单元网络请求不可达时导致的api耗时太长；
* 订单未支付超时关闭脚本实现；
* AdminListBucket接口返回数据增加桶存储大小和对象数量统计信息；
* 新增AdminStorageStatistics接口和测试用例；


## v1.3.1
2023-04-13  
shun <869588058@qq.com>   

* 对象存储桶模型增加统计信息和标签等字段;
* AdminAggregationBucketMetering接口响应数据增加桶的存储数据大小、对象数量和tag等字段信息;
* AdminStatsBucket接口响应数据增加统计时间字段;
* 存储桶计量计费时更新桶统计信息;
* 机构、服务单元、监控单元排序值改为正序排序
* 工单动态邮件通知内容格式修改;
* MonitorTiDBQuery接口参数query增加‘storage’选项，一次性查询tidb的存储总容量和当前已用容量;
* 由于TiDB监控数据格式变动，修改PromQL查询语句;


## v1.3.0 
2023-04-11  
shun <869588058@qq.com>

* 对象存储、云主机服务单元配置模型增加排序权重字段‘sort_weight’，列举服务单元接口响应数据增加此排序字段；
* 增加tidb监控单元model，新增ListUnitTidb、MonitorTiDBQuery接口和测试用例;
* Bucket模型管控状态字段可选项修改；
* 新增AdminLockBucket、AdminDeleteBucket接口和测试用例；
* 工单新建和回复动态发送邮件通知；


## v1.2.0
2023-04-04  
shun <869588058@qq.com>

* 桶model增加创建状态，欠费管控状态字段；
* CreateBucket接口优化，创建桶请求超时生成状态为“创建中”的桶记录，允许创建桶的数量和用户在指定服务单元的券
和余额的总金额正相关;
* 云主机订购接口优化，增加可订购的按量计费云主机数量规则限制，可订购数与余额和券金额正相关;
* 代金券model增加过期和余额不足邮件通知时间2个字段，券过期和余额不足邮件通知脚本实现;
* 退款和交易流水模型增加‘交易操作人’字段;
* 增加AdminListBucket接口和测试用例；
* 增加AdminListTradeBill、AdminStatsBucket接口和测试用例；
* AdminListCashCoupon接口增加参数'time_start' 和 'time_end'；
* 机构模型增加排序权重字段“sort_weight”，监控单元列举接口和列举机构接口返回数据中增加此排序权重字段；
* Email模型字段'receiver'类型改为CharField，以记录多个地址信息；


## v1.1.0
2023-03-15  
shun <869588058@qq.com>

* 增加 站点监控任务特别关注标记（WebsiteTaskAttentionMark）接口和测试用例;
* 站点监控任务创建、列举和更改接口响应增加‘modification’、‘is_attention’字段内容;
* 新增管理员查询对象存储计量计费聚合信息接口和测试用例，分别按bucket、user、service进行聚合；
* AdminCreateCashCoupon api权限修改，允许联邦管理员创建所有app子服务的代金券；
* ListCashCoupon api修改参数‘valid’的值可选项； 
* AdminListCashCoupon api增加参数‘valid_status’；
* AdminListCashCoupon api 增加参数‘issuer’和‘redeemer’；
* 代金券model增加发放人字段“issuer”，券列举查询和查询详情等有关api响应内容增加“issuer”内容；


## v1.0.0
2023-03-09  
shun <869588058@qq.com>

* 增加列举网站监控探测点接口（ListWebsiteDetectionPoint）和测试用例;
* 增加人工充值接口（RechargeManual）和测试用例;
* WebsiteQuery、WebSiteQueryRange接口增加参数'http_duration_seconds';
* 非管理员限制创建2个站点监控任务;
* 站点监控版本模型类重命名，并且移除字段‘provider’，站点监控任务模型增加特别关注
字段‘is_attention’;
* MonitorWebsiteQuery、MonitorWebsiteQueryRange接口增加参数‘detection_point_id’，指定从那个探测点查询数据；

## v0.9.0
2023-03-02  
shun <869588058@qq.com>

* ListMonitorCephUnit api增加筛选参数'organization_id'，响应数据增加监控机构信息；
* ListMonitorServerUnit api增加筛选参数'organization_id'， 响应数据增加监控机构信息;
* 适配器镜像接口修改，增加一些标准化字段；
* 增加一个分页列举镜像的api和测试用例；
* Flavor增加资源提供者服务端规格ID、Disk字段；修改Flavor相关的订单与创建参数；
* 增加 AdminListCashCouponPayment、AdminGetCashCoupon、AdminDeleteCashCoupon api和测试用例；
* ListCashCoupon api移除参数'available'，增加参数'valid'
* 增加 用户查询代金券详情（GetCashCoupon） api 和测试用例；


## v0.8.0
2023-02-13
* 增加server计量计费单详情查询API;
* 完善VMware适配器;
* ListService api响应内容data_center部分增加name_en信息;
* app_service移除外键user，增加users多对多字段标记用户管理权限;
* app_service模型外键字段service改为service_id字符串型字段;
* 站点监控model定义，实现站点监控任务创建、修改、删除等管理接口；
* 实现供监控服务查询站点监控任务变动版本和拉取监控任务接口；
* 实现2个站点监控数据查询接口；
* 云主机和对象存储服务单元配置网址字段移除唯一性限制;
* add AdminListAppService api and testcase
* seagger在线api文档支持http和https选择
* 通行证有关域名变更修改，结算接口文档说明中服务域名变更修改
* admin后台删除存储桶优化
* CreateBucket api存储桶名称有效性验证优化
* aliyun有关依赖包管理文件更新
* 增加阿里云适配器

## v0.7.1
2022-12-27
* 增加查询app交易流水记录api和测试用例;  
* 支付记录查询2个api增加参数‘query_refunded’返回已退款金额信息;  
* add command 'tradebill_trade_amounts_fill';
* ListTradeBill接口响应内容增加'out_trade_no','trade_amounts'内容；  
* 交易流水增加交易总金额和外部交易单号字段；  
* 退款交易流水记录中记录应退券金额；  
* server、对象存储日结算单详情查询2个api返回内容增加‘计量单’列表信息;  

## v0.7.0
2022-12-21
* ListTickets、DetailTicket接口响应增加'rating'评分内容;   
* 结算认证优化，拿到签名字符串后先做base64解码验证有效性;    
* 修复ListStatementStorage接口传入参数'date_end'报错的问题;  
* 监控单元Ceph、server模型修改，可访问权限可单独配置，去除service字段；  
* 增加ListCephMonitorUnit、ListServerMonitorUnit api和测试用例；  
* 修改3个原监控查询api，参数“service_id”改为“monitor_unit_id”；  

## v0.6.0
2022-12-05    
* 修改支付记录model，增加交易流水账单model，内部支付扣费函数接口修改，对应的列举支付记录、查询支付记录详情、
  列举代金券支付记录、支付扣费、查询支付状态等接口返回内容修改和测试用例修改；  
* 增加退款接口、退款查询接口和测试用例; 
* 结算接入文档增加退款接口内容；  
* 云主机配置规格flavor绑定服务单元，每个服务单元可单独设置，ListFlavor接口增加参数“service_id”, 增加对应测试用例；
* 增加命令'update_coupon_time'更新一批券（从指定券模板复刻的）生效时间为当前时间；  
* 增加命令'payment_to_tradebill'为历史支付记录创建交易流水，以及填充历史支付记录后添加的字段信息；
* admin后台一些数据不允许删除操作；

## v0.5.0
2022-11-11   
* ListTicketFollowUp接口修改，工单提交人只能查询回复信息，处理人能查询所有回复和工单修改记录信息;  
* 代金券兑换api优化，只允许云主机的券兑换给vo组； 
* 监控相关model增加一些字段；
* 依赖包版本升级pyOpenSSL==21.0.0；
* 新增接口TicketRatingQuery（工单评价查询），TicketRatingAdd（工单提交评价）和测试用例； 
* ListTicket api通过参数'assigned_to'查询指定处理人的工单； 
* rsa加密签名字符串格式修改，不做url特殊字符转换；
* 工单id长度修改，关闭的工单不允许修改工单的状态和转交工单； 
* add command 'update_app_public_key'；app公钥改为多行文本输入框
* 优化command 'generate_rsa_key'；
* 通行证jwt用户单位字段为null时认证失败的bug修复；
* 简化工单状态选项数量，以及对应的api修改；工单指定处理人后工单状态改为‘处理中’；转交工单权限修改，允许所
有管理员转交工单；
* add command 'importbucket' and 'list_storage_service'；
* ListMeteringStorage接口响应内容增加'service'数据；

## v0.4.1
2022-10-31
* admin后台server列表不允许删除操作;  
* 增加“generate_rsa_key”命令，增加RSA加密签名密钥对生成GenerateRSAKey接口和测试用例代码；  
* 增加结算服务验签RSA公钥查询TradeSignPublicKeyQuery接口和测试用例代码；
* 已指派处理人的“open”状态的工单更改时产生更改记录；  

## v0.4.0
2022-10-26   
* 增加列举对象存储日结算单、单个日结算单明细查询和对象存储计量信息查询3个API和测试用例代码； 
* 列举代金券ListCashCoupon接口增加参数'app_service_category'； 
* ListBucket接口能查询到所有的桶（包括其他用户的）的问题修复； 
* admin列举代金券返回内容增加兑换码字段； 
* 新增管理员创建代金券（可发放给指定用户）接口和测试用例代码；
* 新增ListAppService接口和测试用例代码；
* 新增列举用户（ListUser）接口和测试用例代码；
* 列举工单ListTicket接口增加参数'assigned_to'；
* 新增领取工单（TakeTicket）、转交工单给其他处理人（TicketAssignedToUser）2个接口和测试用例代码；  
* 更改工单状态、更改工单严重程度、提交工单回复3个接口权限修改，只有工单指派的处理人有权限； 

## v0.3.0
2022-09-30
* 新增云服务器日结算单接口ListStatementServer、DetailStatementServer；
* 对象存储桶的计量计费、日结算单和扣费代码实现；
* 新增工单app, 模型定义，新增工单相关接口CreateTicket、ListTicket、TicketDetail、
  UpdateTicket、TicketSeverityChange、TicketStatusChange、TicketFolowUpAdd、
  TicketFollowupList；  
* 列举对象存储服务单元接口不再要求身份认证。

## v0.2.0
2022-09-15
* 对象存储model定义和修改，对象存储日结算单model定义；
* add api ListBucket、DeleteBucket、CreateBucket、ListStorageService and testcase;
* admin后台一些model列表去掉删除的action；
* server服务单元服务状态“暂停服务”时，不允许server重建和续费；
* ListService api默认返回所有服务单元，增加参数'status'筛选不同状态的服务单元
* server列举、详情和归档记录api响应内容'service'增加'name_en'数据；
* 云主机服务单元资源配额列举api修改，过滤掉已删除的服务单元，添加api单元测试
* 多个云主机创建时间相同时，云主机计量代码死循环的问题修复；
* server日结算单生成和单元测试，日结算单扣费；

## v0.1.0
2022-08-24
* 实现订单模块、计量计费模块和支付扣费结算模块；
* EVCloud、OpenStack、VMware服务API适配器实现，服务接入的配置设计和实现;
* 云服务器资源订购、订单支付和资源交付等功能；
* 云服务器重建、删除、操作、状态查询等功能管理API实现；
* 用户登录、登出、修改密码等基础功能，支持科技云通行证登录；
* vpn配置文件下载和账号获取、激活和停用API；
* 视频会议、物理服务器和CEPH集群监控信息查询API实现；
* 代金券功能和API实现；
* VO组功能和API实现;

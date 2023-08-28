## v1.11.1
发布时间： 2023-08-28  
发布人： shun  

* 定义云硬盘变更日志模型，云硬盘计量功能支持按量付费转包年包月的付费方式变更，新增ModifyDiskPayType接口和测试用例；提交人：shun
* 云主机计量优化，修复计费开始时间和重建、付费方式变更时间都不在计费周期内的云主机漏计量的问题；提交人：shun
* 优化月度报表和云主机过期邮件html字符串长度，去除空白行和每行无用的空格；提交人：shun
* 订单创建函数优化，修复无法提交按量付费订单的问题；提交人：shun
* 服务总请求数统计更新脚本优化，并添加测试用例；提交人：shun
* 云主机付费方式修改api测试用例完善；提交人：shun


## v1.11.0
发布时间： 2023-08-16  
发布人： shun  

* 云主机计量功能支持按量付费转包年包月的付费方式变更，新增ModifyServerPayType接口和测试用例；提交人：shun
* ListServiceShareQuota、ListServicePrivateQuota增加参数“data_center_id”；提交人：shun
* AdminCreateCashCoupon接口增加参数‘vo_id’，直接给指定vo发代金券；提交人：shun
* 余额欠费清零command优化；提交人：shun
* 中国科技云身份认证联盟AAI认证登录支持；提交人：shun


## v1.10.0
发布时间： 2023-08-09  
发布人： shun  

* 新增站点监控WebsiteStatusOverview、ListWebSiteDurationDistribution接口和测试用例；提交人：shun
* 实服务总请求数model定义，请求数统计更新脚本实现，PortalServiceStatus、PortalServiceUserNum、PortalServiceReqNum接口和测试用例；提交人：shun
* ListBucket接口响应数据增加桶容量和对象数量信息；提交人：shun
* DetachDisk、DeleteDisk接口增加参数‘as-admin’；提交人：shun
* 月度报表邮件模板增加云硬盘数据内容；提交人：shun
* 添加站点日志请求量时序数据模型和请求量时序数据生成脚本，ListLogSiteTimeCount接口和测试用例；提交人：shun
* 添加资源操作日志模型，云主机、云硬盘和存储桶删除时创建对应的删除日志；提交人：shun
* 预付费云主机过期和按量计费云主机欠费不允许开机，站点监控后台增改操作优化；提交人：shun


## v1.9.0
发布时间： 2023-07-24  
发布人： shun  

* 月度报表模型增加云硬盘相关字段，生成月度报表脚本实现云硬盘月度数据统计；提交人：shun
* MonitorServerQuery、MonitorCephQuery、MonitorTidbQuery接口参数增加一个选项，一次返回所有指标类型数据；提交人：shun
* 云硬盘日结算单接口ListDiskStatement、GetDiskStatement和测试用例；提交人：shun
* 云硬盘计量单查询GetDiskMetering和测试用例；提交人：shun
* 按云硬盘、用户、vo组和服务单元聚合云硬盘计量计费信息4个查询接口和测试用例；提交人：shun
* LogSite模型定义，ListLogSite、 LogSiteQuery接口和测试用例；提交人：shun


## v1.8.0
发布时间： 2023-07-14  
发布人： shun  

* 云主机过期邮件通知脚本，过期或将过期云主机通知邮件视图页面；提交人：shun
* 列举server、ceph、tidb监控服务单元3个接口响应数据去重；提交人：shun
* 增加云主机配置样式flavor创建、查询、修改和删除管理员接口和测试用例；提交人：shun
* 扩展ListDisk api，可以查询个人，vo组云硬盘，以管理员身份查询云硬盘；提交人：shun
* 监控主机内存使用率指标查询语句去除大页内存；提交人：shun


## v1.7.2
发布时间： 2023-07-05  
发布人： shun  

* 续费询价接口支持云硬盘续费询价；提交人：shun
* 增加云硬盘备注修改接口和测试用例；提交人：shun
* 增加云硬盘计量单查询接口和测试用例；提交人：shun
* vo组资源统计信息查询接口响应数据增加云硬盘数量和在组中的角色信息；提交人：shun
* 订购按量计费云主机云硬盘时要求拥有下限金额为100；提交人：shun


## v1.7.1
发布时间： 2023-07-01  
发布人： shun  

* 新增云硬盘续费接口RenewDisk和测试用例；提交人：shun
* 定义云硬盘计量、日结算单模型，实现云硬盘计量、日结算单生成和结算功能，云盘计量结算测试用例；提交人：shun
* uuid模型默认id改为short uuid1长25的字符串；提交人：shun
* 对象存储计量记录模型增加字段'billed_network_flow'和'billed_network_flow'；提交人：shun
* 云硬盘金额计算修复，容量定价价格由按小时改为按天计算；提交人：shun


## v1.7.0
发布时间： 2023-06-29  
发布人： shun  

* 云主机适配器云硬盘相关函数接口设计定义，实现evcloud适配器云硬盘相关函数接口；提交人：shun
* 云硬盘订购创建、列举、删除、挂载、卸载接口和测试用例；提交人：shun
* 云主机重建要求先卸载云硬盘，DeleteServer、ActionServer接口视图处理函数优化，删除时先卸载云硬盘；提交人：shun
* ListAzone接口和适配器增加可用性字段available；提交人：shun
* 服务单元私有配额资源后台更新操作内容增加云硬盘已用资源量；提交人：shun
* 网站名称可通过配置文件设置，不配置科技云通行证信息时登录页面不显示通行证登录连接按钮；提交人：shun
* ListWebsite接口增加basic身份认证支持；提交人：shun
* 云主机服务单元增加字段“disk_available”标识是否提供云硬盘资源服务，对象存储服务单元增加字段“loki_tag”；提交人：shun


## v1.6.3
发布时间： 2023-06-09  
发布人： shun  

* AdminMeteringServerStatistics接口和测试用例；提交人：shun
* 按发放人统计代金券信息管理员查询接口和测试用例；提交人：shun
* 聚合统计每个用户代金券信息、聚合统计每个VO组代金券信息 管理员查询接口和测试用例；提交人：shun
* 按用户、vo组和服务单元聚合server计量计费查询3个接口增加排序参数‘order_by’；提交人：shun
* 安装shortuuid依赖包，更新依赖包文件，网站监控测试用例修改，对象存储服务单元排序值改为正序；提交人：shun
* 订购时长选项后台增、改时检查是否已存在相同选项，增加'update_website_url'命令；提交人：shun


## v1.6.2
发布时间： 2023-06-09  
发布人： shun  

* tidb监控单元主机磁盘使用率更改为指定挂载盘的使用率；提交人：shun
* 新增代金券统计管理员接口和测试用例；提交人：shun
* 新增SendEmail接口和测试用例，邮件模型增加字段“remote_ip”；提交人：shun
* 站点监控模型增加url协议、域名、uri和防篡改4字段，用户站点监控任务创建、修改和列举接口使用新的4个字段，原url参数移除，对应测试用例修改；提交人：shun
* 由于站点监控模型变更，编写数据库迁移文件和新增命令“clearwebsitetask”，来处理已有数据；提交人：shun
* 月度报表邮件发送用户增加筛选条件，只查询月度周期结束时间之前创建的用户；提交人：shun


## v1.6.1
发布时间： 2023-06-05  
发布人： shun

* 增加订购时长模型，ListPeriod接口和测试用例；提交人：shun
* 存储桶计量计费每天收取0.06基础费；提交人：shun
* 月度报表数据库查询优化，报表中vo组按组角色排序，个人云主机展示每个云主机的计量结算数据；提交人：shun


## v1.6.0
发布时间： 2023-05-30  
发布人： shun

* 添加report app，月度报表模型定义，月度报表生成和邮件发送功能脚本实现；提交人：shun
* 券余额不足过期和订单超时关闭脚本日志配置优化；提交人：shun
* ceph,server,tidb监控单元增加关联云主机服务单元字段，允许关联的云主机服务单元管理员访问监控单元；提交人：shun
* 邮件模型增加‘tag’、’is_html‘、‘status’、'status_desc'和'success_time'字段；提交人：shun
* 增加邮件详情预览页面，后台邮件列表增加“预览”连接；提交人：shun
* evcloud适配器镜像列举修改，返回所有基础和个人镜像；提交人：shun


## v1.5.0
发布时间： 2023-05-22  
发布人： shun

* 订购云主机时验证配置样式flavor是否和服务单元匹配； 提交人：shun
* 云主机元数据、配置样式flavor、服务单元资源配额中的内存单位由MiB改为GiB, 
  相关接口返回内存值的单位同时变更为GiB，编写对应的数据库迁移文件以更新历史数据，
  以及受影响的相关功能代码和测试用例修改； 提交人：shun
* add AdminMeteringStorageStatistics api and testcase； 提交人：shun
* 对象存储计量表增加计量时桶字节容量大小字段； 提交人：shun
* 云主机和存储服务单元名称变更时 同步更新到对应的钱包子服务； 提交人：shun
* 后台server修改页面字段布局优化，增加明文输入修改默认登录密码的功能； 提交人：shun
* add command 'balance_due_zero'； 提交人：shun
* 新增指定时间段内创建用户和vo数量api和测试用例； 提交人：shun
* GetServerVNC接口增加管理员身份参数‘as-admin’；  提交人：shun


## v1.4.0
2023-04-27  
shun

* 新增VO组统计信息查询接口和测试用例；
* TiDB监控单元增加版本字段'version'；
* uwsgi配置文件修改，socket文件方式启动服务；
* EVCloud适配器身份认证请求设置timeout，以防止服务单元网络请求不可达时导致的api耗时太长；
* 订单未支付超时关闭脚本实现；
* AdminListBucket接口返回数据增加桶存储大小和对象数量统计信息；
* 新增AdminStorageStatistics接口和测试用例；


## v1.3.1
2023-04-13  
shun  

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
shun

* 对象存储、云主机服务单元配置模型增加排序权重字段‘sort_weight’，列举服务单元接口响应数据增加此排序字段；
* 增加tidb监控单元model，新增ListUnitTidb、MonitorTiDBQuery接口和测试用例;
* Bucket模型管控状态字段可选项修改；
* 新增AdminLockBucket、AdminDeleteBucket接口和测试用例；
* 工单新建和回复动态发送邮件通知；


## v1.2.0
2023-04-04  
shun

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
shun

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
shun

* 增加列举网站监控探测点接口（ListWebsiteDetectionPoint）和测试用例;
* 增加人工充值接口（RechargeManual）和测试用例;
* WebsiteQuery、WebSiteQueryRange接口增加参数'http_duration_seconds';
* 非管理员限制创建2个站点监控任务;
* 站点监控版本模型类重命名，并且移除字段‘provider’，站点监控任务模型增加特别关注
字段‘is_attention’;
* MonitorWebsiteQuery、MonitorWebsiteQueryRange接口增加参数‘detection_point_id’，指定从那个探测点查询数据；

## v0.9.0
2023-03-02  
shun

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

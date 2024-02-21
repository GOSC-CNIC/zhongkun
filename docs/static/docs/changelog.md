## v1.18.0
发布时间： 2024-02-21  
发布人： shun  

* 移除app ipam和link；提交人：shun
* 订单资源模型增加资源实例删除时间字段"instance_delete_time"，订单详情查询接口返回数据增加此字段，
  云主机云硬盘删除时更新相关订单资源删除时间；提交人：shun
* 新增tidb、ceph、服务器监控指标数据查询v2接口和测试用例；提交人：shun
* 旧tidb、ceph、服务器监控指标数据查询接口查询后端代码重构，一次查询所有指标数据时网络请求改为异步方式；提交人：shun


## v1.17.0
发布时间： 2024-02-06  
发布人： shun  

* 错误日志创建优化，ErrorLog模型增加add_log方法；提交人：shun
* 全局和中英语言日期和时间显示和输入格式设置；提交人：shun
* 增加欠费云主机和存储桶model，遍历查询欠费云主机和存储桶的功能代码实现，定时任务放在月度报表定时任务脚本中；提交人：shun
* 新增列举欠费云主机和存储桶接口和测试用例；提交人：shun
* 询价接口增加参数“number”, 支持一次订购多个资源询价；提交人：shun
* 订单模型增加订购数量number字段，列举订单和订单详情查询接口响应数据增加“number”和“instance_status”字段；提交人：shun
* 云主机创建订购api增加参数“number”，允许订购多个云主机，实现订购多个资源的订单的资源交付功能；提交人：shun
* 安装django-baton，美化admin后台，添加一个css样式文件到后台所有model页面，使列表表头文字不换行；提交人：shun
* ipv4拆分器实现最小化拆分ipv4网段规划方法；提交人：shun
* 移除ipam和link的所有model和api；提交人：shun


## v1.16.0
发布时间： 2024-01-22  
发布人： shun  

* 重构ipam和link app合并为一个新的app netbox；编写数据库迁移文件把原ipam和link的数据库表数据复制到netbox对应的表中；
  原ipam和link的2个用户角色权限接口合并为了一个新接口；
  netbox新增与原ipam和link的功能相同的对应接口，原ipam和link的接口底层对接到netbox视图层和数据库表；提交人：shun


## v1.15.4
发布时间： 2024-01-16  
发布人： shun  

* 云主机计量计费统计接口统计数据改为按vo和user分别统计；提交人：shun
* 把云主机服务单元和配额model、接口路由和代码从service app迁移到servers app下, 手动修改迁移model有关的历史数据库迁移文件记录；提交人：shun
* 定义错误日志model，记录异常日志到数据库；提交人：shun
* admin后台app排序优化，修复admin后台用户不能修改密码的问题；提交人：shun


## v1.15.3
发布时间： 2024-01-12  
发布人： shun  

* 定义机构二级的联系人model，新增 联系人创建、修改、列举接口和测试用例；提交人：shun
* 新增 机构二级对象修改、详情查询、添加和移除联系人接口和测试用例；提交人：shun
* 新增 按指定拆分规划拆分一个ipv4地址段接口和测试用例；提交人：shun
* 移除链路的机构二级model和接口，配线架改为外键关联ipam的机构二级；提交人：shun
* 移除钱包的支付机构model，移除机构model中的4个不再使用的url字段，移除机构和云主机服务单元接入申请相关接口；提交人：shun
* 后台链路model的一些外键字段优化，后台日期时间默认显示格式设置；提交人：shun


## v1.15.2
发布时间： 2024-01-05  
发布人： shun  

* 站点监控任务模型移除url字段，增加数据中心逻辑外键字段，站点监控任务列举和监控数据查询接口支持数据中心监控任务和管理员权限；提交人：shun
* 查询站点监控任务关联的用户邮件地址接口增加关联的数据中心管理员邮箱地址，并完善对应测试用例；提交人：shun
* 数据中心模型增加指标和日志监控网址字段，后台添加或修改数据中心时自动创建或更新指标和日志系统对应的监控任务；提交人：shun
* 云主机和对象存储服务单元模型增加监控任务id字段，后台添加和更改服务单元时自动创建对应的站点监控任务；提交人：shun
* 用户不存在时，通过aai身份认证访问时自动创建用户失败后尝试查询用户是否已存在，避免并发访问同时创建用户冲突时不必要的报错；提交人：shun
* 异常和日志打印优化，不成功的response都记录日志；提交人：shun
* ipam机构二级对象查询接口关键字查询范围增加机构名称；提交人：shun
* django4.2.8 up 4.2.9,django-tidb4.2.1 up 4.2.3；提交人：shun
* 查看swagger在线文档页面需要登录；提交人：shun


## v1.15.1
发布时间： 2023-12-28  
发布人： shun  

* 路由和接口代码结构重构，各app相关路由和接口代码由api app移到各app下；提交人：shun
* 项目目录名由cloudverse改为yunkun；提交人：shun
* 云主机服务单元私有配额未设置，默认不做资源限制；提交人：shun
* 安装django-json-wedget，后台json字段编辑优化；提交人：shun
* 适配器增加可用资源配额查询接口，EVCloud和OpenStack适配器实现此接口，新增服务单元可用资源总量查询接口和测试用例；提交人：shun
* 新增欠费云主机查询脚本，保存结果到邮件记录；提交人：shun
* 日志数量统计时序数据模型数量字段改为有符号整型类型，查询时序数据的接口屏蔽统计数量小于0的无效数据；
  日志统计时序数据定时脚本优化，统计失败时插入数量为-1的无效的占位记录，并尝试更新前几个周期可能存在的无效时序数据，
  新增更新无效日志统计时序数据定时脚本；提交人：shun
* 订单详情查询接口返回数据增加资源交付状态描述字段“desc”；提交人：shun
* 视屏会议监控查询不到数据问题优化，获取客户端IP方法整合到访问IP鉴权模块，移除“我的资源”页面；提交人：shun
* 后台日志统计时序数据时间戳转年月日格式时间显示，后台云主机和存储服务单元配置明文密码显示优化，一些model注释名称修改；提交人：shun；提交人：shun


## v1.15.0
发布时间： 2023-12-11  
发布人： shun  

* 项目目录由vms改为cloudverse，gosc目录改为cloudverse，对应修改受路径变更影响的各种配置和脚本；提交人：shun
* 移除link被压缩的旧迁移文件；提交人：shun
* IPv4RangeSplit接口限制拆分子网掩码长度差值不能大于8，即每次拆分子网数最多256个；提交人：shun
* 新增 数据中心下关联的各服务单元查询接口和测试用例；提交人：shun
* 云主机服务单元配额和配置样式相关接口支持数据中心管理员权限；提交人：shun
* ipam、link、vo和monitor的路由配置放到各自app下；提交人：shun
* 新增 IPAM机构分配对象创建和查询接口和测试用例；提交人：shun
* 新增 IPv4地址段变更记录查询接口（ListIPv4RangeRecord）和测试用例；提交人：shun
* 新增 IPv4地址段备注信息修改接口（IPv4RangeRemark）和测试用例；提交人：shun
* 新增 IPv4地址查询和备注修改接口和测试用例；提交人：shun
* ipv4range修改记录类型时，新旧地址段存储对调，ip_ranges字段由存旧地址段信息改为存修改后的新地址段信息；数据中心备注字段类型由Char改为Text；提交人：shun
* 云主机服务单元model增加字段“仅管理员可见”，列举服务单元接口响应数据增加此字段；提交人：shun
* ipv6地址、地址段和地址段变更记录model定义，iprangeimport命令实现ipv6 range导入；提交人：shun
* 新增 IPv6地址段创建、查询、修改、删除、收回、预留接口和测试用例；提交人：shun
* 实现客户端ip访问限制类IPRestrictor，link所有api增加客户端ip访问限制鉴权，站点监控用户邮箱地址查询接口、邮件发送和portal有关接口客户端IP访问权限鉴权优化；提交人：shun
* 新增 通过标签标识查询对应监控单元管理员邮箱地址接口和测试用例；提交人：shun
* 查询有管理权限的云主机和对象存储服务单元接口返回数据重复问题修复；提交人：shun
* 数据中心管理员移除、添加接口修改和admin后台变更数据中心管理员时，管理员权限同步到钱包中的数据中心下云主机和对象存储服务单元对应的结算单元；提交人：shun
* 优化适配器自定义参数，各适配器可以定义自定义参数，服务单元接入配置会检测自定义参数的设置；提交人：shun
* api在线文档默认折叠显示，scheme默认选择为https；提交人：shun


## v1.14.2
发布时间： 2023-11-22  
发布人： shun  

* link设计重构，添加相关接口和测试用例；提交人：xukai
* 新增 IPv4RangeDelete、IPv4RangeRecover、IPv4RangeReserve、IPv4RangeAssign 接口和测试用例；提交人：shun
* django4.2.5 to 4.2.7；提交人：shun
* ListServer和ListVoServer api返回数据增加vo组信息；提交人：shun
* AdminListCashCoupon api 增加query参数“id”，查询资源券编码；提交人：shun
* vo组相关接口视图全部移动到vo app下，新增 vo组组长移交接口和测试用例；提交人：shun
* 云主机model增加4个镜像系统有关字段，对应的列举云主机、云主机详情查询和列举云主机归档变更记录接口返回数据增此4个字段数据；提交人：shun
* 压缩link app迁移文件；提交人：shun


## v1.14.1
发布时间： 2023-11-17  
发布人： shun  

* 新增 IPv4RangeMerge、IPv4RangeSplit接口和测试用例；提交人：shun
* 新增 管理员修改资源券备注信息接口和测试用例；提交人：shun
* 个人监控网站状态统计接口返回内容增加异常站点url列表；提交人：shun
* 新增业务、链路、光缆、配线架 detail接口，业务、链路list接口增加状态筛选参数和测试用例；提交人：xukai
* 新增网元查询接口和测试用例；提交人：xukai
* 链路管理：列举四种网元设备的接口添加"is_linked"状态筛选参数和测试用例；提交人：xukai
* 列举链路、业务接口添加状态查询参数和测试用例；提交人：xukai


## v1.14.0
发布时间： 2023-11-07  
发布人： shun  

* 新增ipam app和model定义，新增ListIPv4Range、GetIPAMUserRole、CreateIPv4Range、UpdateIPv4Range接口和测试用例；提交人：shun
* 新增link app和model定义，新增租用线路添加、查询、更新接口，光缆相关接口，用户权限接口，列举业务接口，列举链路机构二级实例接口等和测试用例；提交人：xukai
* 站点监控任务创建和修改api增加tcp监控任务支持；提交人：wanghuang
* ListMonitorWebsite api增加参数’scheme‘，MonitorWebsiteQuery和
  MonitorWebsiteQueryRange接口修改，同时支持http和tcp监控任务数据查询；提交人：shun
* 个人http监控网站 状态统计和网络延迟区间统计2个api修改，避免后加入的tcp监控任务的影响；提交人：shun
* 安装openpyxl依赖包，增加从excel文件导入IP段命令脚本，增加云硬盘和站点监控统计命令，云主机和存储桶统计信息命令serverstats和bucketstats；提交人：shun
* 新增ListStorageServiceAdmin接口和测试用例；提交人：shun
* 邮件模型增加字段‘is_feint’，发送邮件API增加参数‘is_feint’，可以指定邮件只存数据库不真的发送；提交人：shun
* AdminStorageBucketLock api增加‘只读锁’参数选项；提交人：shun
* 新增GetMonitorWebsiteUserEmail接口和测试用例；提交人：shun
* 定义机构联系人model，多对多关联机构，机构增加省份字段，增加ListOrganization、GetOrganizationDetail接口和测试用例；提交人：shun
* 资源券增加备注字段，查询券信息和创建券有关接口增加备注信息；提交人：shun
* 钱包app结算服务单元关联支付机构改为全局统一机构，云主机和存储服务单元新建时自动在余额钱包注册对应的结算服务单元；提交人：shun
* 管理员查询过期云主机，原来只按过期时间，现在加上包年包月付费方式；后台云主机记录修改时，如果是按量付费自动清空过期时间；提交人：shun
* monitor有关的api的代码文件移动到monitor app下；云硬盘最大容量调整为20T；
  模板左边导航栏，机构和云主机服务单元渲染标签修改，只显示有服务单元的机构；提交人：shun


## v1.13.0
发布时间： 2023-10-08  
发布人： shun  

* 桶月度统计趋势模型定义，月度统计数据生成定时脚本实现，新增ListBucketStatsMonthly、
ListStorageStatsMonthly、ListStorageStatsMonthlyService接口和测试用例；提交人：shun
* django-tidb 4.2.0 to 4.2.1，安装python-crontab包，实现crontabtask命令以方便管理定时任务；提交人：shun
* 定价模型增加站点监控价格字段，定义站点监控计量、日结算单模型，实现站点监控计量计费和扣费功能；提交人：shun
* 站点监控任务创建接口和测试用例修改，要求有足够余额或资源券才允许创建；提交人：shun
* 月度报表模型增加站点监控计量计费相关字段，月度报表记录生成功能代码实现站点监控数据月度统计；提交人：shun
* 新增ListMonitorSiteMetering、ListMonitorSiteStatement、GetMonitorSiteStatementDetail接口和测试用例；提交人：shun
* 站点日志数据量时序统计脚本优化，使用异步网络请求缩短耗时，loki日志查询接口异常响应时代码容错性优化；提交人：shun
* 代金券改名为资源券；提交人：shun
* 获取用户服务单元vpn时，如果用户在服务单元没有可用资源只查询vpn不再自动创建新的vpn账户；提交人：shun
* 增加站点名称和网址配置，此配置会动态影响到工单、资源券过期和月度报表通知邮件标题和部分邮件内容；提交人：shun
* 钱包app子服务的服务类别增加‘监控’选项，对应的增加月度报表模板中资源券服务类别；提交人：shun
* 适配器列举系统镜像接口返回数据结构中系统的架构、版本、类型判断容错性优化；提交人：shun


## v1.12.0
发布时间： 2023-09-05  
发布人： shun  

* django3.2升级到4.2，DRF升级到3.14，其他依赖包部分升级；提交人：shun
* Django5将不再支持时区库pytz，从代码中移除pytz，用datetime.timezone.utc替换pytz.utc；提交人：shun
* 重新生成所有app数据库迁移文件；提交人：shun
* 安装django-tidb依赖包，支持兼容tidb数据库；提交人：shun
* 按用户聚合对象存储计量信息管理员查询接口响应数据增加用户所属单位“company”字段；提交人：shun
* 站点监控创建数量上限由2调整为5个；提交人：shun

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

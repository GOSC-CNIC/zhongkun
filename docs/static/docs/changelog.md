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

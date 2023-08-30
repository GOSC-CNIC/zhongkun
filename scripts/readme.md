## 1. 定时任务
本服务有一些计量、月度报表等定时任务需要配置，在linux环境下可以使用crontab工具实现定时任务。   
* 已以CentOS为例
```
# 查看是否安装
rpm -qa | grep crontab

# 安装
yum -y install vixie-cron
yum -y install crontabs
```
* crontab守护进程crond的管理命令：
```
service crond start    //启动
service crond stop     //关闭
service crond restart  //重启
service crond reload   //重新载入配置
service crond staus    //查看状态
```
* crontab定时任务配置文件编辑配置   
  可以使用`crontab -e`编辑配置文件，会在路径/var/spool/cron下创建一个以当前用户名命名的文件，以配置用户定时任务；   
  也可以直接编辑/etc/crontab文件配置系统定时任务；  
  本服务需要配置的定时任务如下：
```
# Example of job definition:
# .---------------- minute (0 - 59)
# |  .------------- hour (0 - 23)
# |  |  .---------- day of month (1 - 31)
# |  |  |  .------- month (1 - 12) OR jan,feb,mar,apr ...
# |  |  |  |  .---- day of week (0 - 6) (Sunday=0 or 7) OR sun,mon,tue,wed,thu,fri,sat
# |  |  |  |  |
# *  *  *  *  * user-name  command to be executed

0 9 * * * root python3 /home/uwsgi/vms/metering/timedelta_metering.py >> /var/log/vms/metering.log
0 17 28 * * root python3 /home/uwsgi/vms/scripts/run_generate_and_email_month_report.py >> /var/log/vms/monthly_report.log
*/1 * * * * root python3 /home/uwsgi/vms/scripts/run_log_site_req_num.py >> /var/log/vms/logsite_timecount.log
0 */1 * * * root python3 /home/uwsgi/vms/scripts/update_service_req_num.py >> /var/log/vms/update_req_num.log
```


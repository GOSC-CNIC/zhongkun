## 初始化服务
1. 代码下载

3. 配置 settings.py  
```shell
settings.py  添加 app 名称 和 定时任务

INSTALLED_APPS = ['apps.app_probe']

CRONTABJOBS = [
    ('task100_probe_start', '*/3 * * * *',
     'python3 /home/uwsgi/yunkun/apps/app_probe/scripts/updatePrometheus.py >> /var/log/yunkun/probe.log')
]  # 注意 将原来的任务删除，只保留自己执行的文件任务


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {
            'timeout': 180,
        }
    }
}

python manage.py migrate
```
url.py 配置
```
   path('api/probe/', include('app_probe.api_urls', namespace='probe-api')),
```

base.html  在首页后添加
```

<li class="nav-item"><a class="nav-link" href="{% url "probes:probe-details" %}"><i class="bi bi-broadcast-pin"></i>{% trans '探针' %}</a></li>

```

```
注释掉  PAY_APP_ID 一行：
apps/servers/handlers/disk_handler.py

apps/servers/handlers/server_handler.py

url.py 
注释掉
check.check_setting()

```



5. 启动定时任务
```shell
python3 manage.py  crontabtask add task100_probe_start

```

nginx 配置
```
    server {
        listen      8000 ;               # TCP listener for HTTP/1.1

        location /  {
            uwsgi_pass unix:///home/uwsgi/yunkun/yunkun.sock;
            include /etc/nginx/uwsgi_params;
            uwsgi_param Host $host;
            uwsgi_param X-Real_IP $remote_addr;
            uwsgi_param X-Forwarded-For $proxy_add_x_forwarded_for;
            uwsgi_param X-Forwarded-Proto $scheme;     # django https need
            allow all;
            allow 127.0.0.1;
            deny all;
        }

    }

```


### 定时任务
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
* crontab定时任务配置管理   
  1. 管理命令管理任务   
     项目配置文件中通过配置项“CRONTABJOBS”配置定时任务；命令默认会操作crontab的配置文件/var/spool/cron/root。
  ```
  # 命令形式，comment是任务的标签，comment不是必须的，可以通过comment操作部分任务
  python3 manage.py crontabtask subcommand comment
  
  crontabtask add           # 添加所有任务到crontab的配置文件
  crontabtask add task1     # 添加所有注释以"task1"开头的所有任务
  crontabtask show          # 列举当前所有任务
  crontabtask remove        # 移除所有任务
  crontabtask remove task1  # 移除所有注释以"task1"开头的所有任务
  ```
  2. 手动管理编辑配置文件   
  可以使用`crontab -e`编辑配置文件，会在路径/var/spool/cron下创建一个以当前用户名命名的文件，以配置用户定时任务；   
  也可以直接编辑/etc/crontab文件配置系统定时任务；  
  配置完成后，重新载入配置，`service crond reload`。  
  本服务需要配置的定时任务如下(具体参照参考项目配置文件中配置项“CRONTABJOBS”配置定时任务)：
  ```
  # Example of job definition:
  # .---------------- minute (0 - 59)
  # |  .------------- hour (0 - 23)
  # |  |  .---------- day of month (1 - 31)
  # |  |  |  .------- month (1 - 12) OR jan,feb,mar,apr ...
  # |  |  |  |  .---- day of week (0 - 6) (Sunday=0 or 7) OR sun,mon,tue,wed,thu,fri,sat
  # |  |  |  |  |
  # *  *  *  *  * user-name  command to be executed
  
  0 9 * * * root python3 /home/uwsgi/yunkun/scripts/timedelta_metering.py >> /var/log/yunkun/metering.log
  0 12 28 * * root python3 /home/uwsgi/yunkun/scripts/run_bucket_monthly_stats.py >> /var/log/yunkun/monthly_bucket_stats.log
  0 17 28 * * root python3 /home/uwsgi/yunkun/scripts/run_generate_and_email_month_report.py >> /var/log/yunkun/monthly_report.log
  */1 * * * * root python3 /home/uwsgi/yunkun/scripts/run_log_site_req_num.py >> /var/log/yunkun/logsite_timecount.log
  0 */1 * * * root python3 /home/uwsgi/yunkun/scripts/update_service_req_num.py >> /var/log/yunkun/update_req_num.log
  */3 * * * * root python3 /home/uwsgi/yunkun/scripts/run_scan_process.py >> /var/log/yunkun/task_scan_process.log
  ```
  
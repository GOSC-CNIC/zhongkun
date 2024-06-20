## 关于ZhongKun


## 环境搭建(CentOS)
### 1 安装python和Git
请自行安装python3.9和Git。
使用Git拉取代码： 
```
git clone https://gitee.com/cstcloud-cnic/zhongkun.git
git clone https://github.com/GOSC-CNIC/zhongkun.git     # 备用
```
### 2 安装python运行环境
#### （1） 使用python虚拟环境
使用pip命令安装pipenv。  
```
pip3 install pipenv
```
在代码工程根目录下，即文件Pipfile同目录下运行命令：  
```
pipenv install
```
#### （2） 使用系统python环境
在代码工程根目录下，即文件requirements.txt同目录下运行命令：  
```pip3 install -r requirements.txt```

### 3 安全敏感信息配置文件
安全信息配置demo文件security_demo.py修改文件名为security.py，根据自己情况完成配置。   
余额结算支付配置PAYMENT_BALANCE需要启动服务后配置，具体请看下面“余额结算”小节说明；

### 4 数据库安装
请自行安装mysql、Mariadb或TiDB数据库，根据自己的情况修改security.py文件中数据库的配置项。 
  ```
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',  # mysql数据库引擎
        # 'ENGINE': 'django_tidb',    # TiDB数据库
        'NAME': 'xxx',  # 数据的库名，事先要创建之
        'HOST': '127.0.0.1',  # 主机
        'PORT': '3306',  # 数据库使用的端口
        'USER': 'xxx',  # 数据库用户名
        'PASSWORD': 'xxx',  # 密码
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4'
        }
    },
}
```   
### 5 运行服务
如果使用python虚拟环境，先激活python虚拟环境  
```
pipenv shell
```    
数据库迁移,在项目根目录下运行如下命令完成数据库迁移。  
```
python3 manage.py migrate
```
运行web服务  
```
python3 manage.py runserver 0:80
```   
如果一切正常，打开浏览器输入url(主机IP, 如：127.0.0.1)即可查看站点;


### 余额结算
服务启动时会检测钱包结算配置参数PAYMENT_BALANCE中的app_id，第一次部署服务时app_id未配置会无法启动服务，
需要先设置一个类似“20240610186309”的有效值，然后启动服务后再后台添加一个结算app后，再修改为正确的。  
钱包可以支持多个外部服务接入结算，一个服务接入钱包都需要在钱包中先注册一个APP，用于钱包接口的权限验证和交易流水所属记录。  
本服务中云主机、云硬盘等功能模块的资源订购支付和计量扣费依赖钱包结算模块，
本服务需要在钱包结算模块中注册一个应用APP，启动服务后，在后台添加一个APP。然后配置安全信息配置文件security.py中余额结算支付
配置项PAYMENT_BALANCE，"app_id"需要配置成上面注册的云服务器APP的id。   
因为钱包在本服务中，所以本服务的结算不会通过钱包网络接口调用，会直接在服务内部函数接口调用。


### 生成环境部署
部署方式不是唯一的，下面推荐一种方式，Python3.9+、Nginx、uwsgi。

* 项目代码必须放在路径/home/uwsgi/下，项目根目录下00_shell目录中有uwsgi的配置文件和几个sh脚本可以方便控制uwsgi启动关闭；
* 也可以使用systemctl管理服务，执行一下脚本config_systemctl.sh，会配置好zhongkun.service服务；
```
systemctl start/stop/reload zhongkun.service
```

* 有些接口需要获取客户端的ip地址，所以nginx需要配置标头X-Forwarded-For
```
X-Forwarded-For 可能伪造，需要在服务一级代理防范处理
比如nginx：
uwsgi_param X-Forwarded-For $remote_addr;     不能使用 $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-For $remote_addr;     不能使用 $proxy_add_x_forwarded_for;
```

* 服务有一些定时任务使用crontab实现，可以使用crontabtask命令管理，具体使用可以查看scripts/readme.md文件
```
python3 manage.py crontabtask [subcommand] [comment]
```

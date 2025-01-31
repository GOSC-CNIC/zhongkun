## 关于ZhongKun


## 环境搭建(CentOS10)
### 1 安装python和Git
请自行安装python3.12和Git。
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
```pip3 install -r 00_script/depend/requirements.txt```

### 3 安全敏感信息配置文件
安全信息配置demo文件security_demo.py修改文件名为security.py，根据自己情况完成配置。配置项主要包括 数据库、邮箱配置；  

### 4 数据库安装
数据库和版本支持MySQL（8.0+）、MariaDB（10.4+）和TiDB（7.5.0+）；请自行安装mysql、Mariadb或TiDB数据库，根据自己的情况修改security.py文件中数据库的配置项。 
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
* 特别注意  
> 创建数据库时，数据库字符集（CHARACTER）使用“utf8mb4”，字符集校对（COLLATION）推荐“utf8mb4_bin”。  
> 通过sql导入旧数据库数据时请一定确保旧数据库和新建数据库的字符集校对一致，例如必须同时为“utf8mb4_bin”，或者同时为“utf8mb4_general_ci”。
因为表主键id是字符串型，后续新建表外键字符集校对会跟随新数据库，如果通过sql导入的旧表和新表字符集校对不一致，创建外键约束会失败。

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


### 站点参数配置
一些站点服务的配置项需要在admin后台（全局配置 > 站点参数）完成配置，包括服务名称、AAI认证、钱包等相关配置。

* 支付钱包配置
>钱包可以支持多个外部服务接入结算，一个服务接入钱包都需要在钱包中先注册一个APP，用于钱包接口的权限验证和交易流水所属记录。  
本服务中云主机、云硬盘等功能模块的资源订购支付和计量扣费依赖钱包结算模块，
本服务需要在钱包结算模块中注册一个应用APP，启动服务后，在后台钱包添加一个APP，然后配置站点参数“本服务内支付结算对应的钱包app_id”，需要配置成上面注册的云服务器APP的id。   
因为钱包在本服务中，所以本服务的结算不会通过钱包网络接口调用，会直接在服务内部函数接口调用。
> 钱包接口加签验签需要配置钱包的密钥对（私钥和公钥），可以通过命令`python3 manage.py generat_rsa_key --keysize=2048`生成一个密钥对。

* AAI登录认证
> 需要先去AAI认证服务提交接人申请，然后完成AAI登录相关的参数配置。


### 生成环境部署
部署方式不是唯一的，下面推荐一种方式，Python3.9+、Nginx、uwsgi。

* 项目代码必须放在路径/home/uwsgi/下，项目根目录下00_script目录中有uwsgi的配置文件和几个sh脚本可以方便控制uwsgi启动关闭；
* 也可以使用systemctl管理服务，执行一下脚本00_script/config_systemctl.sh，会配置好zhongkun.service服务；
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

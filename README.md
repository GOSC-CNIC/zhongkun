## 关于GOSC


## 环境搭建(CentOS)
### 1 安装python和Git
请自行安装python3.9和Git。
使用Git拉取代码： 
```
git clone https://gitee.com/gosc-cnic/vms.git
git clone https://github.com/GOSC-CNIC/gosc.git     # 备用
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
请自行安装mysql数据库，根据自己的情况修改security.py文件中数据库的配置项。 
  ```
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',  # 数据库引擎
        'NAME': 'xxx',  # 数据的库名，事先要创建之
        'HOST': '127.0.0.1',  # 主机
        'PORT': '3306',  # 数据库使用的端口
        'USER': 'xxx',  # 数据库用户名
        'PASSWORD': 'xxx',  # 密码
        'OPTIONS': {'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"}
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
云服务器功能模块的资源订购支付和计量扣费依赖余额结算模块，云服务器功能模块对应于余额结算模块中
的一个应用APP，所以需要在余额结算模块中先注册一个APP，启动服务后，在后台添加一个APP即可。  
然后配置安全信息配置security.py中余额结算支付配置项PAYMENT_BALANCE，
"app_id"需要配置成上面注册的云服务器APP的id。


### 1. 从v1.11.1之前的版本升级到v1.12.0之后版本的步骤
* 必须先正常升级到v1.11.1，执行数据库迁移；
* 然后升级到v1.12.0
>v1.12.0版本主要的依赖包做了升级，django3.2升级到4.2，DRF3.13升到3.14，新使用的django-tidb4.2包。
> 先升级Python环境`pip3 install -r requirements.txt`。
如果数据库是TiDB，配置文件中数据库后端需要修改为`'ENGINE': 'django_tidb'`。
* 创建新数据库迁移文件的迁移记录  
>v1.12.0重新生成了几乎所有app的数据库迁移文件，需要处理迁移记录。
先执行下面假迁移命令添加新的迁移文件的迁移记录，
大多数迁移文件（因为文件名相同）已有对应的旧的迁移记录存在。  
```
python3 manage.py migrate --fake
```

* 删除已经不存在的旧迁移文件的旧的迁移记录
>需要为每个app移除旧的迁移文件的迁移记录
```
python3 manage.py migrate users --prune
python3 manage.py migrate service --prune
python3 manage.py migrate servers --prune
python3 manage.py migrate storage --prune
python3 manage.py migrate report --prune
python3 manage.py migrate order --prune
python3 manage.py migrate metering --prune
python3 manage.py migrate monitor --prune
python3 manage.py migrate bill --prune
```
* 然后再升级到后续版本

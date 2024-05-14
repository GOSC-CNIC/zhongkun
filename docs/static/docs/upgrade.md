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


### 2. 从v1.14.0、v1.14.1版本升级到v1.14.2之后版本的步骤
    原因：由于v1.14.0版本开始增加了link app，在v1.14.2版本对link下的迁移文件进行了压缩，
    所以从v1.14.0、v1.14.1这2个版本升级到v1.14.2(不含)之后的版本，需要先升级到v1.14.2版本，再升级到之后的版本。
    备注：v1.14.0（不含）之前版本升级到v1.14.2（不含）之后版本可以掠过此升级步骤。

* 必须先正常升级到v1.14.2，执行数据库迁移；
* 再升级到之后的版本。
* v1.14.2之后的版本会移除被压缩的旧迁移文件，可以删除这些不存在的旧迁移文件的旧的迁移记录
```
python3 manage.py migrate link --prune
```

### 3. 从v1.16.0之前的版本升级到v1.16.0（含）之后版本的步骤
    原因：由于v1.16.0版本对ipam和link app重构合并为了一个新的app netbox，数据库迁移会把原ipam和link的数据库表数据复制到netbox对
    应的表中，原ipam和link的API接口在v1.16.0之后版本将弃用，netbox有对应的新api。
    新api主要变更：
        原ipam和link的用户角色权限API接口合并为了一个接口；其他接口只是url路径做了更改。

* 必须先正常升级到v1.16.0，执行数据库迁移，创建netbox模型的数据库表，并从ipam和link的数据库表复制数据；
* 再升级到v1.17.0，执行数据库迁移，会删除ipam和link的数据库表和api；
* 再升级到之后的版本。


### 4. 从v2.3.0（含）之前的版本升级到v2.3.1之后版本的步骤
    原因：由于v2.3.1版本对monitor和service app的迁移文件进行了压缩。

* 必须先正常升级到v2.3.1，执行数据库迁移，把压缩后的迁移文件记录更新到数据库迁移记录表；
* 再升级到v2.3.1之后的版本。

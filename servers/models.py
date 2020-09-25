from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.utils import timezone

from service.models import ServiceConfig

User = get_user_model()


class Server(models.Model):
    """
    虚拟服务器实例
    """
    id = models.AutoField(primary_key=True, verbose_name='ID')
    service = models.ForeignKey(to=ServiceConfig, null=True, on_delete=models.SET_NULL, related_name='server_set', verbose_name=_('接入的服务配置'))
    name = models.CharField(max_length=255, verbose_name=_('服务器实例名称'))
    instance_id = models.CharField(max_length=128, verbose_name=_('虚拟主机ID'), help_text=_('各接入服务中虚拟主机的ID'))
    flavor_id = models.CharField(max_length=128, verbose_name=_('硬件配置类型ID'), help_text=_('cpu数、内存大小等硬件配置'))
    vcpus = models.IntegerField(verbose_name=_('虚拟CPU数'), default=0)
    ram = models.IntegerField(verbose_name=_('内存MB'), default=0)
    ipv4 = models.CharField(max_length=128, verbose_name='IPV4', default='')
    public_ip = models.BooleanField(default=True, verbose_name=_('公/私网'))
    image_id = models.CharField(max_length=128, verbose_name=_('镜像ID'), default='')
    image = models.CharField(max_length=255, verbose_name=_('镜像系统名称'), default='')
    creation_time = models.DateTimeField(auto_now_add=True, verbose_name=_('创建时间'))
    remarks = models.CharField(max_length=255, default='', verbose_name=_('备注'))
    user = models.ForeignKey(to=User, verbose_name=_('创建者'), on_delete=models.SET_NULL, related_name='user_servers', null=True)
    # deleted = models.BooleanField(default=False, editable=False, verbose_name=_('删除'))

    class Meta:
        ordering = ['-id']
        verbose_name = _('虚拟服务器')
        verbose_name_plural = verbose_name

    def user_has_perms(self, user):
        """
        用户是否有访问此宿主机的权限

        :param user: 用户
        :return:
            True    # has
            False   # no
        """
        if not isinstance(user.id, int):    # 未认证用户
            return False

        if user.is_superuser:
            return True

        if self.user_id == user.id:
            return True

        return False

    def do_delete(self):
        """
        :return: True or False
        """
        try:
            self.delete()
        except Exception as e:
            return False

        return True

    def do_archive(self):
        """
        创建归档记录
        :return: True or False
        """
        if not self.id:
            return False

        a = ServerArchive()
        try:
            a.service = self.service
            a.name = self.name
            a.instance_id = self.instance_id
            a.vcpus = self.vcpus
            a.ram = self.ram
            a.ipv4 = self.ipv4
            a.public_ip = self.public_ip
            a.image_id = self.image_id
            a.image = self.image
            a.creation_time = self.creation_time
            a.remarks = self.remarks
            a.user_id = self.user_id
            a.deleted_time = timezone.now()
            a.save()
        except Exception as e:
            return False

        if not self.do_delete():
            a.do_delete()

        return True


class ServerArchive(models.Model):
    """
    虚拟服务器实例归档
    """
    id = models.AutoField(primary_key=True, verbose_name='ID')
    service = models.ForeignKey(to=ServiceConfig, null=True, on_delete=models.SET_NULL, related_name='server_archive_set', verbose_name=_('接入的服务配置'))
    name = models.CharField(max_length=255, verbose_name=_('服务器实例名称'))
    instance_id = models.CharField(max_length=128, verbose_name=_('虚拟主机ID'), help_text=_('各接入服务中虚拟主机的ID'))
    vcpus = models.IntegerField(verbose_name=_('虚拟CPU数'), default=0)
    ram = models.IntegerField(verbose_name=_('内存MB'), default=0)
    ipv4 = models.CharField(max_length=128, verbose_name='IPV4', default='')
    public_ip = models.BooleanField(default=True, verbose_name=_('公/私网'))
    image_id = models.CharField(max_length=128, verbose_name=_('镜像ID'), default='')
    image = models.CharField(max_length=255, verbose_name=_('镜像系统名称'), default='')
    creation_time = models.DateTimeField(auto_now_add=True, verbose_name=_('创建时间'))
    remarks = models.CharField(max_length=255, default='', verbose_name=_('备注'))
    user = models.ForeignKey(to=User, verbose_name=_('创建者'), on_delete=models.SET_NULL, related_name='user_server_archives', null=True)
    deleted_time = models.DateTimeField(verbose_name=_('删除归档时间'), auto_now_add=True)

    class Meta:
        ordering = ['-id']
        verbose_name = _('虚拟服务器')
        verbose_name_plural = verbose_name

    def do_delete(self):
        """
        :return: True or False
        """
        try:
            self.delete()
        except Exception as e:
            return False

        return True


class Flavor(models.Model):
    id = models.AutoField(primary_key=True, verbose_name='ID')
    vcpus = models.IntegerField(verbose_name=_('虚拟CPU数'), default=0)
    ram = models.IntegerField(verbose_name=_('内存MB'), default=0)
    enable = models.BooleanField(verbose_name=_('可用状态'), default=True)
    creation_time = models.DateTimeField(auto_now_add=True, verbose_name=_('创建时间'))

    class Meta:
        db_table = 'flavor'
        ordering = ['-id']
        verbose_name = _('配置样式')
        verbose_name_plural = verbose_name



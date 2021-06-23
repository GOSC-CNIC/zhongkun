# Generated by Django 3.2.4 on 2021-06-17 07:51

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='VirtualOrganization',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=256, verbose_name='组名')),
                ('creation_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('company', models.CharField(default='', max_length=256, verbose_name='单位')),
                ('description', models.CharField(default='', max_length=1024, verbose_name='组描述')),
                ('status', models.CharField(choices=[('active', '活动的'), ('disable', '禁用')], default='active', max_length=32, verbose_name='状态')),
                ('deleted', models.BooleanField(default=False, verbose_name='删除')),
            ],
            options={
                'verbose_name': '项目组',
                'verbose_name_plural': '项目组',
                'db_table': 'virtual_organization',
                'ordering': ['creation_time'],
            },
        ),
        migrations.CreateModel(
            name='VoMember',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('leader', '组管理员'), ('member', '组员')], default='member', max_length=16, verbose_name='组角色')),
                ('join_time', models.DateTimeField(auto_now_add=True, verbose_name='加入时间')),
                ('inviter', models.CharField(blank=True, default='', max_length=256, verbose_name='邀请人')),
                ('inviter_id', models.CharField(blank=True, editable=False, max_length=36, verbose_name='邀请人ID')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='用户')),
                ('vo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vo.virtualorganization', verbose_name='组')),
            ],
            options={
                'verbose_name': '组成员关系',
                'verbose_name_plural': '组成员关系',
                'db_table': 'vo_member',
                'ordering': ['join_time'],
            },
        ),
        migrations.AddField(
            model_name='virtualorganization',
            name='members',
            field=models.ManyToManyField(related_name='members_vo_set', through='vo.VoMember', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='virtualorganization',
            name='owner',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='owner_vo_set', to=settings.AUTH_USER_MODEL, verbose_name='所有者'),
        ),
        migrations.AddConstraint(
            model_name='vomember',
            constraint=models.UniqueConstraint(fields=('vo', 'user'), name='unique_together_vo_user'),
        ),
    ]

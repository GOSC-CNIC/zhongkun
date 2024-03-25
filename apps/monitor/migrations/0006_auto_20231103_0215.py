# Generated by Django 4.2.5 on 2023-11-03 02:15

from django.db import migrations, connection

from service.models import OrgDataCenter, DataCenter


def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def do_units_to_org_data_center(units: list, unit_model_class, thanos_or_loki=True):
    """
    thanos_or_loki: True(thanos); False(loki)
    """
    ok_count = 0
    skip_count = 0
    for u_dict in units:
        org = DataCenter.objects.filter(id=u_dict['organization_id']).first()
        if org is None:
            skip_count += 1
            continue

        # 机构下没有数据中心就创建一个默认数据中心
        odc = OrgDataCenter.objects.filter(organization_id=org.id).first()
        if odc is None:
            odc = OrgDataCenter(name=f'数据中心-{org.name}', name_en='', organization_id=org.id)
            odc.save(force_insert=True)

        # thanos or loki update
        endpoint_url = u_dict['endpoint_url']
        if thanos_or_loki:
            if endpoint_url and odc.thanos_endpoint_url != endpoint_url:
                odc.thanos_endpoint_url = endpoint_url
                odc.save(update_fields=['thanos_endpoint_url'])
        else:
            if endpoint_url and odc.loki_endpoint_url != endpoint_url:
                odc.loki_endpoint_url = endpoint_url
                odc.save(update_fields=['loki_endpoint_url'])

        sv = unit_model_class(id=u_dict['id'])
        sv.org_data_center_id = odc.id
        sv.save(update_fields=['org_data_center_id'])
        ok_count += 1

    return ok_count, skip_count


def ceph_unit_org_data_center(apps, schema_editor):
    unit_model_class = apps.get_model("monitor", "MonitorJobCeph")
    # 将来会从监控单元模型移除organization字段，无法通过model获取organization信息。只能使用原始sql
    cursor = connection.cursor()
    sql = 'SELECT `t1`.`id`, `t1`.`organization_id`, `t2`.`endpoint_url` FROM `monitor_monitorjobceph` AS `t1` ' \
          'INNER JOIN `monitor_monitorprovider` AS `t2` ON (`t1`.`provider_id` = `t2`.`id`)'
    cursor.execute(sql)
    units = dictfetchall(cursor)
    ok_count, skip_count = do_units_to_org_data_center(
        units=units, unit_model_class=unit_model_class, thanos_or_loki=True)
    print(f'Changed CEPH monitor unit ForeignKey to OrgDataCenter OK，ok={ok_count}, skip={skip_count}')


def server_unit_org_data_center(apps, schema_editor):
    unit_model_class = apps.get_model("monitor", "MonitorJobServer")
    # 将来会从监控单元模型移除organization字段，无法通过model获取organization信息。只能使用原始sql
    cursor = connection.cursor()
    # cursor.execute('SELECT `id`, `organization_id` FROM `monitor_monitorjobserver`')
    sql = 'SELECT `t1`.`id`, `t1`.`organization_id`, `t2`.`endpoint_url` FROM `monitor_monitorjobserver` AS `t1` ' \
          'INNER JOIN `monitor_monitorprovider` AS `t2` ON (`t1`.`provider_id` = `t2`.`id`)'
    cursor.execute(sql)
    units = dictfetchall(cursor)

    ok_count, skip_count = do_units_to_org_data_center(
        units=units, unit_model_class=unit_model_class, thanos_or_loki=True)
    print(f'Changed Server monitor unit ForeignKey to OrgDataCenter OK，ok={ok_count}, skip={skip_count}')


def tidb_unit_org_data_center(apps, schema_editor):
    unit_model_class = apps.get_model("monitor", "MonitorJobTiDB")
    # 将来会从监控单元模型移除organization字段，无法通过model获取organization信息。只能使用原始sql
    cursor = connection.cursor()
    # cursor.execute('SELECT `id`, `organization_id` FROM `monitor_unit_tidb`')
    sql = 'SELECT `t1`.`id`, `t1`.`organization_id`, `t2`.`endpoint_url` FROM `monitor_unit_tidb` AS `t1` ' \
          'INNER JOIN `monitor_monitorprovider` AS `t2` ON (`t1`.`provider_id` = `t2`.`id`)'
    cursor.execute(sql)
    units = dictfetchall(cursor)

    ok_count, skip_count = do_units_to_org_data_center(
        units=units, unit_model_class=unit_model_class, thanos_or_loki=True)
    print(f'Changed TiDB monitor unit ForeignKey to OrgDataCenter OK，ok={ok_count}, skip={skip_count}')


def sitelog_unit_org_data_center(apps, schema_editor):
    unit_model_class = apps.get_model("monitor", "LogSite")
    # 将来会从监控单元模型移除organization字段，无法通过model获取organization信息。只能使用原始sql
    cursor = connection.cursor()
    # cursor.execute('SELECT `id`, `organization_id` FROM `log_site`')
    sql = 'SELECT `t1`.`id`, `t1`.`organization_id`, `t2`.`endpoint_url` FROM `log_site` AS `t1` ' \
          'INNER JOIN `monitor_monitorprovider` AS `t2` ON (`t1`.`provider_id` = `t2`.`id`)'
    cursor.execute(sql)
    units = dictfetchall(cursor)

    ok_count, skip_count = do_units_to_org_data_center(
        units=units, unit_model_class=unit_model_class, thanos_or_loki=False)
    print(f'Changed SiteLog unit ForeignKey to OrgDataCenter OK，ok={ok_count}, skip={skip_count}')


def do_nothing(apps, schema_editor):
    print('do nothing')


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0005_logsite_org_data_center_and_more'),
    ]

    operations = [
        migrations.RunPython(ceph_unit_org_data_center, reverse_code=do_nothing),
        migrations.RunPython(server_unit_org_data_center, reverse_code=do_nothing),
        migrations.RunPython(tidb_unit_org_data_center, reverse_code=do_nothing),
        migrations.RunPython(sitelog_unit_org_data_center, reverse_code=do_nothing),
    ]
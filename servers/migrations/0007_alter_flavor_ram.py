# Generated by Django 3.2.13 on 2023-04-27 07:34
import math

from django.db import migrations


def flavor_ram_mb_to_gb(apps, schema_editor):
    flavor_model = apps.get_model("servers", "Flavor")
    flavors = flavor_model.objects.all()
    for flavor in flavors:
        if flavor.ram > 1000:
            flavor.ram = math.ceil(flavor.ram / 1024)
            flavor.save(update_fields=['ram'])

    print('Changed flavor ram unit from MiB to GiB OK', len(flavors))


def flavor_ram_gb_to_mb(apps, schema_editor):
    flavor_model = apps.get_model("servers", "Flavor")
    flavors = flavor_model.objects.all()
    for flavor in flavors:
        if flavor.ram < 1000:
            flavor.ram = flavor.ram * 1024
            flavor.save(update_fields=['ram'])

    print('Changed back flavor ram unit from GiB to Mib OK', len(flavors))


class Migration(migrations.Migration):

    dependencies = [
        ('servers', '0006_auto_20230223_0650'),
    ]

    operations = [
        # migrations.AlterField(
        #     model_name='flavor',
        #     name='ram',
        #     field=models.IntegerField(default=0, verbose_name='内存GiB'),
        # ),
        migrations.RunPython(flavor_ram_mb_to_gb, reverse_code=flavor_ram_gb_to_mb),
    ]
from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ("scan", "0003_vtreport_size_vttask_errmsg_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="vttask",
            name="pay_amount",
        ),
        migrations.RemoveField(
            model_name="vttask",
            name="balance_amount",
        ),
        migrations.RemoveField(
            model_name="vttask",
            name="coupon_amount",
        ),
    ]

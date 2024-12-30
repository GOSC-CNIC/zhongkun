from decimal import Decimal

from apps.app_order.models import Price


def create_price():
    price = Price(
        vm_base=Decimal('0.02'),
        vm_ram=Decimal('0.012'),
        vm_cpu=Decimal('0.066'),
        vm_disk=Decimal('0.122'),
        vm_pub_ip=Decimal('0.66'),
        vm_upstream=Decimal('0.33'),
        vm_downstream=Decimal('1.44'),
        vm_disk_snap=Decimal('0.65'),
        disk_size=Decimal('1.02'),
        disk_snap=Decimal('0.77'),
        obj_size=Decimal('1.2'),
        obj_upstream=Decimal('0'),
        obj_downstream=Decimal('0'),
        obj_replication=Decimal('0'),
        obj_get_request=Decimal('0'),
        obj_put_request=Decimal('0'),
        scan_host=Decimal('111.11'),
        scan_web=Decimal('222.22'),
        mntr_site_base=Decimal('0.3'),
        mntr_site_tamper=Decimal('0.2'),
        mntr_site_security=Decimal('0.5'),
        prepaid_discount=66
    )
    price.save(force_insert=True)
    return price

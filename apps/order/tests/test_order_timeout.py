from decimal import Decimal
from datetime import timedelta

from django.utils import timezone
from django.test.testcases import TransactionTestCase

from utils.model import PayType, OwnerType, ResourceType
from apps.order.models import Order
from apps.order.workers.timeout_cancel import OrderTimeoutTask


class OrderTimeoutTests(TransactionTestCase):
    def setUp(self):
        pass

    @staticmethod
    def init_date(length: int):
        ret = []
        for i in range(length):
            order = Order(
                order_type=Order.OrderType.NEW.value,
                status=Order.Status.UNPAID.value,
                total_amount=Decimal(f'{i}.68'),
                payable_amount=Decimal(f'{i}.00'),
                pay_amount=Decimal('0'),
                balance_amount=Decimal('0'),
                coupon_amount=Decimal('0'),
                app_service_id='pay_app_service_id',
                service_id='service_id',
                service_name='service_name',
                resource_type=ResourceType.VM.value,
                instance_config='',
                period=6,
                pay_type=PayType.PREPAID.value,
                payment_time=None,
                user_id='user_id',
                username='username',
                vo_id='vo_id',
                vo_name='vo_name',
                owner_type=OwnerType.USER.value,
                deleted=False,
                trading_status=Order.TradingStatus.OPENING.value,
                completion_time=None,
                creation_time=timezone.now()
            )
            order.save(force_insert=True)
            ret.append(order)

        return ret

    def test_order_timeout(self):
        nt = timezone.now()

        order_list = self.init_date(length=6)
        order1, order2, order3, order4, order5, order6 = order_list

        order2.creation_time = nt - timedelta(minutes=10)
        order2.status = Order.Status.PAID.value
        order2.trading_status = Order.TradingStatus.COMPLETED.value
        order2.save(update_fields=['creation_time', 'status', 'trading_status'])

        order3.creation_time = nt - timedelta(minutes=30)
        order3.save(update_fields=['creation_time'])

        order4.creation_time = nt - timedelta(minutes=40)
        order4.save(update_fields=['creation_time'])

        order5.creation_time = nt - timedelta(minutes=50)
        order5.status = Order.Status.REFUND.value
        order5.save(update_fields=['creation_time', 'status'])

        order6.creation_time = nt - timedelta(minutes=60)
        order6.save(update_fields=['creation_time'])

        OrderTimeoutTask(timeout_minutes=120).run()
        order1.refresh_from_db()
        self.assertEqual(order1.status, Order.Status.UNPAID.value)
        order2.refresh_from_db()
        self.assertEqual(order2.status, Order.Status.PAID.value)
        order3.refresh_from_db()
        self.assertEqual(order3.status, Order.Status.UNPAID.value)
        order4.refresh_from_db()
        self.assertEqual(order4.status, Order.Status.UNPAID.value)
        order5.refresh_from_db()
        self.assertEqual(order5.status, Order.Status.REFUND.value)
        order6.refresh_from_db()
        self.assertEqual(order6.status, Order.Status.UNPAID.value)

        OrderTimeoutTask(timeout_minutes=60).run()
        order1.refresh_from_db()
        self.assertEqual(order1.status, Order.Status.UNPAID.value)
        order2.refresh_from_db()
        self.assertEqual(order2.status, Order.Status.PAID.value)
        order3.refresh_from_db()
        self.assertEqual(order3.status, Order.Status.UNPAID.value)
        order4.refresh_from_db()
        self.assertEqual(order4.status, Order.Status.UNPAID.value)
        order5.refresh_from_db()
        self.assertEqual(order5.status, Order.Status.REFUND.value)
        order6.refresh_from_db()
        self.assertEqual(order6.status, Order.Status.CANCELLED.value)
        self.assertEqual(order6.trading_status, Order.TradingStatus.CLOSED.value)

        OrderTimeoutTask(timeout_minutes=30).run()
        order1.refresh_from_db()
        self.assertEqual(order1.status, Order.Status.UNPAID.value)
        order2.refresh_from_db()
        self.assertEqual(order2.status, Order.Status.PAID.value)
        order3.refresh_from_db()
        self.assertEqual(order3.status, Order.Status.CANCELLED.value)
        order4.refresh_from_db()
        self.assertEqual(order4.status, Order.Status.CANCELLED.value)
        order5.refresh_from_db()
        self.assertEqual(order5.status, Order.Status.REFUND.value)
        order6.refresh_from_db()
        self.assertEqual(order6.status, Order.Status.CANCELLED.value)
        self.assertEqual(order6.trading_status, Order.TradingStatus.CLOSED.value)

        OrderTimeoutTask(timeout_minutes=-1).run()
        order1.refresh_from_db()
        self.assertEqual(order1.status, Order.Status.CANCELLED.value)
        order2.refresh_from_db()
        self.assertEqual(order2.status, Order.Status.PAID.value)
        order3.refresh_from_db()
        self.assertEqual(order3.status, Order.Status.CANCELLED.value)
        order4.refresh_from_db()
        self.assertEqual(order4.status, Order.Status.CANCELLED.value)
        order5.refresh_from_db()
        self.assertEqual(order5.status, Order.Status.REFUND.value)
        order6.refresh_from_db()
        self.assertEqual(order6.status, Order.Status.CANCELLED.value)
        self.assertEqual(order6.trading_status, Order.TradingStatus.CLOSED.value)

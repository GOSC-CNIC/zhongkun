from decimal import Decimal

from django.test import TransactionTestCase

from core import errors
from utils.test import get_or_create_user
from utils.model import OwnerType
from order.models import ResourceType
from vo.managers import VoManager
from .models import Bill, PaymentHistory
from .managers import BillManager, PaymentManager


class PaymentManagerTests(TransactionTestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.vo = VoManager().create_vo(user=self.user, name='test vo', company='test', description='test')

    def test_pay_user_bill(self):
        pay_mgr = PaymentManager()
        # test create bill  OwnerType
        with self.assertRaises(errors.Error):
            BillManager().create_bill(
                _type=Bill.Type.PREPAID,
                status=Bill.Status.UNPAID.value,
                amounts=Decimal('123.45'),
                service_id='service_id',
                resource_type=ResourceType.VM.value,
                instance_id='instance_id',
                order_id='order_id',
                owner_type=OwnerType.VO.value,
                user_id=self.user.id,
                vo_id=''
            )
        with self.assertRaises(errors.Error):
            BillManager().create_bill(
                _type=Bill.Type.PREPAID,
                status=Bill.Status.UNPAID.value,
                amounts=Decimal('123.45'),
                service_id='service_id',
                resource_type=ResourceType.VM.value,
                instance_id='instance_id',
                order_id='order_id',
                owner_type=OwnerType.USER.value,
                user_id='',
                vo_id='test'
            )

        # pay bill, invalid user id
        bill_unpaid1 = BillManager().create_bill(
            _type=Bill.Type.PREPAID,
            status=Bill.Status.UNPAID.value,
            amounts=Decimal('123.45'),
            service_id='service_id',
            resource_type=ResourceType.VM.value,
            instance_id='instance_id',
            order_id='order_id',
            owner_type=OwnerType.USER.value,
            user_id='user_id',
            vo_id=''
        )
        with self.assertRaises(errors.Error):
            pay_mgr.pay_bill(bill=bill_unpaid1, payer_name=self.user.username, remark='')

        # pay bill, type PREPAID
        bill_prepaid = BillManager().create_bill(
            _type=Bill.Type.PREPAID,
            status=Bill.Status.UNPAID.value,
            amounts=Decimal('123.45'),
            service_id='service_id',
            resource_type=ResourceType.VM.value,
            instance_id='instance_id',
            order_id='order_id',
            owner_type=OwnerType.USER.value,
            user_id=self.user.id,
            vo_id=''
        )
        balance = pay_mgr.pay_bill(bill=bill_prepaid, payer_name=self.user.username, remark='')
        self.assertEqual(balance, Decimal('-123.45'))
        bill_prepaid.refresh_from_db()
        self.assertEqual(bill_prepaid.status, Bill.Status.PREPAID)
        pay_history = bill_prepaid.paymenthistory
        self.assertEqual(pay_history.payer_type, OwnerType.USER.value)
        self.assertEqual(pay_history.payer_id, self.user.id)
        self.assertEqual(pay_history.type, PaymentHistory.Type.PAYMENT)
        self.assertEqual(pay_history.amounts, Decimal('-123.45'))
        self.assertEqual(pay_history.before_payment, Decimal(0))
        self.assertEqual(pay_history.after_payment, Decimal('-123.45'))

        # pay bill, type REFUND
        bill_refund = BillManager().create_bill(
            _type=Bill.Type.REFUND,
            status=Bill.Status.UNPAID.value,
            amounts=Decimal('223.45'),
            service_id='service_id',
            resource_type=ResourceType.VM.value,
            instance_id='instance_id',
            order_id='order_id',
            owner_type=OwnerType.USER.value,
            user_id=self.user.id,
            vo_id=''
        )
        balance = pay_mgr.pay_bill(bill=bill_refund, payer_name=self.user.username, remark='')
        self.assertEqual(balance, Decimal(100))
        bill_refund.refresh_from_db()
        self.assertEqual(bill_refund.status, Bill.Status.PREPAID)
        pay_history = bill_refund.paymenthistory
        self.assertEqual(pay_history.amounts, Decimal('223.45'))
        self.assertEqual(pay_history.before_payment, Decimal('-123.45'))
        self.assertEqual(pay_history.after_payment, Decimal(100))
        self.assertEqual(pay_history.payer_type, OwnerType.USER.value)
        self.assertEqual(pay_history.payer_id, self.user.id)
        self.assertEqual(pay_history.type, PaymentHistory.Type.REFUND)

    def test_pay_vo_bill(self):
        pay_mgr = PaymentManager()
        payer_name = self.vo.name

        # pay bill, invalid vo id
        bill_unpaid1 = BillManager().create_bill(
            _type=Bill.Type.PREPAID,
            status=Bill.Status.UNPAID.value,
            amounts=Decimal('123.45'),
            service_id='service_id',
            resource_type=ResourceType.VM.value,
            instance_id='instance_id',
            order_id='order_id',
            owner_type=OwnerType.VO.value,
            user_id='',
            vo_id='vo_id'
        )
        with self.assertRaises(errors.Error):
            pay_mgr.pay_bill(bill=bill_unpaid1, payer_name=payer_name, remark='')

        # pay bill, type PREPAID
        bill_prepaid = BillManager().create_bill(
            _type=Bill.Type.PREPAID,
            status=Bill.Status.UNPAID.value,
            amounts=Decimal('123.45'),
            service_id='service_id',
            resource_type=ResourceType.VM.value,
            instance_id='instance_id',
            order_id='order_id',
            owner_type=OwnerType.VO.value,
            user_id='',
            vo_id=self.vo.id
        )
        balance = pay_mgr.pay_bill(bill=bill_prepaid, payer_name=payer_name, remark='')
        self.assertEqual(balance, Decimal('-123.45'))
        bill_prepaid.refresh_from_db()
        self.assertEqual(bill_prepaid.status, Bill.Status.PREPAID)
        pay_history = bill_prepaid.paymenthistory
        self.assertEqual(pay_history.amounts, Decimal('-123.45'))
        self.assertEqual(pay_history.before_payment, Decimal(0))
        self.assertEqual(pay_history.after_payment, Decimal('-123.45'))
        self.assertEqual(pay_history.payer_type, OwnerType.VO.value)
        self.assertEqual(pay_history.payer_id, self.vo.id)
        self.assertEqual(pay_history.type, PaymentHistory.Type.PAYMENT)

        # pay bill, type REFUND
        bill_refund = BillManager().create_bill(
            _type=Bill.Type.REFUND,
            status=Bill.Status.UNPAID.value,
            amounts=Decimal('223.45'),
            service_id='service_id',
            resource_type=ResourceType.VM.value,
            instance_id='instance_id',
            order_id='order_id',
            owner_type=OwnerType.VO.value,
            user_id='',
            vo_id=self.vo.id
        )
        balance = pay_mgr.pay_bill(bill=bill_refund, payer_name=payer_name, remark='')
        self.assertEqual(balance, Decimal(100))
        bill_refund.refresh_from_db()
        self.assertEqual(bill_refund.status, Bill.Status.PREPAID)
        pay_history = bill_refund.paymenthistory
        self.assertEqual(pay_history.payer_type, OwnerType.VO.value)
        self.assertEqual(pay_history.payer_id, self.vo.id)
        self.assertEqual(pay_history.type, PaymentHistory.Type.REFUND)
        self.assertEqual(pay_history.amounts, Decimal('223.45'))
        self.assertEqual(pay_history.before_payment, Decimal('-123.45'))
        self.assertEqual(pay_history.after_payment, Decimal(100))

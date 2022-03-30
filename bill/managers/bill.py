from decimal import Decimal

from django.utils.translation import gettext as _

from core import errors
from utils.model import OwnerType
from order.models import ResourceType
# from bill.models import Bill
#
#
# class BillManager:
#     def create_bill(
#             self,
#             _type: str,
#             status: str,
#             amounts: Decimal,
#             service_id: str,
#             resource_type: str,
#             instance_id: str,
#             order_id: str,
#             owner_type: str,
#             user_id: str = '',
#             vo_id: str = ''
#     ):
#         if status not in Bill.Status.values:
#             raise errors.Error(message=_('无效的账单状态'))
#
#         if resource_type not in ResourceType.values:
#             raise errors.Error(message=_('无效的资源类型'))
#
#         if owner_type == OwnerType.USER.value:
#             if not user_id:
#                 raise errors.Error(message=_('归属者类型为用户, 用户id无效'))
#         elif owner_type == OwnerType.VO.value:
#             if not vo_id:
#                 raise errors.Error(message=_('归属者类型为vo组, vo组id无效'))
#         else:
#             raise errors.Error(message=_('无效的归属者类型'))
#
#         bill = Bill(
#             type=_type, status=status, amounts=amounts, service_id=service_id,
#             resource_type=resource_type, instance_id=instance_id, order_id=order_id,
#             owner_type=owner_type, user_id=user_id, vo_id=vo_id
#         )
#         bill.save(force_insert=True)
#         return bill

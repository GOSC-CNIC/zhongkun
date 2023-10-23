from django.utils.translation import gettext as _
from datetime import date
from link.models import LeaseLine
from django.db.models import Q
from core import errors

class LeaseLineManager:
    @staticmethod
    def get_queryset():
        return LeaseLine.objects.all()

    @staticmethod
    def get_leaseline(id: str):
        """
        :raises: TicketNotExist
        """
        print(id)
        
        ticket = LeaseLine.objects.filter(id=id).first()
        if ticket is None:
            raise errors.BadRequest(message=_('租用线路不存在'), code='LeaseLineNotExist')
        return ticket

    @staticmethod
    def create_leaseline(
            private_line_number: str,
            lease_line_code: str,
            line_username: str,
            endpoint_a: str,
            endpoint_z: str,
            line_type: str,
            cable_type: str,
            bandwidth: float,
            length: int,
            provider: str,
            enable_date: date,
            is_whithdrawal: bool,
            money: float,
            remarks: str
    ) -> LeaseLine:

        leaseline = LeaseLine(
            private_line_number=private_line_number,
            lease_line_code=lease_line_code,
            line_username=line_username,
            endpoint_a=endpoint_a,
            endpoint_z=endpoint_z,
            line_type=line_type,
            cable_type=cable_type,
            bandwidth=bandwidth,
            length=length,
            provider=provider,
            enable_date=enable_date,
            is_whithdrawal=is_whithdrawal,
            money=money,
            remarks=remarks,
        )
        leaseline.save(force_insert=True)
        return leaseline
    
    @staticmethod
    def update_leaseline(
            leaseline: LeaseLine,
            private_line_number: str,
            lease_line_code: str,
            line_username: str,
            endpoint_a: str,
            endpoint_z: str,
            line_type: str,
            cable_type: str,
            bandwidth: float,
            length: int,
            provider: str,
            enable_date: date,
            is_whithdrawal: bool,
            money: float,
            remarks: str
    ) -> LeaseLine:
        leaseline.private_line_number=private_line_number
        leaseline.lease_line_code=lease_line_code
        leaseline.line_username=line_username
        leaseline.endpoint_a=endpoint_a
        leaseline.endpoint_z=endpoint_z
        leaseline.line_type=line_type
        leaseline.cable_type=cable_type
        leaseline.bandwidth=bandwidth
        leaseline.length=length
        leaseline.provider=provider
        leaseline.enable_date=enable_date
        leaseline.is_whithdrawal=is_whithdrawal
        leaseline.money=money
        leaseline.remarks=remarks
        leaseline.save(force_update=True)
        return leaseline
    
    @staticmethod
    def filter_queryset(is_whithdrawal: bool = None,  search: str = None, enable_date_start: date = None, enable_date_end: date = None):
        qs = LeaseLineManager.get_queryset()
        lookups = {}
        if is_whithdrawal is not None:
            lookups['is_whithdrawal'] = is_whithdrawal

        if enable_date_start:
            lookups['enable_date__gte'] = enable_date_start

        if enable_date_end:
            lookups['enable_date__lte'] = enable_date_end

        qs = qs.filter(**lookups)
        if search:
            q = Q(private_line_number__icontains=search) | Q(lease_line_code__icontains=search) | Q(line_username__icontains=search) \
                | Q(endpoint_a__icontains=search) | Q(endpoint_z__icontains=search) | Q(remarks__icontains=search)

            qs = qs.filter(q)

        return qs
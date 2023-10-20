from datetime import date
from link.models import LeaseLine

class LeaseLineManager:
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
        print(enable_date)
        print(type(enable_date))

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
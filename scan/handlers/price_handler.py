from api.viewsets import CustomGenericViewSet
from rest_framework.response import Response
from scan.models import VtScanService
from utils.decimal_utils import quantize_10_2


class ScanPriceHandler:
    @staticmethod
    def get_scan_price(view: CustomGenericViewSet, request):
        try:
            ins = VtScanService.get_instance()
            return Response(
                data={
                    "price": {
                        "web": str(quantize_10_2(ins.web_scan_price)),
                        "host": str(quantize_10_2(ins.host_scan_price)),
                    }
                }
            )
        except Exception as exc:
            return view.exception_response(exc)

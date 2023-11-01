from api.viewsets import NormalGenericViewSet
from django.utils.translation import gettext_lazy, gettext as _
from api.paginations import NewPageNumberPagination
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from link.handlers.opticalfiber_handler import OpticalFiberHandler
from link.serializers.opticalfiber_serializer import OpticalFiberSerializer
from rest_framework.decorators import action


class OpticalFiberViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举光纤'),
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举光纤信息

            http Code 200 Ok:
                {
                    "count": 141,
                    "page_num": 8,
                    "page_size": 20,
                    "results": [
                        {
                            "is_linked": true,
                            "element_id": "mgb3k0t02f0m954adqenm950n",
                            "id": "mgb3ciey2jgjqh0i56ihnpzk2",
                            "sequence": 1,
                            "fiber_cable": {
                                "id": "mgb1bi5zka5c0dyrgo0m89sq7",
                                "number": "test-fibercable-number-1"
                            }
                        }
                    ]
                }

        """
        return OpticalFiberHandler.list_opticalfiber(view=self, request=request)
    

    def get_serializer_class(self):
        return OpticalFiberSerializer

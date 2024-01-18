from rest_framework.permissions import BasePermission

from .utils.iprestrict import LinkIPRestrictor


class LinkIPRestrictPermission(BasePermission):
    def has_permission(self, request, view):
        # try:
        #     LinkIPRestrictor().check_restricted(request=request)
        # except AccessDenied as exc:
        #     self.message = exc.message
        #     return False
        #
        LinkIPRestrictor().check_restricted(request=request)
        return True
